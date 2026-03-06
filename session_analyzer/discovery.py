"""ログファイル探索モジュール"""

from __future__ import annotations

import os
from pathlib import Path

from session_analyzer.exceptions import AmbiguousSessionError, SessionNotFoundError
from session_analyzer.models import SessionFiles


class LogDiscovery:
    """セッション ID に対応する JSONL ファイルパスを探索する"""

    def _get_root_dir(self, claude_dir: Path | None = None) -> Path:
        """
        Claude 設定ルートディレクトリを解決する。

        優先順位:
        1. 引数 claude_dir（明示指定）
        2. 環境変数 CLAUDE_CONFIG_DIR
        3. $HOME/.claude
        """
        if claude_dir is not None:
            return claude_dir
        env_dir = os.environ.get("CLAUDE_CONFIG_DIR")
        if env_dir:
            return Path(env_dir)
        return Path.home() / ".claude"

    def _scan_jsonl_files(self, root_dir: Path) -> list[Path]:
        """
        root_dir/projects/ 配下を再帰的にスキャンして *.jsonl ファイルを返す。
        projects/ ディレクトリが存在しない場合は空リストを返す。
        """
        projects_dir = root_dir / "projects"
        if not projects_dir.exists():
            return []
        return list(projects_dir.rglob("*.jsonl"))

    def discover(
        self,
        session_id: str,
        root_dir: Path,
    ) -> SessionFiles:
        """
        セッション ID に対応する JSONL ファイルを探索する。

        Raises:
            SessionNotFoundError: マッチするファイルが存在しない
            AmbiguousSessionError: 複数のファイルがマッチした
        """
        all_files = self._scan_jsonl_files(root_dir)

        if not all_files:
            raise SessionNotFoundError(session_id)

        # 完全一致を優先
        exact = [f for f in all_files if f.stem == session_id]
        if len(exact) == 1:
            main_file = exact[0]
        elif len(exact) > 1:
            raise AmbiguousSessionError(session_id, [str(f) for f in exact])
        else:
            # prefix 一致
            prefix = [f for f in all_files if f.stem.startswith(session_id)]
            if len(prefix) == 0:
                raise SessionNotFoundError(session_id)
            if len(prefix) > 1:
                raise AmbiguousSessionError(session_id, [str(f) for f in prefix])
            main_file = prefix[0]

        # サブエージェントファイル探索: {session_dir}/{session_id}/subagents/agent-*.jsonl
        session_dir = main_file.parent
        subagents_dir = session_dir / main_file.stem / "subagents"
        subagents: list[Path] = []
        if subagents_dir.exists():
            subagents = sorted(subagents_dir.glob("agent-*.jsonl"))

        return SessionFiles(main=main_file, subagents=subagents)
