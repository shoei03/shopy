from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from tqdm import tqdm

import shopy as sp
from shopy import ExtractFilesInfo, GetName, path_config


class CalcCentrality:
    def write_repo_metadata(
        self, input_dir: Path, start_date: str, end_date: str, output_dir: Path
    ) -> None:
        """リポジトリの月次データを取得し、CSVに保存する

        Args:
            input_dir (Path): リポジトリまでのパス
            start_date (str): 収集の開始日
            end_date (str): 収集の終了日
        """
        # リポジトリの月次データを取得
        filtered_hashes, filtered_dates = sp.get_monthly_commits(
            repo_path=input_dir,
            start_date=start_date,
            end_date=end_date,
        )
        # CSVに保存
        repo_metadata_df = pd.DataFrame(
            {
                path_config.COMMIT_DATE_COLUMNS: filtered_dates,
                path_config.COMMIT_ID_COLUMNS: filtered_hashes,
            }
        )
        repo_metadata_df.to_csv(
            output_dir,
            index=False,
        )

    def read_repo_metadata(self, input_dir: Path) -> tuple[list[str], list[str]]:
        """リポジトリの月次データを取得する

        Args:
            input_dir (Path): リポジトリまでのパス

        Returns:
            tuple: コミットハッシュとコミット日時のリスト
        """
        repo_metadata_df = pd.read_csv(
            input_dir,
        )
        filtered_dates: list[datetime] = repo_metadata_df[
            path_config.COMMIT_DATE_COLUMNS
        ].tolist()
        filtered_hashes: list[str] = repo_metadata_df[
            path_config.COMMIT_ID_COLUMNS
        ].tolist()

        return filtered_hashes, filtered_dates

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
        sp.reset_repo_state(
            repo_path=path_config.REPO_DIR,
            commit_hash=state,
        )

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
        sp.write_json(
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

    def write_centrality(self, file_dependency: dict, output_dir: Path) -> None:
        """中心性を計算し、CSVに保存する

        Args:
            input_dir (Path): 依存関係が記述されたJSONファイルのパス
            output_dir (Path): 出力先のディレクトリ
        """
        # グラフ構築
        graph = self.build_dependency_graph(file_dependency)
        centrality = nx.pagerank(graph)

        # DataFrame化
        df = pd.DataFrame(
            {
                path_config.FULL_PACKAGE_COLUMNS: list(centrality.keys()),
                path_config.CENTRALITY_COLUMNS: list(centrality.values()),
            }
        )

        score_col = path_config.CENTRALITY_COLUMNS
        original_scores = df[score_col]

        # 1. L2正規化
        l2_norm = np.linalg.norm(original_scores)
        df[path_config.CENTRALITY_L2_COLUMNS] = (
            original_scores / l2_norm if l2_norm != 0 else 0
        )

        # 2. Zスコア標準化
        mean = original_scores.mean()
        std = original_scores.std()
        df[path_config.CENTRALITY_Z_COLUMNS] = (
            (original_scores - mean) / std if std != 0 else 0
        )

        # 3. Min-Max正規化
        min_val = original_scores.min()
        max_val = original_scores.max()
        df[path_config.CENTRALITY_MIN_MAX_COLUMNS] = (
            (original_scores - min_val) / (max_val - min_val)
            if max_val != min_val
            else 0
        )

        # 4. ログスケール（log1p = log(1 + x), 0の処理も安全）
        df[path_config.CENTRALITY_LOG_COLUMNS] = np.log1p(original_scores)

        # スコアで降順ソート
        df_sorted = df.sort_values(by=score_col, ascending=False)

        # 保存先ディレクトリの作成
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        df_sorted.to_csv(output_dir, index=False)

    def load_centrality_timeseries(self, input_dir: Path, output_dir: Path) -> None:
        """クラスごとの中心性スコアの時系列データを作成し、CSVに保存

        Args:
            input_dir (Path): 各時点の中心性スコアが保存されたディレクトリ
            output_dir (Path): 出力先のディレクトリ
        """
        # スコア名ごとの一時保存用辞書
        score_records: dict[str, list[pd.DataFrame]] = defaultdict(list)

        for subdir in sorted(sp.get_child_dir(input_dir)):
            try:
                timestamp = pd.to_datetime(subdir, utc=True)
            except Exception:
                print(f"スキップ（無効な日付）: {subdir}")
                continue

            input_csv = input_dir / str(timestamp) / path_config.CENTRALITY_CSV

            try:
                df = pd.read_csv(input_csv)

                if path_config.FULL_PACKAGE_COLUMNS not in df.columns:
                    print(
                        f"警告: {input_csv} に '{path_config.FULL_PACKAGE_COLUMNS}' 列が存在しません。"
                    )
                    continue

                # "centrality_" で始まる列を抽出
                score_columns = [
                    col for col in df.columns if col.startswith("centrality_")
                ]

                for score_col in score_columns:
                    temp_df = df[[path_config.FULL_PACKAGE_COLUMNS, score_col]].copy()
                    temp_df[path_config.COMMIT_DATA_KEY] = timestamp.isoformat()
                    score_records[score_col].append(temp_df)

            except Exception as e:
                print(f"読み込みエラー: {input_csv} → {e}")
                continue

        # 出力ディレクトリの作成
        output_dir.mkdir(parents=True, exist_ok=True)

        for score_col, dataframes in score_records.items():
            combined_df = pd.concat(dataframes, ignore_index=True)

            timeseries_df = combined_df.pivot(
                index=path_config.FULL_PACKAGE_COLUMNS,
                columns=path_config.COMMIT_DATA_KEY,
                values=score_col,
            ).sort_index(axis=1)

            output_csv = output_dir / f"{score_col}.csv"
            timeseries_df.to_csv(output_csv)

    def plot_all_centralities_per_class(
        self, centrality_dir: Path, output_base_dir: Path
    ) -> None:
        """中心性スコアの時系列データを可視化する

        Args:
            centrality_dir (Path): 中心性スコアの時系列データが保存されたディレクトリ
            output_base_dir (Path): 出力先のディレクトリ
        """
        csv_paths = sorted(centrality_dir.glob("*.csv"))

        for csv_path in csv_paths:
            score_name = csv_path.stem
            df = pd.read_csv(csv_path, index_col=0)
            df.columns = pd.to_datetime(df.columns)

            # クラス名（FQN）一覧を抽出
            class_list = df.index.tolist()

            output_dir = output_base_dir / score_name
            output_dir.mkdir(parents=True, exist_ok=True)

            for fqn in tqdm(
                class_list,
                desc=f"{score_name} をプロット中",
                leave=True,
                dynamic_ncols=True,
            ):
                series = df.loc[fqn]
                data = pd.DataFrame(
                    {
                        path_config.COMMIT_DATA_KEY: series.index,
                        score_name: series.values,
                    }
                )

                plt.figure(figsize=(10, 5))
                plt.plot(
                    data[path_config.COMMIT_DATA_KEY],
                    data[score_name],
                    color="lightblue",
                    marker="o",
                    linestyle="-",
                    markersize=4,  # 点の大きさを小さく
                )

                plt.title(
                    f"{score_name} Over Time\n{fqn}".replace("$", "\\$"), fontsize=14
                )  # タイトルサイズ大
                plt.xlabel("Time", fontsize=12)  # ラベルサイズ中
                plt.ylabel(score_name, fontsize=12)
                plt.xticks(rotation=45, fontsize=10)  # 目盛サイズ
                plt.yticks(fontsize=10)
                plt.tight_layout()

                safe_name = sp.sanitize_filename(fqn)
                save_path = output_dir / f"{safe_name}.png"
                plt.savefig(save_path)
                plt.close()

    def main(self) -> None:
        # # 2024年の最終コミット日時にリポジトリを戻す
        # last_commit_hash, _ = sp.get_last_commit_date(
        #     repo_path=path_config.REPO_DIR, limit_year="2025"
        # )
        # sp.reset_repo_state(
        #     repo_path=path_config.REPO_DIR,
        #     commit_hash=last_commit_hash,
        # )

        # # リポジトリの月次データを取得し、CSVに保存
        # self.write_repo_metadata(
        #     input_dir=path_config.REPO_DIR,
        #     start_date="2008-01-01",
        #     end_date="2024-12-31",
        #     output_dir=path_config.PROJECTS_DATA_DIR / path_config.MONTHLY_COMMITS_CSV,
        # )

        # # リポジトリの月次データを読み込み
        # filtered_hashes, filtered_dates = self.read_repo_metadata(
        #     input_dir=path_config.PROJECTS_DATA_DIR / path_config.MONTHLY_COMMITS_CSV
        # )

        # # ファイルの依存関係を計算し、jsonで保存
        # for commit_hash, commit_date in tqdm(
        #     zip(filtered_hashes, filtered_dates),
        #     desc="特定のコミットを処理中",
        #     total=len(filtered_hashes),
        #     leave=False,
        # ):
        #     try:
        # output_path: Path = path_config.CENTRALITY_DATA_DIR / str(commit_date)

        # # 依存関係を構築し、jsonで保存(この処理は非常に時間がかかる)
        # self.build_dependency(
        #     max_files=20000,
        #     input_dir=path_config.REPO_DIR,
        #     language="java",
        #     output_dir=(output_path / path_config.FILE_DEPENDENCY_JSON),
        #     state=commit_hash,
        # )

        # # 依存関係のjsonを読み込み
        # file_dependency = sp.read_json(
        #     input_dir=(output_path / path_config.FILE_DEPENDENCY_JSON)
        # )

        # # 依存関係から中心性を計算し、csvで保存
        # self.write_centrality(
        #     file_dependency=file_dependency,
        #     output_dir=(output_path / path_config.CENTRALITY_CSV),
        # )

        # except Exception as e:
        #     print(
        #         f"[ERROR] コミット処理中にエラーが発生しました。 {commit_hash}: {e}"
        #     )
        #     continue

        # # 中心性スコアの時系列データを作成し、CSVに保存
        # self.load_centrality_timeseries(
        #     input_dir=path_config.CENTRALITY_DATA_DIR,
        #     output_dir=path_config.CENTRALITY_MATRIX_DIR,
        # )

        # 中心性スコアの時系列データを可視化
        self.plot_all_centralities_per_class(
            centrality_dir=path_config.CENTRALITY_MATRIX_DIR,
            output_base_dir=path_config.CENTRALITY_CHANGE_DIR,
        )


if __name__ == "__main__":
    calc_centrality = CalcCentrality()
    calc_centrality.main()
