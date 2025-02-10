import subprocess


class GitReset:

    def git_reset(self, commit_hash: str, cwd: str) -> bool:
        """
        コミットハッシュの状態にリポジトリを戻す
        """
        try:
            result = subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
                cwd=cwd
            )
            print("リポジトリの状態をリセットしました。")
            return True
        
        except subprocess.CalledProcessError as e:
            print(f"リポジトリの状態をリセットできませんでした。{e.stderr}")
            return False