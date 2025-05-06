import json
from pathlib import Path


def write_json(dict: dict, output_dir: Path) -> None:
    """
    JSONファイルを書き込む
    Args:
        dict (dict): 書き込むJSONファイルのパス
        output_dir (Path): 出力先ディレクトリ
    """
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with open(output_dir, "w", encoding="utf-8") as f:
        json.dump(dict, f, ensure_ascii=False, indent=4)


def read_json(input_dir: Path) -> dict:
    """
    JSONファイルを読み込む
    Args:
        input_dir (Path): 読み込むJSONファイルのパス
    Returns:
        dict: 読み込んだJSONデータ
    """
    with open(input_dir, "r", encoding="utf-8") as f:
        dict = json.load(f)
    return dict
