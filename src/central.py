from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import seaborn as sns
from dateutil.relativedelta import relativedelta
from tqdm import tqdm

from shopy import JSON, ExtractFilesInfo, GetName, ShellCommand, path_config


class CalcCentrality:
    def __init__(self):
        self.shell_command = ShellCommand()
        self.json = JSON()

    def build_dependency(
        self,
        input_dir: Path = path_config.REPO_DIR,
        language: str = "java",
        max_files: int = 20000,
        output_dir: Path = path_config.CENTRALITY_DATA_DIR,
        state: str = "HEAD",
    ) -> None:
        """ファイルの依存関係を取得する

        Args:
            cwd (Path, optional): リポジトリまでのパス. Defaults to path_config.REPO_DIR.
            language (str, optional): 対象言語. Defaults to "java".
            max_files (int, optional): 最大ファイル数. Defaults to 20000.

        Returns:
            dict: ファイルの依存関係
        """
        # コミットハッシュの状態にリポジトリを戻す
        self.shell_command.run_cmd(
            cmd=f"git reset --hard {state}",
            cwd=path_config.REPO_DIR,
        )
        sleep(2)

        # ファイル情報を取得
        ef = ExtractFilesInfo(path_config.REPO_DIR, path_config.DATA_DIR)
        file_df = ef.extract_file_info(cwd=input_dir, language=language)

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
                "fqn": get_name.find_fqn(
                    input_dir, file_path, path_config.PACKAGE_PREFIX
                ),
                "imp": get_name.extract_imports(input_dir, file_path),
            }
            for file_path in tqdm(
                sampled_files, desc="依存関係解析", leave=False, dynamic_ncols=True
            )
        }

        processed_file_dependency = {str(k): v for k, v in file_dependency.items()}
        self.json.write_json(
            dict=processed_file_dependency,
            output_dir=output_dir,
        )

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

    def get_monthly_commits(
        self,
        repo_path: str,
        branch: str = "main",
        start_date: str = "2023-01-01",
        end_date: str = "2024-12-31",
    ) -> dict[str, tuple[str, str]]:
        """
        各月の最後のコミットのハッシュとUTCのISO形式日時を取得する

        Returns:
            dict[str, tuple[commit_hash, commit_date]]
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        monthly_commits: dict[str, tuple[str, str]] = {}
        current = start

        while current <= end:
            next_month = current + relativedelta(months=1)
            since = current.strftime("%Y-%m-%d")
            until = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")

            cmd = (
                f"git log {branch} "
                f'--after="{since}" --before="{until}" '
                f"--pretty=format:'%H|%aI' --reverse"
            )

            commits = self.shell_command.run_cmd(cmd, cwd=repo_path)
            if commits:
                last_commit_line = commits[-1]
                if "|" in last_commit_line:
                    commit_hash, commit_date = last_commit_line.split("|", 1)
                    commit_date_utc = datetime.fromisoformat(commit_date).astimezone(
                        timezone.utc
                    )
                    monthly_key = since[:7]
                    monthly_commits[monthly_key] = (commit_hash, commit_date_utc)

            current = next_month

        return monthly_commits

    def get_child_dir(self, path: Path) -> list[Path]:
        """指定したパスの子ディレクトリを取得する

        Args:
            path (Path): 対象のパス

        Returns:
            list[Path]: 子ディレクトリのリスト
        """
        return [p.name for p in path.iterdir() if p.is_dir()]

    def create_centrality(self, input_dir: Path, output_dir: Path) -> None:
        """中心性を計算し、CSVに保存する

        Args:
            input_dir (Path): 依存関係が記述されたJSONファイルのパス
            output_dir (Path): 出力先のディレクトリ
        """
        # 依存関係のJSONファイルを読み込む
        file_dependency = self.json.read_json(
            input_dir=(input_dir / "file_dependency.json")
        )

        # 中心性スコアを計算する
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

        # 中心性スコアをCSVに保存
        sorted_centrality_df.to_csv(
            output_dir / path_config.CENTRALITY_CSV, index=False
        )

    def create_repo_metadata(
        self, input_dir: Path, start_date: str, end_date: str
    ) -> None:
        # リポジトリの月次データを取得
        commits = self.get_monthly_commits(
            repo_path=path_config.REPO_DIR,
            start_date=start_date,
            end_date=end_date,
        )
        sorted_months = sorted(commits.keys())
        filtered_hashes = [commits[month][0] for month in sorted_months]
        filtered_dates = [commits[month][1] for month in sorted_months]
        repo_metadata_df = pd.DataFrame(
            {
                path_config.COMMIT_DATE_COLUMNS: filtered_dates,
                path_config.COMMIT_ID_COLUMNS: filtered_hashes,
            }
        )
        # CSVに保存
        repo_metadata_df.to_csv(
            path_config.PROJECTS_DATA_DIR / "monthly_commits.csv",
            index=False,
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

    def get_last_commit_date(self, repo_path: Path, limit_year: str) -> str:
        all_commits: list[str] = self.shell_command.run_cmd(
            cmd=f"git log --before={limit_year}-01-01T00:00:00+00:00 --pretty=format:'%H|%aI' --reverse",
            cwd=repo_path,
        )
        return all_commits[-1]

    def load_centrality_timeseries(self, input_dir: Path, output_dir: Path) -> None:
        """
        クラスごとの中心性スコアの時系列データフレームを作成する。
        欠損値はNaNのままとする。

        :param input_dir: 各時点の中心性スコアCSVが格納されたディレクトリ
        :return: index=FQN, columns=timestamp, value=centrality_score のDataFrame
        """
        all_records = []

        for subdir_name in sorted(self.get_child_dir(input_dir)):
            timestamp = pd.to_datetime(subdir_name, utc=True)
            csv_path = input_dir / str(subdir_name) / "centrality_scores.csv"

            if not csv_path.exists():
                continue

            try:
                df = pd.read_csv(csv_path, usecols=["FQN", "centrality_score"])
                df["timestamp"] = str(timestamp)
                all_records.append(df)
            except Exception as e:
                print(f"読み込みエラー: {csv_path} → {e}")

        if not all_records:
            raise FileNotFoundError(
                "有効な centrality_scores.csv が見つかりませんでした。"
            )

        combined = pd.concat(all_records, ignore_index=True)

        timeseries_df = combined.pivot(
            index="FQN", columns="timestamp", values="centrality_score"
        ).sort_index(axis=1)

        timeseries_df.to_csv(output_dir / "centrality_timeseries.csv")

    def main(self) -> None:
        # 2024年の最終コミット日時にリポジトリを戻す
        last_commit_metadata: str = self.get_last_commit_date(
            repo_path=path_config.REPO_DIR, limit_year="2025"
        )
        last_commit_hash: str = last_commit_metadata.split("|")[0]
        self.shell_command.run_cmd(
            cmd=f"git reset --hard {last_commit_hash}", cwd=path_config.REPO_DIR
        )
        sleep(2)

        # リポジトリの月次データを取得し、CSVに保存
        self.create_repo_metadata(
            input_dir=path_config.REPO_DIR,
            start_date="2008-01-01",
            end_date="2024-12-31",
        )

        # ファイルの依存関係を計算し、jsonで保存
        repo_metadata_df = pd.read_csv(
            path_config.PROJECTS_DATA_DIR / "monthly_commits.csv"
        )
        filtered_dates: list[datetime] = repo_metadata_df[
            path_config.COMMIT_DATE_COLUMNS
        ].tolist()
        filtered_hashes: list[str] = repo_metadata_df[
            path_config.COMMIT_ID_COLUMNS
        ].tolist()
        for commit_hash, commit_date in tqdm(
            zip(filtered_hashes, filtered_dates),
            desc="特定のコミットを処理中",
            total=len(filtered_hashes),
            leave=False,
        ):
            try:
                output_path: Path = (
                    path_config.CENTRALITY_DATA_DIR
                    / str(commit_date)
                    / "file_dependency.json"
                )
                self.build_dependency(
                    max_files=20000,
                    input_dir=path_config.REPO_DIR,
                    language="java",
                    output_dir=output_path,
                    state=commit_hash,
                )

            except Exception as e:
                print(
                    f"[ERROR] コミット処理中にエラーが発生しました。 {commit_hash}: {e}"
                )
                continue

        # 中心性スコアを計算し、CSVに保存
        filtered_dates: list[Path] = self.get_child_dir(path_config.CENTRALITY_DATA_DIR)
        for commit_date in filtered_dates:
            input_dir: Path = path_config.CENTRALITY_DATA_DIR / str(commit_date)
            output_dir: Path = path_config.CENTRALITY_DATA_DIR / str(commit_date)
            self.create_centrality(input_dir=input_dir, output_dir=output_dir)

        # 中心性スコアの時系列データを作成し、CSVに保存
        self.load_centrality_timeseries(
            input_dir=path_config.CENTRALITY_DATA_DIR,
            output_dir=path_config.EXISTING_FILES_DATA_DIR,
        )


if __name__ == "__main__":
    calc_centrality = CalcCentrality()
    calc_centrality.main()
