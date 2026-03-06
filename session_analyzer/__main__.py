"""python -m session_analyzer のエントリポイント"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from session_analyzer.exceptions import (
    AmbiguousSessionError,
    ReportGenerationError,
    SessionNotFoundError,
)
from session_analyzer.session_analyzer import SessionAnalyzer


def _run_pipeline(session_id: str, claude_dir: Path, output_path: Path) -> Path:
    """パイプライン実行: SessionAnalyzer に委譲する"""
    return SessionAnalyzer().run(session_id, claude_dir, output_path)


def main(argv: list[str] | None = None) -> int:
    """エントリポイント。argv=None のとき sys.argv を使用。終了コードを返す。"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="session_analyzer",
        description="Claude Code セッションログを解析し HTML レポートを生成する",
    )
    parser.add_argument("session_id", help="解析対象のセッション ID")
    parser.add_argument(
        "--output",
        "-o",
        help="出力 HTML ファイルパス（省略時: session-{session_id}.html）",
    )
    parser.add_argument(
        "--claude-dir",
        help="Claude 設定ディレクトリ（省略時: $CLAUDE_CONFIG_DIR または $HOME/.claude）",
    )

    args = parser.parse_args(argv)

    # 出力パスの解決
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"session-{args.session_id}.html")

    # claude ルートディレクトリの解決
    if args.claude_dir:
        claude_dir = Path(args.claude_dir)
    elif env_dir := os.environ.get("CLAUDE_CONFIG_DIR"):
        claude_dir = Path(env_dir)
    else:
        claude_dir = Path.home() / ".claude"

    try:
        html_path = _run_pipeline(args.session_id, claude_dir, output_path)
        print(html_path)
        return 0
    except SessionNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except AmbiguousSessionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ReportGenerationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
