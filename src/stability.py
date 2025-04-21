import csv
import subprocess
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from shopy import path_config


class StabilityCalculator:
    def __init__(self, repo_path: str, frec: float = 0.67, weight_min: float = 0.1):
        self.repo_path = Path(repo_path)
        self.frec = frec
        self.weight_min = weight_min
        self.commit_hashes = []
        self.file_commit_map = defaultdict(list)
        self.commit_weights = {}

    def run_git_command(self, args):
        result = subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result.check_returncode()
        return result.stdout.strip()

    def extract_commits(self):
        log = self.run_git_command(["log", "--reverse", "--pretty=format:%H"])
        self.commit_hashes = log.splitlines()
        print(f"Total commits: {len(self.commit_hashes)}")

    def map_file_changes(self):
        for idx, commit_hash in tqdm(
            enumerate(self.commit_hashes),
            total=len(self.commit_hashes),
            desc="Mapping file changes",
        ):
            diff = self.run_git_command(
                ["diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash]
            )
            files = diff.splitlines()
            for file in files:
                if file.endswith(".java"):
                    self.file_commit_map[file].append(idx)

    def calculate_stability_scores(self):
        n_total = len(self.commit_hashes)
        n_recent = int(self.frec * n_total)
        recent_commit_indexes = set(range(n_total - n_recent, n_total))

        weights = {}
        for idx in recent_commit_indexes:
            relative_pos = idx - (n_total - n_recent)
            weight = (1 - self.weight_min) * (relative_pos / n_recent) + self.weight_min
            weights[idx] = weight

        self.commit_weights = weights  # 保存するために保持

        total_weight = sum(weights.values())
        stability_scores = {}

        for file, commits in self.file_commit_map.items():
            score = sum(weights.get(cidx, 0) for cidx in commits)
            # change_score = score / total_weight if total_weight > 0 else 0
            # stability_scores[file] = 1 - change_score
            stability_scores[file] = score

        return stability_scores

    def save_commit_weights(self, path: str = "commit_weights.csv"):
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["commit_index", "commit_hash", "weight"])
            for idx in sorted(self.commit_weights):
                writer.writerow(
                    [idx, self.commit_hashes[idx], f"{self.commit_weights[idx]:.6f}"]
                )
        print(f"Saved commit weights to {path}")

    def save_stability_scores(
        self, scores: dict[str, float], path: str = "stability_scores.csv"
    ):
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["file_path", "stability_score"])
            for file, score in sorted(scores.items(), key=lambda x: -x[1]):
                writer.writerow([file, f"{score:.6f}"])
        print(f"Saved stability scores to {path}")

    def analyze(self):
        self.extract_commits()
        self.map_file_changes()
        return self.calculate_stability_scores()


if __name__ == "__main__":
    repo_path = path_config.REPO_DIR
    calculator = StabilityCalculator(repo_path)
    scores = calculator.analyze()
    calculator.save_commit_weights(
        Path(path_config.STABILITY_DATA_DIR / "commit_weights.csv")
    )
    calculator.save_stability_scores(
        scores, Path(path_config.STABILITY_DATA_DIR / "stability_scores.csv")
    )
