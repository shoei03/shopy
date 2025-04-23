import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import seaborn as sns
from tqdm import tqdm

from shopy import JSON, ExtractFilesInfo, GetName, ShellCommand, path_config


class CalcCentrality:
    def __init__(self):
        self.shell_command = ShellCommand()
        self.json = JSON()

    def build_dependency(
        self,
        cwd: Path = path_config.REPO_DIR,
        language: str = "java",
        max_files: int = 20000,
    ) -> dict:
        """ファイルの依存関係を取得する

        Args:
            cwd (Path, optional): リポジトリまでのパス. Defaults to path_config.REPO_DIR.
            language (str, optional): 対象言語. Defaults to "java".
            max_files (int, optional): 最大ファイル数. Defaults to 20000.

        Returns:
            dict: ファイルの依存関係
        """
        # ファイル情報を取得
        ef = ExtractFilesInfo(path_config.REPO_DIR, path_config.DATA_DIR)
        file_df = ef.extract_file_info(cwd=cwd, language=language)

        # ファイルのパスを取得
        file_paths: list[Path] = [
            Path(f) for f in file_df[path_config.EXISTING_FILE_COLUMNS].tolist()
        ]

        # データ数が多い場合はサンプリング
        sampled_files = (
            file_paths[:max_files] if len(file_paths) > max_files else file_paths
        )

        # ファイル内のpackageとimportを取得
        get_name = GetName()
        file_dependency: dict[Path, dict[str, object]] = {
            file_path: {
                "fqn": get_name.find_fqn(cwd, file_path, path_config.PACKAGE_PREFIX),
                "imp": get_name.extract_imports(cwd, file_path),
            }
            for file_path in tqdm(
                sampled_files, desc="依存関係解析", leave=False, dynamic_ncols=True
            )
        }

        return file_dependency

    def build_dependency_graph(self, file_dependency: dict[Path, dict]) -> nx.DiGraph:
        """
        FQNベースの依存関係グラフを構築する。

        Args:
            file_dependency: ファイルパスをキー、"fqn"と"imp"を含む辞書を値とする依存情報

        Returns:
            nx.DiGraph: クラスFQNをノードとする依存関係グラフ
        """
        G = nx.DiGraph()

        for info in file_dependency.values():
            if not (fqn := info.get("fqn")):
                continue

            G.add_node(fqn)

            for imp in info.get("imp", []):
                G.add_edge(fqn, imp)

        return G

    def filter_metadata_monthly(
        self,
        commit_hashes: list[str],
        commit_dates: list[datetime],
        time_period: int = 30,
    ) -> list[tuple[str, datetime]]:
        """1ヶ月ごとにコミットをフィルタリングする。

        Args:
            commit_hashes (list[str]): コミットハッシュのリスト
            commit_dates (list[datetime]): コミット日時のリスト

        Returns:
            list[tuple[str, datetime]]: フィルタリングされたコミットハッシュと日時のリスト
        """
        if (
            not commit_dates
            or not commit_hashes
            or len(commit_dates) != len(commit_hashes)
        ):
            return []

        selected_indices: list[int] = [0]  # 最初のインデックスは常に含める
        start_date = commit_dates[0]
        end_date = commit_dates[-1]

        current_target = start_date + timedelta(days=time_period)
        idx = 1

        while current_target < end_date and idx < len(commit_dates):
            while idx < len(commit_dates) and commit_dates[idx] < current_target:
                idx += 1
            if idx < len(commit_dates):
                selected_indices.append(idx)
            current_target += timedelta(days=time_period)

        if selected_indices[-1] != len(commit_dates) - 1:
            selected_indices.append(len(commit_dates) - 1)

        # インデックスを使って分離リストに変換
        filtered_hashes: list[str] = [commit_hashes[i] for i in selected_indices]
        filtered_dates: list[datetime] = [commit_dates[i] for i in selected_indices]

        return filtered_hashes, filtered_dates

    def extract_commit_metadata(
        self, file_path_in_repo: Path
    ) -> tuple[list[str], list[datetime]]:
        """gitのメタデータを抽出する

        Args:
            file_path (Path): 対象とするファイルのパス

        Returns:
            tuple[list[str], list[datetime]]: コミットハッシュと日時のリスト
        """
        # Gitログからファイルのコミット情報（古い順）を取得
        shell_command = ShellCommand()
        raw_logs: list[str] = shell_command.run_cmd(
            cmd=(
                f"git log --all --full-history --reverse --pretty=format:%H,%aI -- {file_path_in_repo}"
            ),
            cwd=path_config.REPO_DIR,
        )

        # コミットハッシュとISO形式の日時に分解
        commit_metadata_pairs: list[tuple[str, str]] = [
            log.split(",", 1) for log in raw_logs
        ]

        # ハッシュとUTC日時にそれぞれ分離して格納
        commit_hashes: list[str] = [pair[0] for pair in commit_metadata_pairs]
        commit_dates: list[datetime] = [
            datetime.fromisoformat(pair[1]).astimezone(timezone.utc)
            for pair in commit_metadata_pairs
        ]

        return commit_hashes, commit_dates

    def get_last_commit_date(self, repo_path: Path, limit_year: str) -> str:
        all_commits: list[str] = self.shell_command.run_cmd(
            cmd=f"git log --before={limit_year}-01-01T00:00:00+00:00 --pretty=format:'%H|%aI' --reverse",
            cwd=repo_path,
        )
        return all_commits[-1]

    def get_child_dir(self, path: Path) -> list[Path]:
        """指定したパスの子ディレクトリを取得する

        Args:
            path (Path): 対象のパス

        Returns:
            list[Path]: 子ディレクトリのリスト
        """
        return [p.name for p in path.iterdir() if p.is_dir()]

    def create_centrality(self, output_dir: Path) -> None:
        """中心性を計算し、CSVに保存する

        Args:
            output_dir (Path): 依存関係が記述されたJSONファイルのパス
        """
        file_dependency = self.json.read_json(
            input_dir=(output_dir / "file_dependency.json")
        )

        graph = self.build_dependency_graph(file_dependency)
        centrality = nx.pagerank(graph)

        centrality_df = pd.DataFrame(
            {
                path_config.CENTRALITY_COLUMNS: centrality.values(),
                path_config.FULL_PACKAGE_COLUMNS: centrality.keys(),
            }
        )
        sorted_centrality_df = centrality_df.sort_values(
            by=path_config.CENTRALITY_COLUMNS, ascending=False
        )
        sorted_centrality_df.to_csv(
            output_dir / path_config.CENTRALITY_CSV, index=False
        )

    def save_centrality_changes(self, df_plot: pd.DataFrame, fqn: str) -> None:
        sns.set(style="whitegrid")
        plt.figure(figsize=(10, 6))
        sns.lineplot(
            data=df_plot,
            x=path_config.COMMIT_DATE_COLUMNS,
            y=path_config.CENTRALITY_COLUMNS,
            marker="o",
        )

        plt.title(f"Time-series changes in the centrality score for {fqn} ")
        plt.xlabel(path_config.COMMIT_DATE_COLUMNS)
        plt.ylabel(path_config.CENTRALITY_COLUMNS)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(
            path_config.CENTRALITY_DATA_DIR / fqn / path_config.CENTRALITY_CHANGES_PNG,
            dpi=300,
        )

    def main(self) -> None:
        # 2024年の最終コミット日時にリポジトリを戻す
        last_commit_metadata: str = self.get_last_commit_date(
            repo_path=path_config.REPO_DIR, limit_year="2025"
        )
        last_commit_hash: str = last_commit_metadata.split("|")[0]
        self.shell_command.run_cmd(
            cmd=f"git reset --hard {last_commit_hash}", cwd=path_config.REPO_DIR
        )
        sleep(4)

        # # ファイルの情報を書き込む
        # efi = ExtractFilesInfo(path_config.REPO_DIR, path_config.DATA_DIR)
        # existing_files_df = efi.main(isDeleted=False)

        # ファイルの情報を読み取る
        existing_files_df = pd.read_csv(
            path_config.EXISTING_FILES_INFO_CSV,
            encoding="utf-8",
        )

        # --------------------------------
        # 一旦ランダムに10件のファイルのみを処理
        random_existing_files_list: list[Path] = list(
            existing_files_df[path_config.EXISTING_FILE_COLUMNS]
        )
        random.shuffle(random_existing_files_list)
        random_existing_files_list = random_existing_files_list[:10]
        # --------------------------------
        for file_path_in_repo in tqdm(
            random_existing_files_list,
            desc="ファイルを1件ずつ処理中",
            dynamic_ncols=True,
        ):
            try:
                commit_hashes, commit_dates = self.extract_commit_metadata(
                    file_path_in_repo=file_path_in_repo
                )
                filtered_hashes, filtered_dates = self.filter_metadata_monthly(
                    commit_hashes, commit_dates, time_period=180
                )
            except Exception as e:
                print(f"ファイルのメタデータの取得でエラーが発生しました。: {e}")
                continue

            with ThreadPoolExecutor(max_workers=4) as executor:
                for commit_hash, commit_date in tqdm(
                    zip(filtered_hashes, filtered_dates),
                    desc="特定のコミットを処理中",
                    total=len(filtered_hashes),
                    leave=False,
                ):
                    try:
                        # コミットIDの状態にリポジトリを戻す
                        self.shell_command.run_cmd(
                            cmd=f"git reset --hard {commit_hash}",
                            cwd=path_config.REPO_DIR,
                        )
                        sleep(2)

                        # ファイルの依存関係を取得
                        file_dependency: dict = self.build_dependency(
                            max_files=20000,
                            cwd=path_config.REPO_DIR,
                            language="java",
                        )

                        if Path(file_path_in_repo) not in file_dependency:
                            print(
                                f"[WARN] {file_path_in_repo} が依存関係に見つかりません。スキップします。"
                            )
                            continue

                        # 完全修飾クラス名を取得
                        fqn = file_dependency[Path(file_path_in_repo)]["fqn"]

                        # ファイルの依存関係をjsonで保存
                        output_path: Path = (
                            path_config.CENTRALITY_DATA_DIR
                            / fqn
                            / str(commit_date)
                            / "file_dependency.json"
                        )
                        processed_file_dependency = {
                            str(k): v for k, v in file_dependency.items()
                        }
                        executor.submit(
                            self.json.write_json(
                                dict=processed_file_dependency,
                                output_dir=output_path,
                            )
                        )
                    except Exception as e:
                        print(
                            f"[ERROR] コミット処理中にエラーが発生しました。 {commit_hash}: {e}"
                        )
                        continue

        # FQNs: list[Path] = self.get_child_dir(path_config.CENTRALITY_DATA_DIR)
        # for fqn in FQNs:
        #     commit_dates: list[Path] = self.get_child_dir(
        #         path_config.CENTRALITY_DATA_DIR / fqn
        #     )

        #     data: list = []
        #     for commit_date in commit_dates:
        #         output_dir: Path = path_config.CENTRALITY_DATA_DIR / fqn / commit_date

        #         self.create_centrality(output_dir=output_dir)

        #         # 中心性スコアを取得
        #         centrality_df = pd.read_csv(output_dir / path_config.CENTRALITY_CSV)
        #         target_row = centrality_df[centrality_df["FQN"].str.endswith(str(fqn))]
        #         if not target_row.empty:
        #             centrality_score = target_row[path_config.CENTRALITY_COLUMNS].iloc[
        #                 0
        #             ]

        #             data.append(
        #                 {
        #                     path_config.COMMIT_DATE_COLUMNS: commit_date,
        #                     path_config.CENTRALITY_COLUMNS: centrality_score,
        #                 }
        #             )

        #     df_plot = pd.DataFrame(data)
        #     df_plot[path_config.COMMIT_DATE_COLUMNS] = pd.to_datetime(
        #         df_plot[path_config.COMMIT_DATE_COLUMNS], utc=True
        #     )

        #     self.save_centrality_changes(df_plot, fqn)


if __name__ == "__main__":
    calc_centrality = CalcCentrality()
    calc_centrality.main()
