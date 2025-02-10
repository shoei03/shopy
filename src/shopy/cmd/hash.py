import subprocess


class GitHash:

    def get_commit_hashes(self, file_path: str, cwd: str) -> list:
        """
        コミットハッシュを取得
        """
        try:
            result = subprocess.run(
                [
                    "git", "log", "--all", "--full-history", "--pretty=format:%H", "--", file_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
                cwd=cwd
            )

            return result.stdout.splitlines()

        except subprocess.CalledProcessError as e:
            print(f"エラーが発生しました。: {e.stderr}")
            return []

    def get_latest_commit_hashes(self, file_path: str, cwd: str) -> str:
        """
        最新から一つ前のコミットハッシュを取得
        """
        try:
            result = subprocess.run(
                [
                    "git", "log", "--format=%H", "-n", "2", "--", file_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
                cwd=cwd
            )

            commits = result.stdout.strip().split("\n")
            print(commits)

            if len(commits) < 2:
                return None

            latest_commit = commits[0]
            previous_commit = commits[1]

            return previous_commit

        except subprocess.CalledProcessError as e:
            print(f"エラーが発生しました。: {e.stderr}")
            return []
