from shopy import CalcMetrics, ExtractFilesInfo, StoreFiles, path_config


def main():
    ef = ExtractFilesInfo(path_config.REPO_DIR, path_config.PROJECTS_DATA_DIR)
    ef.main(isDeleted=True)

    sf = StoreFiles()
    sf.save_deleted_file()
    sf.save_existing_file()
    
    cm = CalcMetrics()
    cm.main()


if __name__ == "__main__":
    main()
