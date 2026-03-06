"""思考ログの抽出と整理アナライザー"""

from __future__ import annotations

from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    ThinkingBlock,
    ThinkingEntry,
    ThinkingReport,
)


class ThinkingAnalyzer:
    """assistant メッセージの thinking ブロックを全ログから抽出し、時系列で整理する"""

    def analyze(self, session: ParsedSession) -> ThinkingReport:
        entries: list[ThinkingEntry] = []

        # メインエントリから抽出
        for entry in session.main_entries:
            if not isinstance(entry, AssistantEntry):
                continue
            for block in entry.content:
                if isinstance(block, ThinkingBlock):
                    entries.append(
                        ThinkingEntry(
                            content=block.thinking,
                            message_uuid=entry.uuid,
                            timestamp=entry.timestamp,
                            source="main",
                        )
                    )

        # サブエージェントエントリから抽出
        for agent_id, sub_entries in session.subagent_entries.items():
            for entry in sub_entries:
                if not isinstance(entry, AssistantEntry):
                    continue
                for block in entry.content:
                    if isinstance(block, ThinkingBlock):
                        entries.append(
                            ThinkingEntry(
                                content=block.thinking,
                                message_uuid=entry.uuid,
                                timestamp=entry.timestamp,
                                source=agent_id,
                            )
                        )

        # 時系列順にソート
        entries.sort(key=lambda e: e.timestamp)

        return ThinkingReport(
            entries=entries,
            has_thinking=len(entries) > 0,
        )
