"""タスク3.2: メインセッションとサブエージェントの統合テスト"""
import json
import pytest
from pathlib import Path

from session_analyzer.parser import LogParser
from session_analyzer.models import (
    AssistantEntry, UserEntry, ParsedSession, SessionFiles,
)


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries))


def _make_assistant(uuid: str = "uuid-a1", agent_id: str | None = None) -> dict:
    base = {
        "type": "assistant",
        "uuid": uuid,
        "parentUuid": None,
        "timestamp": "2024-01-01T00:00:00Z",
        "message": {
            "model": "claude-sonnet-4-6",
            "content": [{"type": "text", "text": "OK"}],
            "usage": {"input_tokens": 10, "output_tokens": 5,
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
        },
    }
    if agent_id:
        base["agentId"] = agent_id
    return base


def _make_user(uuid: str = "uuid-u1", is_meta: bool = False) -> dict:
    return {
        "type": "user",
        "uuid": uuid,
        "parentUuid": None,
        "timestamp": "2024-01-01T00:01:00Z",
        "isMeta": is_meta,
        "message": {"role": "user", "content": "hello"},
    }


# --- parse() の基本動作 ---

def test_parse_returns_parsed_session(tmp_path):
    """parse()がParsedSessionを返すこと"""
    main = tmp_path / "abc123.jsonl"
    _write_jsonl(main, [_make_user()])
    files = SessionFiles(main=main, subagents=[])

    result = LogParser().parse(files)

    assert isinstance(result, ParsedSession)


def test_parse_sets_session_id_from_filename(tmp_path):
    """ParsedSessionのsession_idがメインファイルのステム（ファイル名）になること"""
    main = tmp_path / "abc123def456.jsonl"
    _write_jsonl(main, [_make_user()])
    files = SessionFiles(main=main, subagents=[])

    result = LogParser().parse(files)

    assert result.session_id == "abc123def456"


def test_parse_main_entries(tmp_path):
    """メインJSONLのエントリがmain_entriesに格納されること"""
    main = tmp_path / "sess1.jsonl"
    _write_jsonl(main, [_make_user("u1"), _make_assistant("a1")])
    files = SessionFiles(main=main, subagents=[])

    result = LogParser().parse(files)

    assert len(result.main_entries) == 2


def test_parse_no_subagents(tmp_path):
    """サブエージェントなしの場合、subagent_entriesが空dictであること"""
    main = tmp_path / "sess1.jsonl"
    _write_jsonl(main, [_make_user()])
    files = SessionFiles(main=main, subagents=[])

    result = LogParser().parse(files)

    assert result.subagent_entries == {}


# --- サブエージェントの統合 ---

def test_parse_subagent_entries_keyed_by_agent_id(tmp_path):
    """サブエージェントのエントリがagentIdをキーとして格納されること"""
    main = tmp_path / "sess1.jsonl"
    _write_jsonl(main, [_make_user()])

    sub_dir = tmp_path / "sess1" / "subagents"
    sub_dir.mkdir(parents=True)
    sub_file = sub_dir / "agent-aaa111.jsonl"
    _write_jsonl(sub_file, [_make_assistant("a1", agent_id="aaa111")])

    files = SessionFiles(main=main, subagents=[sub_file])

    result = LogParser().parse(files)

    assert "aaa111" in result.subagent_entries
    assert len(result.subagent_entries["aaa111"]) == 1


def test_parse_subagent_agent_id_extracted_from_filename(tmp_path):
    """agent-{id}.jsonlファイル名からagentIdが正しく抽出されること"""
    main = tmp_path / "sess1.jsonl"
    _write_jsonl(main, [_make_user()])

    sub_dir = tmp_path / "sess1" / "subagents"
    sub_dir.mkdir(parents=True)
    sub_file = sub_dir / "agent-xyz789.jsonl"
    _write_jsonl(sub_file, [_make_assistant("a1")])

    files = SessionFiles(main=main, subagents=[sub_file])
    result = LogParser().parse(files)

    assert "xyz789" in result.subagent_entries


def test_parse_multiple_subagents(tmp_path):
    """複数のサブエージェントがそれぞれ別キーで格納されること"""
    main = tmp_path / "sess1.jsonl"
    _write_jsonl(main, [_make_user()])

    sub_dir = tmp_path / "sess1" / "subagents"
    sub_dir.mkdir(parents=True)

    sub1 = sub_dir / "agent-aaa111.jsonl"
    _write_jsonl(sub1, [_make_assistant("a1")])
    sub2 = sub_dir / "agent-bbb222.jsonl"
    _write_jsonl(sub2, [_make_assistant("a2"), _make_user("u2")])

    files = SessionFiles(main=main, subagents=[sub1, sub2])
    result = LogParser().parse(files)

    assert "aaa111" in result.subagent_entries
    assert "bbb222" in result.subagent_entries
    assert len(result.subagent_entries["bbb222"]) == 2


def test_parse_subagent_entries_have_agent_id_set(tmp_path):
    """サブエージェントのエントリにagent_idが設定されていること"""
    main = tmp_path / "sess1.jsonl"
    _write_jsonl(main, [_make_user()])

    sub_dir = tmp_path / "sess1" / "subagents"
    sub_dir.mkdir(parents=True)
    sub_file = sub_dir / "agent-aaa111.jsonl"
    _write_jsonl(sub_file, [_make_assistant("a1")])

    files = SessionFiles(main=main, subagents=[sub_file])
    result = LogParser().parse(files)

    entry = result.subagent_entries["aaa111"][0]
    assert isinstance(entry, AssistantEntry)
    assert entry.agent_id == "aaa111"


def test_parse_main_entries_have_no_agent_id(tmp_path):
    """メインエントリのagent_idはNoneであること"""
    main = tmp_path / "sess1.jsonl"
    _write_jsonl(main, [_make_assistant("a1")])
    files = SessionFiles(main=main, subagents=[])

    result = LogParser().parse(files)

    assert result.main_entries[0].agent_id is None
