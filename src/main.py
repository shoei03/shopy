from shopy import path_config
from shopy import ExtractFilesInfo


def main():
    ef = ExtractFilesInfo(path_config.REPO_DIR, path_config.PROJECTS_DATA_DIR)
    ef.main(isDeleted=True)


if __name__ == "__main__":
    main()
