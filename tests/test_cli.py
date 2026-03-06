"""タスク6.1: argparse による CLI 実装テスト"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from session_analyzer.__main__ import main
from session_analyzer.exceptions import (
    AmbiguousSessionError,
    ReportGenerationError,
    SessionNotFoundError,
)

# パイプライン実行関数のモックターゲット
_PIPELINE_TARGET = "session_analyzer.__main__._run_pipeline"


def _mock_pipeline(return_path: Path = Path("/tmp/session-abc.html")):
    """_run_pipeline をモックするコンテキストマネージャーを返す"""
    return patch(_PIPELINE_TARGET, return_value=return_path)


# -----------------------------------------------------------------------
# argparse の基本動作
# -----------------------------------------------------------------------


class TestArgparseBehavior:
    def test_help_exits_zero(self) -> None:
        """--help は exit code 0 で終了する"""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_missing_session_id_exits_nonzero(self) -> None:
        """session_id がない場合は exit code != 0"""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code != 0

    def test_main_returns_int(self) -> None:
        """main() が int を返す"""
        with _mock_pipeline():
            result = main(["abc123"])
        assert isinstance(result, int)


# -----------------------------------------------------------------------
# デフォルト出力パス
# -----------------------------------------------------------------------


class TestDefaultOutputPath:
    def test_default_output_is_session_id_html(self, tmp_path: Path) -> None:
        """--output 省略時のデフォルトは session-{session_id}.html"""
        captured_path: list[Path] = []

        def fake_pipeline(session_id: str, claude_dir: Path, output_path: Path) -> Path:
            captured_path.append(output_path)
            return output_path

        with patch(_PIPELINE_TARGET, side_effect=fake_pipeline):
            main(["my-session-id"])

        assert len(captured_path) == 1
        assert captured_path[0].name == "session-my-session-id.html"

    def test_custom_output_overrides_default(self, tmp_path: Path) -> None:
        """--output で指定したパスが使われる"""
        captured_path: list[Path] = []

        def fake_pipeline(session_id: str, claude_dir: Path, output_path: Path) -> Path:
            captured_path.append(output_path)
            return output_path

        custom = str(tmp_path / "custom_report.html")
        with patch(_PIPELINE_TARGET, side_effect=fake_pipeline):
            main(["abc", "--output", custom])

        assert len(captured_path) == 1
        assert captured_path[0] == Path(custom)

    def test_output_short_option(self, tmp_path: Path) -> None:
        """-o が --output の短縮形として機能する"""
        captured_path: list[Path] = []

        def fake_pipeline(session_id: str, claude_dir: Path, output_path: Path) -> Path:
            captured_path.append(output_path)
            return output_path

        custom = str(tmp_path / "short.html")
        with patch(_PIPELINE_TARGET, side_effect=fake_pipeline):
            main(["abc", "-o", custom])

        assert len(captured_path) == 1
        assert captured_path[0] == Path(custom)


# -----------------------------------------------------------------------
# Claude ディレクトリ解決
# -----------------------------------------------------------------------


class TestClaudeDirResolution:
    def test_claude_dir_option_is_used(self) -> None:
        """--claude-dir で指定したパスが claude_dir として渡される"""
        captured: list[Path] = []

        def fake_pipeline(session_id: str, claude_dir: Path, output_path: Path) -> Path:
            captured.append(claude_dir)
            return output_path

        with patch(_PIPELINE_TARGET, side_effect=fake_pipeline):
            main(["abc", "--claude-dir", "/tmp/my-claude"])

        assert captured[0] == Path("/tmp/my-claude")

    def test_env_var_fallback(self) -> None:
        """CLAUDE_CONFIG_DIR 環境変数がフォールバックになる"""
        captured: list[Path] = []

        def fake_pipeline(session_id: str, claude_dir: Path, output_path: Path) -> Path:
            captured.append(claude_dir)
            return output_path

        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/env/claude"}):
            with patch(_PIPELINE_TARGET, side_effect=fake_pipeline):
                main(["abc"])

        assert captured[0] == Path("/env/claude")

    def test_home_dot_claude_default(self) -> None:
        """--claude-dir も CLAUDE_CONFIG_DIR もない場合は $HOME/.claude"""
        captured: list[Path] = []

        def fake_pipeline(session_id: str, claude_dir: Path, output_path: Path) -> Path:
            captured.append(claude_dir)
            return output_path

        env_without_config = {
            k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"
        }
        with patch.dict(os.environ, env_without_config, clear=True):
            with patch(_PIPELINE_TARGET, side_effect=fake_pipeline):
                main(["abc"])

        assert captured[0] == Path.home() / ".claude"

    def test_claude_dir_option_takes_priority_over_env(self) -> None:
        """--claude-dir は CLAUDE_CONFIG_DIR 環境変数より優先される"""
        captured: list[Path] = []

        def fake_pipeline(session_id: str, claude_dir: Path, output_path: Path) -> Path:
            captured.append(claude_dir)
            return output_path

        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/env/claude"}):
            with patch(_PIPELINE_TARGET, side_effect=fake_pipeline):
                main(["abc", "--claude-dir", "/opt/override"])

        assert captured[0] == Path("/opt/override")


# -----------------------------------------------------------------------
# 成功・エラーの exit code と出力
# -----------------------------------------------------------------------


class TestExitCodeAndOutput:
    def test_success_returns_zero(self, capsys: pytest.CaptureFixture) -> None:
        """成功時は exit code 0 を返す"""
        with _mock_pipeline(Path("/tmp/session-abc.html")):
            result = main(["abc"])
        assert result == 0

    def test_success_prints_html_path_to_stdout(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """成功時は HTML ファイルパスを stdout に出力する"""
        expected_path = Path("/tmp/session-abc.html")
        with _mock_pipeline(expected_path):
            main(["abc"])
        out = capsys.readouterr().out
        assert str(expected_path) in out

    def test_session_not_found_returns_one(self, capsys: pytest.CaptureFixture) -> None:
        """SessionNotFoundError 発生時は exit code 1 を返す"""
        with patch(_PIPELINE_TARGET, side_effect=SessionNotFoundError("abc")):
            result = main(["abc"])
        assert result == 1

    def test_session_not_found_prints_to_stderr(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """SessionNotFoundError のメッセージを stderr に出力する"""
        with patch(_PIPELINE_TARGET, side_effect=SessionNotFoundError("abc")):
            main(["abc"])
        err = capsys.readouterr().err
        assert "abc" in err

    def test_ambiguous_session_returns_one(self, capsys: pytest.CaptureFixture) -> None:
        """AmbiguousSessionError 発生時は exit code 1 を返す"""
        with patch(
            _PIPELINE_TARGET,
            side_effect=AmbiguousSessionError("abc", ["abc-1.jsonl", "abc-2.jsonl"]),
        ):
            result = main(["abc"])
        assert result == 1

    def test_ambiguous_session_prints_to_stderr(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """AmbiguousSessionError のメッセージを stderr に出力する"""
        with patch(
            _PIPELINE_TARGET,
            side_effect=AmbiguousSessionError("abc", ["abc-1.jsonl", "abc-2.jsonl"]),
        ):
            main(["abc"])
        err = capsys.readouterr().err
        assert "abc" in err

    def test_report_generation_error_returns_one(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """ReportGenerationError 発生時は exit code 1 を返す"""
        with patch(_PIPELINE_TARGET, side_effect=ReportGenerationError("disk full")):
            result = main(["abc"])
        assert result == 1

    def test_report_generation_error_prints_to_stderr(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """ReportGenerationError のメッセージを stderr に出力する"""
        with patch(_PIPELINE_TARGET, side_effect=ReportGenerationError("disk full")):
            main(["abc"])
        err = capsys.readouterr().err
        assert "disk full" in err or "Failed" in err
