import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import seaborn as sns
from tqdm import tqdm

from shopy import ExtractFilesInfo, GetName, ShellCommand, path_config


class CalcCentrality:
    def __init__(self):
        self.shell_command = ShellCommand()

    def build_dependency_graph(
        self, file_paths: list[Path], max_files: int = 20000
    ) -> tuple[nx.DiGraph, dict[Path, str]]:
        """ファイルの依存関係グラフを構築する。

        Args:
            file_paths (list[Path]): ファイルのリスト
            max_files (int, optional): ファイル数の制限. Defaults to 20000.

        Returns:
            tuple[nx.DiGraph, dict[Path, str]]: ファイルパスとパッケージ名のマッピング
        """
        G = nx.DiGraph()
        get_name = GetName()
        filepath_to_package_name = {}

        # データ数が多い場合はサンプリング
        sampled_files = (
            file_paths[:max_files] if len(file_paths) > max_files else file_paths
        )

        # パッケージ名を取得してノードを追加
        for file in tqdm(
            sampled_files, desc="FQN抽出", leave=False, dynamic_ncols=True
        ):
            fqn = get_name.get_fqn(file, base_package_prefix=path_config.PACKAGE_PREFIX)
            if fqn:
                filepath_to_package_name[file] = fqn
                G.add_node(fqn)

        # import文を取得してエッジを追加
        for file, src_fqn in tqdm(
            filepath_to_package_name.items(),
            desc="依存関係解析",
            leave=False,
            dynamic_ncols=True,
        ):
            for imp in get_name.extract_imports(file):
                if imp.startswith(path_config.PACKAGE_PREFIX):
                    G.add_edge(src_fqn, imp)

        return G, filepath_to_package_name

    def analyze_centrality_from_df(
        self,
        file_df: pd.DataFrame,
        cwd: Path,
        max_files: int = 2000,
        commit_date: datetime = "",
        target_file_path: str = "",
    ) -> None:
        """ファイルの依存関係を解析し、中心性スコアを計算する。

        Args:
            file_df (pd.DataFrame): ファイル情報のDataFrame
            cwd (Path): リポジトリのカレントディレクトリ
            max_files (int, optional): ファイル数の制限 Defaults to 2000.
            commit_date (datetime, optional): コミット日時 Defaults to "".
            target_file_path (str, optional): 着目するファイル Defaults to "".
        """
        file_paths: list[Path] = [
            cwd / Path(f) for f in file_df[path_config.EXISTING_FILE_COLUMNS].tolist()
        ]
        graph, file_to_fqn = self.build_dependency_graph(
            file_paths, max_files=max_files
        )
        centrality = nx.pagerank(graph)

        # FQN列を追加
        file_df[path_config.FULL_PACKAGE_COLUMNS] = file_df[
            path_config.EXISTING_FILE_COLUMNS
        ].map(lambda p: file_to_fqn.get(cwd / Path(p), ""))

        # 中心性スコア列を追加（FQNに対応するもののみ）
        file_df[path_config.CENTRALITY_COLUMNS] = (
            file_df[path_config.FULL_PACKAGE_COLUMNS].map(centrality).fillna(0.0)
        )

        # 中心性スコア順にソート
        centrality_df = file_df[
            [
                path_config.CENTRALITY_COLUMNS,
                path_config.FULL_PACKAGE_COLUMNS,
                path_config.EXISTING_FILE_COLUMNS,
            ]
        ].sort_values(by=path_config.CENTRALITY_COLUMNS, ascending=False)

        # 保存先ディレクトリを確保
        target_file_path = target_file_path.replace("/", "_")
        output_dir = Path(
            path_config.CENTRALITY_DATA_DIR / target_file_path / str(commit_date)
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # CSV保存
        centrality_df.to_csv(output_dir / path_config.CENTRALITY_CSV, index=False)

    def filter_metadata_monthly(
        self, commit_hashes: list[str], commit_dates: list[datetime]
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

        current_target = start_date + timedelta(days=30)
        idx = 1

        while current_target < end_date and idx < len(commit_dates):
            while idx < len(commit_dates) and commit_dates[idx] < current_target:
                idx += 1
            if idx < len(commit_dates):
                selected_indices.append(idx)
            current_target += timedelta(days=30)

        if selected_indices[-1] != len(commit_dates) - 1:
            selected_indices.append(len(commit_dates) - 1)

        # インデックスを使って分離リストに変換
        filtered_hashes: list[str] = [commit_hashes[i] for i in selected_indices]
        filtered_dates: list[datetime] = [commit_dates[i] for i in selected_indices]

        return filtered_hashes, filtered_dates

    def extract_commit_metadata(
        self, file_path: Path
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
                f"git log --all --full-history --reverse --pretty=format:%H,%aI -- {file_path}"
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

    def main(self) -> None:
        ef = ExtractFilesInfo(path_config.REPO_DIR, path_config.DATA_DIR)

        # 2024年の最終コミット日時にリポジトリを戻す
        last_commit_metadata: str = self.get_last_commit_date(
            repo_path=path_config.REPO_DIR, limit_year="2025"
        )
        last_commit_hash: str = last_commit_metadata.split("|")[0]
        self.shell_command.run_cmd(
            cmd=f"git reset --hard {last_commit_hash}", cwd=path_config.REPO_DIR
        )

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
        for file_path in tqdm(
            random_existing_files_list,
            desc="ファイルを1件ずつ処理中",
            dynamic_ncols=True,
        ):
            commit_hashes, commit_dates = self.extract_commit_metadata(
                file_path=file_path
            )
            filtered_hashes, filtered_dates = self.filter_metadata_monthly(
                commit_hashes, commit_dates
            )

            for commit_hash, commit_date in zip(filtered_hashes, filtered_dates):
                # コミットIDの状態にリポジトリを戻す
                self.shell_command.run_cmd(
                    cmd=f"git reset --hard {commit_hash}", cwd=path_config.REPO_DIR
                )
                # 全ファイルを取得
                file_df = ef.extract_file_info(
                    cwd=path_config.REPO_DIR, language="java"
                )
                # 中心性スコアを計算
                if not file_df.empty:
                    self.analyze_centrality_from_df(
                        file_df,
                        path_config.REPO_DIR,
                        max_files=20000,
                        commit_date=commit_date,
                        target_file_path=file_path,
                    )
                else:
                    print("ファイルが見つかりませんでした。")

            # 中心性の時系列変化を可視化
            visualize_centrality = VisualizeCentrality()
            visualize_centrality.main(target_file=file_path)


class VisualizeCentrality:
    def main(self, target_file: Path) -> None:
        file_path: Path = path_config.CENTRALITY_DATA_DIR / target_file
        data: list = []

        # コミット日時のリストを取得
        commit_dates: list[Path] = [p.name for p in file_path.iterdir() if p.is_dir()]
        sorted_commit_dates: list[str] = sorted(
            commit_dates, key=datetime.fromisoformat
        )

        # 対象ファイルの中心性スコアを取得
        for sorted_commit_date in sorted_commit_dates:
            output_dir: Path = (
                path_config.CENTRALITY_DATA_DIR
                / target_file
                / sorted_commit_date
                / path_config.CENTRALITY_CSV
            )
            centrality_df = pd.read_csv(output_dir)

            # 対象ファイル名が含まれる行を抽出（部分一致）
            target_row = centrality_df[
                centrality_df[path_config.EXISTING_FILE_COLUMNS].str.endswith(
                    str(target_file).replace("_", "/")
                )
            ]

            if not target_row.empty:
                centrality_score = target_row[path_config.CENTRALITY_COLUMNS].iloc[0]
                commit_date: str = sorted_commit_date

                data.append(
                    {
                        path_config.COMMIT_DATE_COLUMNS: commit_date,
                        path_config.CENTRALITY_COLUMNS: centrality_score,
                    }
                )

        # ------- DataFrameへ変換・整形 -------
        df_plot = pd.DataFrame(data)
        df_plot[path_config.COMMIT_DATE_COLUMNS] = pd.to_datetime(
            df_plot[path_config.COMMIT_DATE_COLUMNS], utc=True
        )

        # ------- グラフ描画 -------
        sns.set(style="whitegrid")
        plt.figure(figsize=(10, 6))
        sns.lineplot(
            data=df_plot,
            x=path_config.COMMIT_DATE_COLUMNS,
            y=path_config.CENTRALITY_COLUMNS,
            marker="o",
        )

        file_name: str = Path(str(target_file).replace("_", "/")).stem
        plt.title(f"Time-series changes in the centrality score for {file_name} ")
        plt.xlabel(path_config.COMMIT_DATE_COLUMNS)
        plt.ylabel(path_config.CENTRALITY_COLUMNS)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(
            path_config.CENTRALITY_DATA_DIR
            / target_file
            / path_config.CENTRALITY_CHANGES_CSV,
            dpi=300,
        )


if __name__ == "__main__":
    calc_centrality = CalcCentrality()
    calc_centrality.main()
