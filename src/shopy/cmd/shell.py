import subprocess


class ShellCommand:
    def run_cmd(self, cmd: str, cwd: str) -> str:
        """シェルコマンドを実行し、結果を返す

        Args:
            cmd (str): 実行コマンド
            cwd (str): 実行ディレクトリ

        Returns:
            str: コマンドの実行結果
        """
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
                cwd=cwd,
            )
            return result.stdout.strip().splitlines()
        except subprocess.CalledProcessError as e:
            print(f"エラーが発生しました。: {e.stderr}")
            return ""
        except Exception as e:
            print(f"予期しないエラーが発生しました。: {e}")
            return ""
