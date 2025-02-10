from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathConfig:
    ORGANIZATION: str = "iluwatar"
    REPO_NAME: str = "java-design-patterns"
    ROOT_DIR: Path = Path(__file__).parents[3]
    DATA_DIR: Path = ROOT_DIR / "data"
    PROJECTS_DATA_DIR: Path = DATA_DIR / REPO_NAME
    PROJECTS_DIR: Path = ROOT_DIR.parent / "projects"
    REPO_DIR: Path = PROJECTS_DIR / REPO_NAME


path_config = PathConfig()
