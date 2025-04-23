from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathConfig:
    ORGANIZATION:   str = "spring-projects"
    REPO_NAME:      str = "spring-framework"
    PACKAGE_PREFIX: str = "org.springframework"
    
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
    CENTRALITY_DATA_DIR:      Path = ROOT_DIR / "data" / REPO_NAME / "centrality"
    CENTRALITY_CHANGE_DIR:    Path = ROOT_DIR / "data" / REPO_NAME / "centrality_changes"
    L1_CENTRALITY_DIR:        Path = ROOT_DIR / "data" / REPO_NAME / "centrality_changes" / "L1_norm"
    STABILITY_DATA_DIR:       Path = ROOT_DIR / "data" / REPO_NAME / "stability"

    MONTHLY_COMMITS_CSV:    str = "monthly_commits.csv"
    FILE_DEPENDENCY_JSON:   str = "file_dependency.json"
    CENTRALITY_CSV:         str = "centrality_scores.csv"
    CENTRALITY_CHANGE_CSV:  str = "centrality_timeseries.csv"

    EXISTING_FILE_COLUMNS:  str = "Existing File Path"
    DELETED_FILE_COLUMNS:   str = "Deleted File Path"
    IS_DELETED_COLUMNS:     str = "Is Deleted"
    COMMIT_ID_COLUMNS:      str = "Commit ID"
    COMMIT_DATE_COLUMNS:    str = "Commit Date"
    COMMIT_DATA_KEY:        str = "timestamp"
    COMMIT_MESSAGE_COLUMNS: str = "Commit Message"
    CENTRALITY_COLUMNS:     str = "centrality_score"
    FULL_PACKAGE_COLUMNS:   str = "FQN"
    


path_config = PathConfig()
