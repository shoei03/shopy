from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathConfig:
    ORGANIZATION: str = "iluwatar"
    REPO_NAME: str = "java-design-patterns"
    ROOT_DIR: Path = Path(__file__).parents[3]
    DATA_DIR: Path = ROOT_DIR / "data"
    PROJECTS_DATA_DIR: Path = DATA_DIR / REPO_NAME
    DELETED_FILES_DATA_DIR: Path = PROJECTS_DATA_DIR / "deleted_files"
    DELETED_FILES: Path = DELETED_FILES_DATA_DIR / "files"
    DELETED_FILES_INFO_CSV: Path = DELETED_FILES_DATA_DIR / "deleted_files_info.csv"
    EXSISTING_FILES_DATA_DIR: Path = PROJECTS_DATA_DIR / "existing_files"
    EXSISTING_FILES: Path = EXSISTING_FILES_DATA_DIR / "files"
    EXSISTING_FILES_INFO_CSV: Path = EXSISTING_FILES_DATA_DIR / "existing_files_info.csv"
    PROJECTS_DIR: Path = ROOT_DIR.parent / "projects"
    REPO_DIR: Path = PROJECTS_DIR / REPO_NAME


path_config = PathConfig()
