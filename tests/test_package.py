"""タスク1.1: パッケージ構造とエントリポイントのテスト"""

import subprocess
import sys
from pathlib import Path


def test_package_importable():
    """session_analyzerパッケージがインポート可能であること"""
    import session_analyzer

    assert session_analyzer is not None


def test_package_has_version():
    """パッケージにバージョン情報が存在すること"""
    import session_analyzer

    assert hasattr(session_analyzer, "__version__")


def test_main_module_runnable():
    """python -m session_analyzer が実行可能であること（ModuleNotFoundError にならないこと）"""
    result = subprocess.run(
        [sys.executable, "-m", "session_analyzer"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert "No module named" not in result.stderr
    assert "ModuleNotFoundError" not in result.stderr
    # session_id 未指定なので正常終了しないが、argparse エラー (2) または独自エラー (1) のどちらか
    assert result.returncode in (1, 2)


def test_main_entry_point_signature():
    """main() 関数が定義されていて呼び出し可能であること"""
    from session_analyzer.__main__ import main

    assert callable(main)
