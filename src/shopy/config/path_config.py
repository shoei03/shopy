from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathConfig:
    ORGANIZATION: str = "iluwatar"
    REPO_NAME:    str = "java-design-patterns"
    
    ROOT_DIR:     Path = Path(__file__).parents[3]
    PROJECTS_DIR: Path = ROOT_DIR.parent / "projects"
    REPO_DIR:     Path = ROOT_DIR.parent / "projects" / REPO_NAME
    
    DATA_DIR:                 Path = ROOT_DIR / "data"
    PROJECTS_DATA_DIR:        Path = ROOT_DIR / "data" / REPO_NAME
    DELETED_FILES_DATA_DIR:   Path = ROOT_DIR / "data" / REPO_NAME / "deleted_files"
    DELETED_FILES:            Path = ROOT_DIR / "data" / REPO_NAME / "deleted_files" / "files"
    DELETED_FILES_INFO_CSV:   Path = ROOT_DIR / "data" / REPO_NAME / "deleted_files" / "deleted_files_info.csv"
    EXISTING_FILES_DATA_DIR:  Path = ROOT_DIR / "data" / REPO_NAME / "existing_files"
    EXISTING_FILES:           Path = ROOT_DIR / "data" / REPO_NAME / "existing_files" / "files"
    EXISTING_FILES_INFO_CSV:  Path = ROOT_DIR / "data" / REPO_NAME / "existing_files" / "existing_files_info.csv"
    


path_config = PathConfig()
