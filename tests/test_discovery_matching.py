"""タスク2.2: セッションIDマッチングとサブエージェント探索のテスト"""

from pathlib import Path

import pytest

from session_analyzer.discovery import LogDiscovery
from session_analyzer.exceptions import AmbiguousSessionError, SessionNotFoundError
from session_analyzer.models import SessionFiles


def _make_session(root: Path, project: str, session_id: str) -> Path:
    """テスト用セッションJSONLファイルを作成するヘルパー"""
    p = root / "projects" / project
    p.mkdir(parents=True, exist_ok=True)
    f = p / f"{session_id}.jsonl"
    f.write_text("{}")
    return f


def _make_subagent(root: Path, project: str, session_id: str, agent_id: str) -> Path:
    """テスト用サブエージェントJSONLファイルを作成するヘルパー"""
    subdir = root / "projects" / project / session_id / "subagents"
    subdir.mkdir(parents=True, exist_ok=True)
    f = subdir / f"{agent_id}.jsonl"
    f.write_text("{}")
    return f


# --- 完全一致マッチング ---


def test_discover_exact_match(tmp_path):
    """完全一致でセッションJSONLを特定できること"""
    session_id = "abc123"
    expected = _make_session(tmp_path, "proj1", session_id)

    discovery = LogDiscovery()
    result = discovery.discover(session_id, tmp_path)

    assert result.main == expected


def test_discover_exact_match_returns_session_files(tmp_path):
    """discover()がSessionFilesを返すこと"""
    _make_session(tmp_path, "proj1", "abc123")

    discovery = LogDiscovery()
    result = discovery.discover("abc123", tmp_path)

    assert isinstance(result, SessionFiles)


def test_discover_exact_match_preferred_over_prefix(tmp_path):
    """完全一致がprefix一致より優先されること"""
    exact = _make_session(tmp_path, "proj1", "abc123")
    _make_session(tmp_path, "proj2", "abc123456")

    discovery = LogDiscovery()
    result = discovery.discover("abc123", tmp_path)

    assert result.main == exact


# --- prefix マッチング ---


def test_discover_prefix_match(tmp_path):
    """セッションIDのprefixでマッチできること"""
    full_id = "abc123def456"
    expected = _make_session(tmp_path, "proj1", full_id)

    discovery = LogDiscovery()
    result = discovery.discover("abc123", tmp_path)

    assert result.main == expected


def test_discover_prefix_match_multiple_raises(tmp_path):
    """prefixが複数ファイルにマッチした場合はAmbiguousSessionErrorを送出すること"""
    _make_session(tmp_path, "proj1", "abc123xxx")
    _make_session(tmp_path, "proj2", "abc123yyy")

    discovery = LogDiscovery()
    with pytest.raises(AmbiguousSessionError):
        discovery.discover("abc123", tmp_path)


def test_discover_ambiguous_error_message(tmp_path):
    """AmbiguousSessionErrorにセッションIDと候補ファイルが含まれること"""
    _make_session(tmp_path, "proj1", "abc123xxx")
    _make_session(tmp_path, "proj2", "abc123yyy")

    discovery = LogDiscovery()
    with pytest.raises(AmbiguousSessionError) as exc_info:
        discovery.discover("abc123", tmp_path)

    msg = str(exc_info.value)
    assert "abc123" in msg


def test_discover_no_match_raises(tmp_path):
    """マッチするファイルがない場合はSessionNotFoundErrorを送出すること"""
    _make_session(tmp_path, "proj1", "xyz999")

    discovery = LogDiscovery()
    with pytest.raises(SessionNotFoundError):
        discovery.discover("abc123", tmp_path)


# --- サブエージェントファイル探索 ---


def test_discover_no_subagents(tmp_path):
    """サブエージェントがない場合はsubagentsが空リストであること"""
    _make_session(tmp_path, "proj1", "abc123")

    discovery = LogDiscovery()
    result = discovery.discover("abc123", tmp_path)

    assert result.subagents == []


def test_discover_finds_subagents(tmp_path):
    """サブエージェントJSONLファイルを発見できること"""
    _make_session(tmp_path, "proj1", "abc123")
    sub1 = _make_subagent(tmp_path, "proj1", "abc123", "agent-aaa111")
    sub2 = _make_subagent(tmp_path, "proj1", "abc123", "agent-bbb222")

    discovery = LogDiscovery()
    result = discovery.discover("abc123", tmp_path)

    assert set(result.subagents) == {sub1, sub2}


def test_discover_subagents_only_agent_prefix(tmp_path):
    """agent-*.jsonlのパターンにマッチするファイルのみ返すこと"""
    _make_session(tmp_path, "proj1", "abc123")
    valid = _make_subagent(tmp_path, "proj1", "abc123", "agent-aaa111")
    # agent- プレフィックスなしのファイルは含まれない
    other_dir = tmp_path / "projects" / "proj1" / "abc123" / "subagents"
    other_dir.mkdir(parents=True, exist_ok=True)
    (other_dir / "other-file.jsonl").write_text("{}")

    discovery = LogDiscovery()
    result = discovery.discover("abc123", tmp_path)

    assert result.subagents == [valid]


def test_discover_prefix_match_with_subagents(tmp_path):
    """prefixマッチ時もサブエージェントが正しく探索されること"""
    full_id = "abc123def456"
    _make_session(tmp_path, "proj1", full_id)
    sub = _make_subagent(tmp_path, "proj1", full_id, "agent-sub1")

    discovery = LogDiscovery()
    result = discovery.discover("abc123", tmp_path)

    assert sub in result.subagents
