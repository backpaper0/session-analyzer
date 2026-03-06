"""サブエージェント情報集計アナライザー"""

from __future__ import annotations

from session_analyzer.analyzers.token import TokenAnalyzer
from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    SubAgentInfo,
    SubAgentReport,
    TokenUsageStats,
    ToolUseBlock,
)

_SUBAGENT_TOOL_NAMES = frozenset({"Task", "Agent"})


def _compute_subagent_token_usage(
    entries: list,
    model_hint: str = "total",
) -> TokenUsageStats | None:
    """サブエージェントエントリからトークン使用量を集計する。エントリがなければ None。"""
    if not entries:
        return None

    from session_analyzer.models import ParsedSession

    pseudo_session = ParsedSession(
        session_id="_sub",
        main_entries=entries,
        subagent_entries={},
    )
    report = TokenAnalyzer().analyze(pseudo_session)
    return report.total


class SubAgentAnalyzer:
    """Task/Agent ツール呼び出しを検出し、サブエージェントの概要と使用トークンを集計する"""

    def analyze(self, session: ParsedSession) -> SubAgentReport:
        # Task/Agent tool_use ブロックを時系列順に収集
        task_calls: list[SubAgentInfo] = []

        for entry in session.main_entries:
            if not isinstance(entry, AssistantEntry):
                continue
            for block in entry.content:
                if not isinstance(block, ToolUseBlock):
                    continue
                if block.name not in _SUBAGENT_TOOL_NAMES:
                    continue

                inp = block.input or {}
                # prompt は "prompt" フィールド優先、なければ "description"
                prompt = inp.get("prompt") or inp.get("description") or ""
                subagent_type = inp.get("subagent_type")
                subagent_type = (
                    str(subagent_type) if subagent_type is not None else None
                )

                task_calls.append(
                    SubAgentInfo(
                        agent_id=block.id,
                        tool_name=block.name,
                        subagent_type=subagent_type,
                        prompt=str(prompt),
                        launched_at=entry.timestamp,
                        token_usage=None,  # 後で紐づけ
                    )
                )

        # サブエージェントエントリのトークン使用量を計算
        sub_token_usages: list[TokenUsageStats] = []
        for agent_id, sub_entries in session.subagent_entries.items():
            usage = _compute_subagent_token_usage(sub_entries)
            if usage is not None:
                sub_token_usages.append(usage)

        # Task 呼び出しとサブエージェントファイルを順序でマッチング
        for i, info in enumerate(task_calls):
            if i < len(sub_token_usages):
                # dataclass は frozen でないため直接代入
                task_calls[i] = SubAgentInfo(
                    agent_id=info.agent_id,
                    tool_name=info.tool_name,
                    subagent_type=info.subagent_type,
                    prompt=info.prompt,
                    launched_at=info.launched_at,
                    token_usage=sub_token_usages[i],
                )

        return SubAgentReport(agents=task_calls)
