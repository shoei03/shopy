import re
from pathlib import Path


def get_child_dir(path: Path) -> list[Path]:
    """指定したパスの子ディレクトリを取得する

    Args:
        path (Path): 対象のパス

    Returns:
        list[Path]: 子ディレクトリのリスト
    """
    return [p.name for p in path.iterdir() if p.is_dir()]


def sanitize_filename(self, name: str) -> str:
    """ファイル名に使えない文字を安全な形式に変換"""
    return re.sub(r'[\\/*?:"<>|]', "_", name)
