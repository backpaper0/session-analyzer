"""ツール使用サマリーと Bash コマンド集計アナライザー"""
from __future__ import annotations

import shlex
from collections import defaultdict
from dataclasses import dataclass

from session_analyzer.models import (
    AssistantEntry,
    BashInvocation,
    CommandAggregation,
    ParsedSession,
    ToolReport,
    ToolResultBlock,
    ToolUseBlock,
    UserEntry,
)

# サブコマンド展開対象コマンド
SUBCOMMAND_TARGETS: frozenset[str] = frozenset({"git", "docker", "mvn", "npm", "uv"})


def _parse_base_command(cmd: str) -> tuple[str, str | None]:
    """
    コマンド文字列からベースコマンドとサブコマンドを抽出する。
    shlex.split に失敗した場合は先頭スペース区切りトークンを使用。
    """
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = cmd.split()

    if not tokens:
        return (cmd, None)

    base = tokens[0]
    sub = tokens[1] if len(tokens) > 1 and base in SUBCOMMAND_TARGETS else None
    return (base, sub)


@dataclass
class _BashContext:
    """Bash ツール実行の中間データ"""
    tool_use_id: str
    command: str
    timestamp: str
    source: str


class ToolAnalyzer:
    """tool_use ブロックを集計し、Bash コマンドの詳細一覧と集計サマリーを提供する"""

    def analyze(self, session: ParsedSession) -> ToolReport:
        # すべてのエントリを (entries, source) ペアで収集
        sources: list[tuple[list, str]] = [
            (session.main_entries, "main"),
        ]
        for agent_id, sub_entries in session.subagent_entries.items():
            sources.append((sub_entries, agent_id))

        tool_counts: dict[str, int] = defaultdict(int)
        bash_contexts: dict[str, _BashContext] = {}  # tool_use_id -> context
        tool_results: dict[str, ToolResultBlock] = {}  # tool_use_id -> result block

        for entries, source in sources:
            for entry in entries:
                if isinstance(entry, AssistantEntry):
                    for block in entry.content:
                        if not isinstance(block, ToolUseBlock):
                            continue
                        tool_counts[block.name] += 1
                        if block.name == "Bash":
                            cmd = block.input.get("command", "") if block.input else ""
                            bash_contexts[block.id] = _BashContext(
                                tool_use_id=block.id,
                                command=str(cmd),
                                timestamp=entry.timestamp,
                                source=source,
                            )
                elif isinstance(entry, UserEntry):
                    if not isinstance(entry.content, list):
                        continue
                    for block in entry.content:
                        if isinstance(block, ToolResultBlock):
                            tool_results[block.tool_use_id] = block

        # Bash 実行一覧を構築
        bash_invocations: list[BashInvocation] = []
        for tool_id, ctx in bash_contexts.items():
            result = tool_results.get(tool_id)
            is_error = result.is_error if result else False
            error_msg = result.content if (result and result.is_error) else None
            bash_invocations.append(BashInvocation(
                command=ctx.command,
                is_error=is_error,
                error_message=error_msg,
                timestamp=ctx.timestamp,
                source=ctx.source,
            ))

        # bash_aggregation を構築
        base_counts: dict[str, int] = defaultdict(int)
        sub_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for inv in bash_invocations:
            base, sub = _parse_base_command(inv.command)
            base_counts[base] += 1
            if sub is not None:
                sub_counts[base][sub] += 1

        bash_aggregation = sorted(
            [
                CommandAggregation(
                    base_command=base,
                    count=count,
                    sub_commands=dict(sub_counts[base]),
                )
                for base, count in base_counts.items()
            ],
            key=lambda a: a.count,
            reverse=True,
        )

        return ToolReport(
            tool_counts=dict(tool_counts),
            bash_invocations=bash_invocations,
            bash_aggregation=bash_aggregation,
        )
