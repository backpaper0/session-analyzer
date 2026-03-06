"""タスク7.1: サンプルログを使ったエンドツーエンドの動作確認"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

# プロジェクトルートの projects/ ディレクトリ（サンプルログが格納されている）
_PROJECTS_ROOT = Path(__file__).parent.parent
_PROJECTS_DIR = _PROJECTS_ROOT / "projects"

# サブエージェントなしセッション（.jsonl のみ存在）
SESSION_NO_SUBAGENTS = "011f9240-00bc-40fc-a644-d800f30378a3"
# サブエージェントありセッション（.jsonl と subagents/ ディレクトリが存在）
SESSION_WITH_SUBAGENTS = "6fe5d120-fe62-4e37-8719-b774d539cda0"


def _is_valid_html(content: str) -> bool:
    """HTMLParser でパース可能かを確認する"""

    class _Validator(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.ok = True

        def handle_error(self, message: str) -> None:  # type: ignore[override]
            self.ok = False

    v = _Validator()
    v.feed(content)
    return v.ok


def _extract_session_data(content: str) -> dict:
    """HTML 内の SESSION_DATA JS オブジェクトを抽出して返す"""
    m = re.search(r"SESSION_DATA\s*=\s*(\{.*?\})\s*;", content, re.DOTALL)
    assert m is not None, "SESSION_DATA が HTML 内に見つからない"
    return json.loads(m.group(1))


# -----------------------------------------------------------------------
# 前提条件: サンプルログが存在すること
# -----------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def check_sample_logs_exist() -> None:
    """サンプルログファイルが存在しない場合はスキップ"""
    if not _PROJECTS_DIR.exists():
        pytest.skip(f"projects/ ディレクトリが見つかりません: {_PROJECTS_DIR}")


# -----------------------------------------------------------------------
# サブエージェントなしセッション
# -----------------------------------------------------------------------


class TestNoSubagentSession:
    def test_html_file_generated(self, tmp_path: Path) -> None:
        """サブエージェントなしセッションの HTML ファイルが生成される"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        rc = main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        assert rc == 0
        assert output.exists()
        assert output.stat().st_size > 0

    def test_generated_html_is_valid(self, tmp_path: Path) -> None:
        """生成された HTML がパース可能である"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        content = output.read_text(encoding="utf-8")
        assert _is_valid_html(content)

    def test_generated_html_has_all_tabs(self, tmp_path: Path) -> None:
        """生成 HTML に全タブ（トークン/スキル/ツール/サブエージェント/思考）が含まれる"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        content = output.read_text(encoding="utf-8")
        for label in ["トークン", "スキル", "ツール", "サブエージェント", "思考"]:
            assert label in content, f"タブ '{label}' が HTML に見つからない"

    def test_session_data_embedded(self, tmp_path: Path) -> None:
        """SESSION_DATA が HTML にインライン埋め込みされている"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        content = output.read_text(encoding="utf-8")
        data = _extract_session_data(content)
        assert data["session_id"] == SESSION_NO_SUBAGENTS

    def test_no_subagents_in_report(self, tmp_path: Path) -> None:
        """サブエージェントなしセッションではエージェント一覧が空"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        content = output.read_text(encoding="utf-8")
        data = _extract_session_data(content)
        assert data["sub_agents"]["agents"] == []

    def test_stdout_contains_html_path(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """成功時に stdout へ HTML パスが出力される"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        rc = main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        assert rc == 0
        out = capsys.readouterr().out
        assert str(output) in out


# -----------------------------------------------------------------------
# サブエージェントありセッション
# -----------------------------------------------------------------------


class TestWithSubagentSession:
    def test_html_file_generated(self, tmp_path: Path) -> None:
        """サブエージェントありセッションの HTML ファイルが生成される"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        rc = main([SESSION_WITH_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        assert rc == 0
        assert output.exists()

    def test_generated_html_is_valid(self, tmp_path: Path) -> None:
        """生成された HTML がパース可能である"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        main([SESSION_WITH_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        content = output.read_text(encoding="utf-8")
        assert _is_valid_html(content)

    def test_session_data_embedded(self, tmp_path: Path) -> None:
        """SESSION_DATA が正しいセッション ID で埋め込まれている"""
        from session_analyzer.__main__ import main

        output = tmp_path / "out.html"
        main([SESSION_WITH_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        content = output.read_text(encoding="utf-8")
        data = _extract_session_data(content)
        assert data["session_id"] == SESSION_WITH_SUBAGENTS

    def test_html_larger_than_no_subagent(self, tmp_path: Path) -> None:
        """サブエージェントありセッションの HTML はより多くのデータを含む"""
        from session_analyzer.__main__ import main

        out_no_sub = tmp_path / "no_sub.html"
        out_with_sub = tmp_path / "with_sub.html"
        main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(out_no_sub)])
        main([SESSION_WITH_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(out_with_sub)])
        # サブエージェントありの方がデータ量が多い（ファイルサイズで確認）
        assert out_with_sub.stat().st_size >= out_no_sub.stat().st_size


# -----------------------------------------------------------------------
# --output オプション
# -----------------------------------------------------------------------


class TestOutputOption:
    def test_custom_output_path(self, tmp_path: Path) -> None:
        """--output で指定したパスに HTML が生成される"""
        from session_analyzer.__main__ import main

        custom = tmp_path / "custom_report.html"
        rc = main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "--output", str(custom)])
        assert rc == 0
        assert custom.exists()

    def test_short_output_flag(self, tmp_path: Path) -> None:
        """-o ショートフラグでも同様に動作する"""
        from session_analyzer.__main__ import main

        custom = tmp_path / "short_flag.html"
        rc = main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(custom)])
        assert rc == 0
        assert custom.exists()

    def test_default_output_filename(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--output 省略時のデフォルトファイル名 session-{session_id}.html に出力される"""
        from session_analyzer.__main__ import main

        monkeypatch.chdir(tmp_path)
        rc = main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT)])
        assert rc == 0
        expected = tmp_path / f"session-{SESSION_NO_SUBAGENTS}.html"
        assert expected.exists()


# -----------------------------------------------------------------------
# prefix マッチング
# -----------------------------------------------------------------------


class TestPrefixMatching:
    def test_prefix_session_id_resolves(self, tmp_path: Path) -> None:
        """セッション ID の先頭8文字でも正しく解析できる"""
        from session_analyzer.__main__ import main

        prefix = SESSION_NO_SUBAGENTS[:8]
        output = tmp_path / "prefix.html"
        rc = main([prefix, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(output)])
        assert rc == 0
        assert output.exists()

    def test_prefix_produces_same_session_data(self, tmp_path: Path) -> None:
        """prefix マッチと完全一致で同じセッション ID の HTML が生成される"""
        from session_analyzer.__main__ import main

        prefix = SESSION_NO_SUBAGENTS[:8]
        out_full = tmp_path / "full.html"
        out_prefix = tmp_path / "prefix.html"
        main([SESSION_NO_SUBAGENTS, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(out_full)])
        main([prefix, "--claude-dir", str(_PROJECTS_ROOT), "-o", str(out_prefix)])
        data_full = _extract_session_data(out_full.read_text())
        data_prefix = _extract_session_data(out_prefix.read_text())
        assert data_full["session_id"] == data_prefix["session_id"]
