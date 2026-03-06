"""タスク3.1: JSONL 行単位ストリーミング解析のテスト"""

import json
from pathlib import Path

from session_analyzer.models import (
    AssistantEntry,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UsageData,
    UserEntry,
)
from session_analyzer.parser import LogParser


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    """テスト用JSOLファイルを書き込むヘルパー"""
    path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries))


# --- assistant エントリのパース ---

ASSISTANT_ENTRY = {
    "type": "assistant",
    "uuid": "uuid-a1",
    "parentUuid": "uuid-p1",
    "timestamp": "2024-01-01T00:00:00Z",
    "message": {
        "model": "claude-sonnet-4-6",
        "content": [{"type": "text", "text": "Hello!"}],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_input_tokens": 10,
            "cache_read_input_tokens": 5,
        },
    },
}


def test_parse_assistant_entry(tmp_path):
    """assistantエントリがAssistantEntryに変換されること"""
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [ASSISTANT_ENTRY])

    parser = LogParser()
    entries = parser._parse_file(f)[0]

    assert len(entries) == 1
    entry = entries[0]
    assert isinstance(entry, AssistantEntry)
    assert entry.uuid == "uuid-a1"
    assert entry.parent_uuid == "uuid-p1"
    assert entry.timestamp == "2024-01-01T00:00:00Z"
    assert entry.model == "claude-sonnet-4-6"


def test_parse_assistant_usage(tmp_path):
    """assistantエントリのusageが正しくパースされること"""
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [ASSISTANT_ENTRY])

    entries = LogParser()._parse_file(f)[0]
    assert isinstance(entries[0], AssistantEntry)
    usage = entries[0].usage

    assert isinstance(usage, UsageData)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cache_creation_input_tokens == 10
    assert usage.cache_read_input_tokens == 5


def test_parse_assistant_text_block(tmp_path):
    """assistantのtextブロックがTextBlockに変換されること"""
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [ASSISTANT_ENTRY])

    entries = LogParser()._parse_file(f)[0]
    content = entries[0].content

    assert len(content) == 1
    assert isinstance(content[0], TextBlock)
    assert content[0].text == "Hello!"


def test_parse_assistant_tool_use_block(tmp_path):
    """assistantのtool_useブロックがToolUseBlockに変換されること"""
    _msg = ASSISTANT_ENTRY["message"]
    assert isinstance(_msg, dict)
    entry = {
        **ASSISTANT_ENTRY,
        "message": {
            **_msg,
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool-id-1",
                    "name": "Bash",
                    "input": {"command": "ls -la"},
                }
            ],
        },
    }
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [entry])

    entries = LogParser()._parse_file(f)[0]
    block = entries[0].content[0]

    assert isinstance(block, ToolUseBlock)
    assert block.id == "tool-id-1"
    assert block.name == "Bash"
    assert block.input == {"command": "ls -la"}


def test_parse_assistant_thinking_block(tmp_path):
    """assistantのthinkingブロックがThinkingBlockに変換されること"""
    _msg2 = ASSISTANT_ENTRY["message"]
    assert isinstance(_msg2, dict)
    entry = {
        **ASSISTANT_ENTRY,
        "message": {
            **_msg2,
            "content": [
                {
                    "type": "thinking",
                    "thinking": "Let me think...",
                    "signature": "sig-abc",
                }
            ],
        },
    }
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [entry])

    entries = LogParser()._parse_file(f)[0]
    block = entries[0].content[0]

    assert isinstance(block, ThinkingBlock)
    assert block.thinking == "Let me think..."
    assert block.signature == "sig-abc"


def test_parse_assistant_no_parent_uuid(tmp_path):
    """parentUuidがnullのassistantエントリも正しく処理されること"""
    entry = {**ASSISTANT_ENTRY, "parentUuid": None}
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [entry])

    entries = LogParser()._parse_file(f)[0]
    assert entries[0].parent_uuid is None


# --- user エントリのパース ---

USER_ENTRY_STRING = {
    "type": "user",
    "uuid": "uuid-u1",
    "parentUuid": None,
    "timestamp": "2024-01-01T00:01:00Z",
    "isMeta": True,
    "message": {
        "role": "user",
        "content": "Hello from user",
    },
}


