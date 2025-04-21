from pathlib import Path

from shopy import path_config


class CalcMetrics:

    def calc_metrics(self, file_path: Path):
        with open(file_path, 'r') as file:
            lines: list = file.readlines()
            lines_len: list = len(lines)

        return lines_len
    
    def main(self):
        deleted_file_path: Path = Path(path_config.DELETED_FILES).glob('*')
        existing_file_path: Path = Path(path_config.EXISTING_FILES).glob('*')
        
        deleted_metrics: list = [self.calc_metrics(file_path) for file_path in deleted_file_path]
        existing_metrics: list = [self.calc_metrics(file_path) for file_path in existing_file_path]
