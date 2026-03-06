"""タスク2.1: JSONL ファイルの再帰探索と環境変数対応のテスト"""

import pytest

from session_analyzer.discovery import LogDiscovery
from session_analyzer.exceptions import SessionNotFoundError

# --- 再帰スキャン ---


def test_scan_finds_jsonl_files(tmp_path):
    """projects/配下のJSONLファイルを発見できること"""
    projects = tmp_path / "projects" / "proj1"
    projects.mkdir(parents=True)
    (projects / "session1.jsonl").write_text("{}")

    discovery = LogDiscovery()
    files = discovery._scan_jsonl_files(tmp_path)
    assert any(f.name == "session1.jsonl" for f in files)


def test_scan_recursive(tmp_path):
    """ネストされたディレクトリも再帰的にスキャンすること"""
    deep = tmp_path / "projects" / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "nested.jsonl").write_text("{}")

    discovery = LogDiscovery()
    files = discovery._scan_jsonl_files(tmp_path)
    assert any(f.name == "nested.jsonl" for f in files)


def test_scan_ignores_non_jsonl(tmp_path):
    """JSONLでないファイルは無視すること"""
    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "file.json").write_text("{}")
    (projects / "file.txt").write_text("text")
    (projects / "session.jsonl").write_text("{}")

    discovery = LogDiscovery()
    files = discovery._scan_jsonl_files(tmp_path)
    names = [f.name for f in files]
    assert "file.json" not in names
    assert "file.txt" not in names
    assert "session.jsonl" in names


def test_scan_empty_projects_returns_empty(tmp_path):
    """projectsディレクトリが空の場合は空リストを返すこと"""
    (tmp_path / "projects").mkdir()

    discovery = LogDiscovery()
    files = discovery._scan_jsonl_files(tmp_path)
    assert files == []


def test_scan_no_projects_dir_returns_empty(tmp_path):
    """projects/ディレクトリが存在しない場合は空リストを返すこと"""
    discovery = LogDiscovery()
    files = discovery._scan_jsonl_files(tmp_path)
    assert files == []


def test_scan_multiple_files(tmp_path):
    """複数のJSONLファイルをすべて発見すること"""
    p = tmp_path / "projects"
    p.mkdir()
    (p / "sess1.jsonl").write_text("{}")
    (p / "sess2.jsonl").write_text("{}")
    sub = p / "sub"
    sub.mkdir()
    (sub / "sess3.jsonl").write_text("{}")

    discovery = LogDiscovery()
    files = discovery._scan_jsonl_files(tmp_path)
    assert len(files) == 3


# --- ルートディレクトリ解決 ---


def test_get_root_dir_default(monkeypatch, tmp_path):
    """CLAUDE_CONFIG_DIRが未設定の場合は$HOME/.claudeを使用すること"""
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    discovery = LogDiscovery()
    root = discovery._get_root_dir()
    assert root == tmp_path / ".claude"


def test_get_root_dir_env_var(monkeypatch, tmp_path):
    """CLAUDE_CONFIG_DIRが設定されている場合はその値を使用すること"""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))

    discovery = LogDiscovery()
    root = discovery._get_root_dir()
    assert root == tmp_path


def test_get_root_dir_explicit_override(monkeypatch, tmp_path):
    """明示的に指定したディレクトリが環境変数より優先されること"""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/should/be/ignored")
    custom = tmp_path / "custom"

    discovery = LogDiscovery()
    root = discovery._get_root_dir(claude_dir=custom)
    assert root == custom


# --- SessionNotFoundError ---


def test_discover_raises_when_no_jsonl_files(tmp_path):
    """JONLファイルが一切存在しない場合はSessionNotFoundErrorを送出すること"""
    (tmp_path / "projects").mkdir()

    discovery = LogDiscovery()
    with pytest.raises(SessionNotFoundError):
        discovery.discover("nonexistent-id", tmp_path)


def test_discover_raises_session_not_found_error_message(tmp_path):
    """SessionNotFoundErrorにセッションIDが含まれること"""
    (tmp_path / "projects").mkdir()

    discovery = LogDiscovery()
    with pytest.raises(SessionNotFoundError) as exc_info:
        discovery.discover("my-session-id", tmp_path)
    assert "my-session-id" in str(exc_info.value)
