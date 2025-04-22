from pathlib import Path
from typing import Optional

import javalang
from javalang.parser import JavaSyntaxError
from javalang.tokenizer import LexerError

# 試すエンコーディング一覧
_COMMON_ENCODINGS = ["utf-8", "shift_jis", "euc_jp", "iso2022_jp"]


class GetName:
    def __init__(self):
        pass

    def _safe_read_java(self, cwd: Path, java_file: Path) -> str:
        """
        主要な日本語エンコーディングを順に試し、
        どれも UnicodeDecodeError なら最終的に errors='replace' で読み込む。
        """
        for enc in _COMMON_ENCODINGS:
            try:
                return Path(cwd / java_file).read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        # すべてダメならデフォルト UTF-8 で置換モード
        return Path(cwd / java_file).read_bytes().decode("utf-8", errors="replace")

    def find_fqn(
        self, cwd: Path, java_file: Path, base_package_prefix: str
    ) -> Optional[str]:
        """Javaファイルから完全修飾クラス名を取得する

        Args:
            cwd (Path): プロジェクトのパス
            java_file (Path): Javaファイルのパス
            base_package_prefix (str): パッケージ名の先頭

        Returns:
            Optional[str]: 完全修飾クラス名。見つからない／パース失敗時は None
        """
        try:
            # エンコーディング自動判別付きでファイル読み込み
            content = self._safe_read_java(cwd, java_file)
            tree = javalang.parse.parse(content)

            # package 名を取得（なければ空文字列）
            pkg = tree.package.name if tree.package else ""
            if not pkg.startswith(base_package_prefix):
                return None

            # 最初に見つかった型宣言から FQN を生成
            return next(
                (
                    f"{pkg}.{decl.name}" if pkg else decl.name
                    for decl in tree.types
                    if getattr(decl, "name", None)
                ),
                None,
            )
        except (
            JavaSyntaxError,
            LexerError,
            OSError,
            AttributeError,
            StopIteration,
            ValueError,
        ):
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error in find_fqn() for {java_file}: {e}")
            return None

    def extract_imports(self, cwd: Path, java_file: Path) -> list[str]:
        """ファイル内のimport文を抽出する

        Args:
            cwd (Path): プロジェクトのパス
            java_file (Path): Javaファイルのパス

        Returns:
            list[str]: import文のリスト
        """
        try:
            # エンコーディング自動判別付きでファイル読み込み
            content = self._safe_read_java(cwd, java_file)
            tree = javalang.parse.parse(content)
            return [imp.path for imp in tree.imports]
        except (JavaSyntaxError, LexerError, OSError, AttributeError, ValueError):
            return []
        except Exception as e:
            print(f"[ERROR] Unexpected error in extract_imports() for {java_file}: {e}")
            return []
