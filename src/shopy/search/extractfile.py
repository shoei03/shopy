import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from shopy import ShellCommand, path_config


class ExtractFilesInfo:
    def __init__(self, repo_dir, projects_data_dir):
        self.repo_dir = repo_dir
        self.projects_data_dir = projects_data_dir
        self.shell_command: ShellCommand = ShellCommand()

    def extract_deleted_file_info(self, cwd, language="java"):
        """削除されたファイルの情報を取得

        Args:
            cwd (str): ファイルを取得するリポジトリのディレクトリパス
            language (str, optional): どの言語のファイルを対象とするか. Defaults to "java".

        Returns:
            DataFrame: 削除されたファイルの情報を含むDataFrame
        """
        # 削除されたファイルの情報を取得
        lines = self.shell_command.run_cmd(
            cmd="git log --diff-filter=D --name-status --pretty=format:'%H|%aI|%s'",
            cwd=cwd,
        )
        deleted_files_info: list = []
        for line in lines:
            if "|" in line:
                commit_id, commit_date, commit_message = line.split("|", 2)
                utc_commit_date = datetime.fromisoformat(commit_date).astimezone(
                    timezone.utc
                )
            elif line.startswith("D\t") and line.endswith(f".{language}"):
                deleted_files_info.append(
                    {
                        path_config.COMMIT_ID_COLUMNS: commit_id,
                        path_config.COMMIT_DATE_COLUMNS: utc_commit_date,
                        path_config.COMMIT_MESSAGE_COLUMNS: commit_message,
                        # Remove the "D\t" prefix
                        path_config.DELETED_FILE_COLUMNS: line[2:],
                        path_config.IS_DELETED_COLUMNS: True,
                    }
                )

        return pd.DataFrame(deleted_files_info)

    def extract_file_info(self, cwd, language="java"):
        """残存ファイルの情報を取得

        Args:
            cwd (str): ファイルを取得するリポジトリのディレクトリパス
            language (str, optional): どの言語のファイルを対象とするか. Defaults to "java".

        Returns:
            DataFrame: 残存ファイルの情報を含むDataFrame
        """
        # 残存ファイルの情報を取得
        lines = self.shell_command.run_cmd("git ls-tree -r --name-only HEAD", cwd=cwd)
        files_info: list = []
        for line in lines:
            if line.endswith(f".{language}"):
                files_info.append(
                    {
                        path_config.EXISTING_FILE_COLUMNS: line,
                        path_config.IS_DELETED_COLUMNS: False,
                    }
                )

        return pd.DataFrame(files_info)

    def main(self, isDeleted=False):
        if isDeleted:
            file_type = "deleted_files"
            output_dir = Path(self.projects_data_dir, file_type)
            os.makedirs(output_dir, exist_ok=True)
            deleted_files_info = self.extract_deleted_file_info(self.repo_dir)
            deleted_files_info.to_csv(
                Path(output_dir / f"{file_type}_info.csv"), index=False
            )
        else:
            file_type = "existing_files"
            output_dir = Path(self.projects_data_dir, file_type)
            os.makedirs(output_dir, exist_ok=True)
            java_files_info = self.extract_file_info(self.repo_dir)
            java_files_info.to_csv(
                Path(output_dir / f"{file_type}_info.csv"), index=False
            )