def test_parse_user_entry_string_content(tmp_path):
    """userエントリの文字列contentが正しくパースされること"""
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [USER_ENTRY_STRING])

    entries = LogParser()._parse_file(f)[0]

    assert len(entries) == 1
    entry = entries[0]
    assert isinstance(entry, UserEntry)
    assert entry.uuid == "uuid-u1"
    assert entry.is_meta is True
    assert entry.content == "Hello from user"


def test_parse_user_entry_tool_result_content(tmp_path):
    """userエントリのtool_resultリストcontentが正しくパースされること"""
    entry = {
        "type": "user",
        "uuid": "uuid-u2",
        "parentUuid": "uuid-a1",
        "timestamp": "2024-01-01T00:02:00Z",
        "isMeta": False,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tool-id-1",
                    "content": "command output here",
                }
            ],
        },
    }
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [entry])

    entries = LogParser()._parse_file(f)[0]
    block = entries[0].content[0]

    assert isinstance(block, ToolResultBlock)
    assert block.tool_use_id == "tool-id-1"
    assert block.content == "command output here"
    assert block.is_error is False


def test_parse_user_entry_tool_result_error(tmp_path):
    """tool_resultのis_errorフラグが正しく設定されること"""
    entry = {
        "type": "user",
        "uuid": "uuid-u3",
        "parentUuid": "uuid-a1",
        "timestamp": "2024-01-01T00:03:00Z",
        "isMeta": False,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tool-id-2",
                    "content": "Error: command not found",
                    "is_error": True,
                }
            ],
        },
    }
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [entry])

    entries = LogParser()._parse_file(f)[0]
    block = entries[0].content[0]

    assert isinstance(block, ToolResultBlock)
    assert block.is_error is True


def test_parse_user_is_meta_false(tmp_path):
    """isMeta=falseのuserエントリが正しくパースされること"""
    entry = {**USER_ENTRY_STRING, "isMeta": False}
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [entry])

    entries = LogParser()._parse_file(f)[0]
    assert isinstance(entries[0], UserEntry)
    assert entries[0].is_meta is False


# --- 未知型のスキップ ---


def test_parse_skips_unknown_types(tmp_path):
    """未知のtypeエントリがスキップされること"""
    entries_data = [
        {"type": "progress", "data": "..."},
        {"type": "file-history-snapshot", "data": "..."},
        {"type": "system", "data": "..."},
        ASSISTANT_ENTRY,
    ]
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, entries_data)

    entries = LogParser()._parse_file(f)[0]
    assert len(entries) == 1
    assert isinstance(entries[0], AssistantEntry)


# --- 不正JSON のスキップ ---


def test_parse_skips_invalid_json_lines(tmp_path, capsys):
    """不正なJSON行をスキップして処理を継続すること"""
    f = tmp_path / "session.jsonl"
    f.write_text(
        '{"invalid json\n' + json.dumps(ASSISTANT_ENTRY) + "\n" + "not json at all\n"
    )

    entries = LogParser()._parse_file(f)[0]
    assert len(entries) == 1
    assert isinstance(entries[0], AssistantEntry)


def test_parse_invalid_json_warns_to_stderr(tmp_path, capsys):
    """不正なJSON行の警告がstderrに出力されること"""
    f = tmp_path / "session.jsonl"
    f.write_text('{"invalid json\n')

    LogParser()._parse_file(f)
    captured = capsys.readouterr()
    assert captured.err != ""


# --- 空ファイル ---


def test_parse_empty_file(tmp_path):
    """空のJSONLファイルは空リストを返すこと"""
    f = tmp_path / "session.jsonl"
    f.write_text("")

    entries = LogParser()._parse_file(f)[0]
    assert entries == []


# --- 複数エントリの順序 ---


def test_parse_multiple_entries_in_order(tmp_path):
    """複数エントリが順序通りに返されること"""
    user_entry = {
        "type": "user",
        "uuid": "uuid-u1",
        "parentUuid": None,
        "timestamp": "2024-01-01T00:00:00Z",
        "isMeta": False,
        "message": {"role": "user", "content": "hi"},
    }
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [user_entry, ASSISTANT_ENTRY])

    entries = LogParser()._parse_file(f)[0]
    assert len(entries) == 2
    assert isinstance(entries[0], UserEntry)
    assert isinstance(entries[1], AssistantEntry)
