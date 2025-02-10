import os
import shutil
from pathlib import Path

import pandas as pd

from shopy import GitHash, GitReset, path_config


class StoreFiles:

    def open_file(self):
        df = pd.read_csv(path_config.DELETED_FILES_INFO_CSV)
        for index, deleted_file_path in enumerate(df['Deleted File Path'].values):
            commit_hashes = GitHash.get_commit_hashes(
                self, file_path=deleted_file_path, cwd=path_config.REPO_DIR)
            latest_commit = commit_hashes[0]
            if latest_commit is None:
                continue
            GitReset.git_reset(
                self, commit_hash=commit_hashes[0], cwd=path_config.REPO_DIR)
            os.makedirs(path_config.DELETED_FILES, exist_ok=True)
