"""スキル使用サマリーアナライザー"""
from __future__ import annotations

import re

from session_analyzer.models import (
    InvocationMethod,
    ParsedSession,
    SkillInvocation,
    SkillReport,
    UserEntry,
)

_COMMAND_NAME_RE = re.compile(r"<command-name>(/?)([^<]+)</command-name>")


def _extract_skill_name(content: str) -> str | None:
    """文字列から <command-name> タグのスキル名を抽出する。見つからなければ None。"""
    m = _COMMAND_NAME_RE.search(content)
    if m is None:
        return None
    # 先頭の / は除去、残りがスキル名
    return m.group(2).strip()


class SkillAnalyzer:
    """`<command-name>` タグを持つ user メッセージを検出し、起動方法別に分類・集計する"""

    def analyze(self, session: ParsedSession) -> SkillReport:
        invocations: list[SkillInvocation] = []

        all_entries = list(session.main_entries)
        for sub_entries in session.subagent_entries.values():
            all_entries.extend(sub_entries)

        for entry in all_entries:
            if not isinstance(entry, UserEntry):
                continue
            if not isinstance(entry.content, str):
                continue

            skill_name = _extract_skill_name(entry.content)
            if skill_name is None:
                continue

            method = (
                InvocationMethod.LLM_AUTO
                if entry.is_meta
                else InvocationMethod.USER_SLASH_COMMAND
            )
            invocations.append(SkillInvocation(
                skill_name=skill_name,
                method=method,
                timestamp=entry.timestamp,
                uuid=entry.uuid,
            ))

        # タイムスタンプ順（エントリ順）に並べる
        summary: dict[str, int] = {}
        for inv in invocations:
            summary[inv.skill_name] = summary.get(inv.skill_name, 0) + 1

        return SkillReport(invocations=invocations, summary=summary)
