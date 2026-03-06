"""JSONL ログファイルパーサー"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from session_analyzer.models import (
    AssistantEntry,
    ContentBlock,
    LogEntry,
    ParsedSession,
    SessionFiles,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UsageData,
    UserEntry,
)


def _parse_content_block(raw: dict) -> ContentBlock | None:
    """コンテンツブロックをデータクラスに変換する。未知の type は None を返す。"""
    block_type = raw.get("type")
    if block_type == "text":
        return TextBlock(type="text", text=raw.get("text", ""))
    if block_type == "tool_use":
        return ToolUseBlock(
            type="tool_use",
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            input=raw.get("input", {}),
        )
    if block_type == "thinking":
        return ThinkingBlock(
            type="thinking",
            thinking=raw.get("thinking", ""),
            signature=raw.get("signature", ""),
        )
    if block_type == "tool_result":
        content = raw.get("content", "")
        # content が list の場合は文字列に結合する
        if isinstance(content, list):
            content = "\n".join(
                b.get("text", "") if isinstance(b, dict) else str(b) for b in content
            )
        return ToolResultBlock(
            type="tool_result",
            tool_use_id=raw.get("tool_use_id", ""),
            content=content,
            is_error=bool(raw.get("is_error", False)),
        )
    return None


def _parse_content(raw_content: str | list) -> str | list[ContentBlock]:
    """content フィールドを解析する。文字列はそのまま、リストはブロック変換する。"""
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        blocks: list[ContentBlock] = []
        for raw_block in raw_content:
            if not isinstance(raw_block, dict):
                continue
            block = _parse_content_block(raw_block)
            if block is not None:
                blocks.append(block)
        return blocks
    return str(raw_content)


def _parse_assistant_entry(
    raw: dict, agent_id: str | None = None
) -> AssistantEntry | None:
    """raw dict を AssistantEntry に変換する。必須フィールドがなければ None を返す。"""
    message = raw.get("message", {})
    if not isinstance(message, dict):
        return None

    raw_content = message.get("content", [])
    content_blocks: list[ContentBlock] = []
    if isinstance(raw_content, list):
        for rc in raw_content:
            if isinstance(rc, dict):
                block = _parse_content_block(rc)
                if block is not None:
                    content_blocks.append(block)

    usage_raw = message.get("usage", {})
    usage = UsageData(
        input_tokens=usage_raw.get("input_tokens", 0),
        output_tokens=usage_raw.get("output_tokens", 0),
        cache_creation_input_tokens=usage_raw.get("cache_creation_input_tokens", 0),
        cache_read_input_tokens=usage_raw.get("cache_read_input_tokens", 0),
    )

    return AssistantEntry(
        uuid=raw.get("uuid", ""),
        parent_uuid=raw.get("parentUuid"),
        timestamp=raw.get("timestamp", ""),
        model=message.get("model", ""),
        content=content_blocks,
        usage=usage,
        agent_id=agent_id,
    )


def _parse_user_entry(raw: dict, agent_id: str | None = None) -> UserEntry | None:
    """raw dict を UserEntry に変換する。"""
    message = raw.get("message", {})
    if not isinstance(message, dict):
        return None

    raw_content = message.get("content", "")
    content = _parse_content(raw_content)

    return UserEntry(
        uuid=raw.get("uuid", ""),
        parent_uuid=raw.get("parentUuid"),
        timestamp=raw.get("timestamp", ""),
        is_meta=bool(raw.get("isMeta", False)),
        content=content,
        agent_id=agent_id,
    )


class LogParser:
    """JSONL ファイルを行単位で読み込み、型付きドメインオブジェクトに変換する"""

    def _parse_file(
        self,
        path: Path,
        agent_id: str | None = None,
    ) -> tuple[list[LogEntry], str | None, str | None]:
        """
        JSONL ファイルを解析してエントリ一覧と (cwd, last_timestamp) を返す。
        不正 JSON は stderr に警告を出力してスキップする。
        """
        entries: list[LogEntry] = []
        cwd: str | None = None
        last_timestamp: str | None = None
        with path.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as e:
                    print(
                        f"[WARNING] {path}:{lineno}: JSON parse error: {e}",
                        file=sys.stderr,
                    )
                    continue

                if cwd is None:
                    raw_cwd = raw.get("cwd")
                    if raw_cwd:
                        cwd = str(raw_cwd)

                raw_ts = raw.get("timestamp")
                if raw_ts:
                    last_timestamp = str(raw_ts)

                entry_type = raw.get("type")
                if entry_type == "assistant":
                    entry = _parse_assistant_entry(raw, agent_id)
                    if entry is not None:
                        entries.append(entry)
                elif entry_type == "user":
                    entry = _parse_user_entry(raw, agent_id)
                    if entry is not None:
                        entries.append(entry)
                # その他の type（progress, file-history-snapshot, system 等）はスキップ

        return entries, cwd, last_timestamp

    def parse(self, files: SessionFiles) -> ParsedSession:
        """SessionFiles を解析して ParsedSession を返す"""
        session_id = files.main.stem
        main_entries, cwd, last_timestamp = self._parse_file(files.main, agent_id=None)

        subagent_entries: dict[str, list[LogEntry]] = {}
        for sub_path in files.subagents:
            # agent-{agentId}.jsonl → agentId
            stem = sub_path.stem  # e.g. "agent-aaa111"
            agent_id = stem[len("agent-") :] if stem.startswith("agent-") else stem
            entries, _, _ = self._parse_file(sub_path, agent_id=agent_id)
            subagent_entries[agent_id] = entries

        return ParsedSession(
            session_id=session_id,
            main_entries=main_entries,
            subagent_entries=subagent_entries,
            cwd=cwd,
            last_timestamp=last_timestamp,
        )
