from pathlib import Path

import networkx as nx
import pandas as pd
from tqdm import tqdm

from shopy import ExtractFilesInfo, GetName, ShellCommand, path_config


class CalcCentrality:
    def __init__(self):
        self.shell_command = ShellCommand()

    def build_dependency_graph(
        self, java_files: list[Path], max_files: int = 20000
    ) -> tuple[nx.DiGraph, dict[Path, str]]:
        G = nx.DiGraph()
        get_name = GetName()
        file_to_fqn = {}

        # データ数が多い場合はサンプリング
        sampled_files = (
            java_files[:max_files] if len(java_files) > max_files else java_files
        )

        # パッケージ名を取得してノードを追加
        for file in tqdm(sampled_files, desc="FQN抽出", leave=False):
            fqn = get_name.get_fqn(file, base_package_prefix=path_config.PACKAGE_PREFIX)
            if fqn:
                file_to_fqn[file] = fqn
                G.add_node(fqn)

        # import文を取得してエッジを追加
        for file, src_fqn in tqdm(file_to_fqn.items(), desc="依存関係解析", leave=False):
            for imp in get_name.extract_imports(file):
                if imp.startswith(path_config.PACKAGE_PREFIX):
                    G.add_edge(src_fqn, imp)

        return G, file_to_fqn

    def analyze_centrality_from_df(
        self,
        file_df: pd.DataFrame,
        cwd: Path,
        max_files: int = 2000,
        commit_date: str = "",
        target_file_path: str = "",
    ) -> None:
        java_files: list[Path] = [
            cwd / Path(f) for f in file_df["Existing File Path"].tolist()
        ]
        graph, file_to_fqn = self.build_dependency_graph(
            java_files, max_files=max_files
        )
        centrality = nx.pagerank(graph)

        # FQN列を追加
        file_df["FQN"] = file_df["Existing File Path"].map(
            lambda p: file_to_fqn.get(cwd / Path(p), "")
        )

        # 中心性スコア列を追加（FQNに対応するもののみ）
        file_df["centrality_score"] = file_df["FQN"].map(centrality).fillna(0.0)

        # 中心性スコア順にソート
        centrality_df = file_df[
            ["centrality_score", "FQN", "Existing File Path"]
        ].sort_values(by="centrality_score", ascending=False)

        # 保存先ディレクトリを確保
        target_file_path = target_file_path.replace("/", "_")
        output_dir = Path(path_config.CENTRALITY_DATA_DIR / target_file_path / commit_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        # CSV保存
        centrality_df.to_csv(output_dir / "centrality_scores.csv", index=False)

    def main(self) -> None:
        ef = ExtractFilesInfo(path_config.REPO_DIR, path_config.DATA_DIR)

        existing_files_df = pd.read_csv(
            path_config.EXISTING_FILES_INFO_CSV,
            encoding="utf-8",
        )

        # 1ファイルずつ処理
        for file_path in tqdm(
            existing_files_df["Existing File Path"], desc="ファイルを1件ずつ処理中"
        ):
            # ファイルのコミットID、日時を取得（古い順）
            _commit_logs: list[str] = self.shell_command.run_cmd(
                cmd=f"git log --all --full-history --reverse --pretty=format:%H,%ad --date=iso -- {file_path}",
                cwd=path_config.REPO_DIR,
            )
            commit_hashes, commit_dates = zip(
                *(log.split(",", 1) for log in _commit_logs)
            )
            commit_hashes: list[str] = list(commit_hashes)
            commit_dates: list[str] = list(commit_dates)

            for commit_hash, commit_date in zip(commit_hashes, commit_dates):
                # コミットIDの状態にリポジトリを戻す
                self.shell_command.run_cmd(
                    cmd=f"git reset --hard {commit_hash}", cwd=path_config.REPO_DIR
                )

                file_df = ef.extract_java_file_info(
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
                    print("Javaファイルが見つかりませんでした。")

class VisualizeCentrality:
    def main(self) -> None:
        # 中心性スコアのCSVを読み込む
        centrality_df = pd.read_csv(
            path_config.CENTRALITY_DATA_DIR / "centrality_scores.csv"
        )


if __name__ == "__main__":
    calc_centrality = CalcCentrality()
    calc_centrality.main()
