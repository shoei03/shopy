import os
import shutil
from pathlib import Path

import pandas as pd

from shopy import GitHash, GitReset, path_config


class StoreFiles:

    def save_deleted_file(self):
        df = pd.read_csv(path_config.DELETED_FILES_INFO_CSV)

        for index, deleted_file_path in enumerate(df['Deleted File Path'].values):
            commit_hashes = GitHash.get_commit_hashes(
                self, file_path=deleted_file_path, cwd=path_config.REPO_DIR)
            previous_commit = commit_hashes[1]
            if previous_commit is None:
                continue

            print(f"{index + 1}/{len(df)}: {deleted_file_path}")
            GitReset.git_reset(
                self, commit_hash=previous_commit, cwd=path_config.REPO_DIR)

            os.makedirs(path_config.DELETED_FILES, exist_ok=True)
            file_name = deleted_file_path.replace("/", "_")

            if Path(path_config.REPO_DIR / deleted_file_path).exists():
                shutil.copy(
                    path_config.REPO_DIR / deleted_file_path,
                    path_config.DELETED_FILES / file_name
                )
            else:
                continue

    def save_existing_file(self):
        df = pd.read_csv(path_config.EXISTING_FILES_INFO_CSV)

        for index, existing_file_path in enumerate(df['Existing File Path'].values):
            commit_hashes = GitHash.get_commit_hashes(
                self, file_path=existing_file_path, cwd=path_config.REPO_DIR)
            previous_commit = commit_hashes[1]
            if previous_commit is None:
                continue

            print(f"{index + 1}/{len(df)}: {existing_file_path}")
            GitReset.git_reset(
                self, commit_hash=previous_commit, cwd=path_config.REPO_DIR)

            os.makedirs(path_config.EXISTING_FILES, exist_ok=True)
            file_name = existing_file_path.replace("/", "_")

            if Path(path_config.REPO_DIR / existing_file_path).exists():
                shutil.copy(
                    path_config.REPO_DIR / existing_file_path,
                    path_config.EXISTING_FILES / file_name
                )
            else:
                continue
