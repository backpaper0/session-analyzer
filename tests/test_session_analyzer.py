"""タスク6.2: SessionAnalyzer オーケストレーターテスト"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    SessionFiles,
    SessionReport,
    SkillReport,
    SubAgentReport,
    ThinkingReport,
    TokenReport,
    TokenUsageStats,
    ToolReport,
    ToolUseBlock,
    UsageData,
    UserEntry,
)
from session_analyzer.session_analyzer import SessionAnalyzer, _build_agent_link_map


def _make_session_files(tmp_path: Path) -> SessionFiles:
    main = tmp_path / "session-abc.jsonl"
    main.write_text('{"type":"system","content":"hi"}\n')
    return SessionFiles(main=main, subagents=[])


def _make_parsed_session() -> ParsedSession:
    return ParsedSession(session_id="abc", main_entries=[], subagent_entries={})


def _make_session_report() -> SessionReport:
    total = TokenUsageStats(
        model="total",
        input_tokens=0,
        output_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        estimated_cost_usd=0.0,
    )
    return SessionReport(
        session_id="abc",
        token=TokenReport(by_model=[], total=total),
        skills=SkillReport(invocations=[], summary={}),
        tools=ToolReport(tool_counts={}, bash_invocations=[], bash_aggregation=[]),
        sub_agents=SubAgentReport(agents=[]),
        thinking=ThinkingReport(entries=[], has_thinking=False),
    )


# -----------------------------------------------------------------------
# 基本インターフェース
# -----------------------------------------------------------------------


class TestSessionAnalyzerInterface:
    def test_has_run_method(self) -> None:
        """SessionAnalyzer に run() メソッドがある"""
        assert hasattr(SessionAnalyzer, "run")
        assert callable(SessionAnalyzer.run)

    def test_run_returns_path(self, tmp_path: Path) -> None:
        """run() が Path を返す"""
        session_files = _make_session_files(tmp_path)
        parsed = _make_parsed_session()
        report = _make_session_report()
        output = tmp_path / "out.html"

        with (
            patch("session_analyzer.session_analyzer.LogDiscovery") as MockDiscovery,
            patch("session_analyzer.session_analyzer.LogParser") as MockParser,
            patch("session_analyzer.session_analyzer.TokenAnalyzer") as MockToken,
            patch("session_analyzer.session_analyzer.SkillAnalyzer") as MockSkill,
            patch("session_analyzer.session_analyzer.ToolAnalyzer") as MockTool,
            patch("session_analyzer.session_analyzer.SubAgentAnalyzer") as MockSubAgent,
            patch("session_analyzer.session_analyzer.ThinkingAnalyzer") as MockThinking,
            patch("session_analyzer.session_analyzer.HtmlReporter") as MockReporter,
        ):
            MockDiscovery.return_value.discover.return_value = session_files
            MockParser.return_value.parse.return_value = parsed
            MockToken.return_value.analyze.return_value = report.token
            MockSkill.return_value.analyze.return_value = report.skills
            MockTool.return_value.analyze.return_value = report.tools
            MockSubAgent.return_value.analyze.return_value = report.sub_agents
            MockThinking.return_value.analyze.return_value = report.thinking
            MockReporter.return_value.generate.return_value = output

            result = SessionAnalyzer().run("abc", tmp_path, output)

        assert isinstance(result, Path)


# -----------------------------------------------------------------------
# パイプライン呼び出し順序
# -----------------------------------------------------------------------


class TestPipelineOrchestration:
    def _run_with_mocks(self, tmp_path: Path):
        """モック付きで run() を呼び出す共通ヘルパー"""
        session_files = _make_session_files(tmp_path)
        parsed = _make_parsed_session()
        report = _make_session_report()
        output = tmp_path / "out.html"

        mocks: dict[str, MagicMock] = {}
        with (
            patch("session_analyzer.session_analyzer.LogDiscovery") as MockDiscovery,
            patch("session_analyzer.session_analyzer.LogParser") as MockParser,
            patch("session_analyzer.session_analyzer.TokenAnalyzer") as MockToken,
            patch("session_analyzer.session_analyzer.SkillAnalyzer") as MockSkill,
            patch("session_analyzer.session_analyzer.ToolAnalyzer") as MockTool,
            patch("session_analyzer.session_analyzer.SubAgentAnalyzer") as MockSubAgent,
            patch("session_analyzer.session_analyzer.ThinkingAnalyzer") as MockThinking,
            patch("session_analyzer.session_analyzer.HtmlReporter") as MockReporter,
        ):
            MockDiscovery.return_value.discover.return_value = session_files
            MockParser.return_value.parse.return_value = parsed
            MockToken.return_value.analyze.return_value = report.token
            MockSkill.return_value.analyze.return_value = report.skills
            MockTool.return_value.analyze.return_value = report.tools
            MockSubAgent.return_value.analyze.return_value = report.sub_agents
            MockThinking.return_value.analyze.return_value = report.thinking
            MockReporter.return_value.generate.return_value = output

            mocks["discovery"] = MockDiscovery.return_value
            mocks["parser"] = MockParser.return_value
            mocks["token"] = MockToken.return_value
            mocks["skill"] = MockSkill.return_value
            mocks["tool"] = MockTool.return_value
            mocks["subagent"] = MockSubAgent.return_value
            mocks["thinking"] = MockThinking.return_value
            mocks["reporter"] = MockReporter.return_value

            SessionAnalyzer().run("abc", tmp_path, output)

        return mocks

    def test_discovery_called_with_session_id_and_claude_dir(
        self, tmp_path: Path
    ) -> None:
        """LogDiscovery.discover() が session_id と claude_dir で呼ばれる"""
        mocks = self._run_with_mocks(tmp_path)
        mocks["discovery"].discover.assert_called_once_with("abc", tmp_path)

    def test_parser_called_with_session_files(self, tmp_path: Path) -> None:
        """LogParser.parse() が SessionFiles で呼ばれる"""
        mocks = self._run_with_mocks(tmp_path)
        mocks["parser"].parse.assert_called_once()

    def test_all_five_analyzers_called(self, tmp_path: Path) -> None:
        """5つのアナライザーが全て呼ばれる"""
        mocks = self._run_with_mocks(tmp_path)
        mocks["token"].analyze.assert_called_once()
        mocks["skill"].analyze.assert_called_once()
        mocks["tool"].analyze.assert_called_once()
        mocks["subagent"].analyze.assert_called_once()
        mocks["thinking"].analyze.assert_called_once()

    def test_reporter_called_with_session_report_and_output_path(
        self, tmp_path: Path
    ) -> None:
        """HtmlReporter.generate() が SessionReport と output_path で呼ばれる"""
        mocks = self._run_with_mocks(tmp_path)
        mocks["reporter"].generate.assert_called_once()
        call_args = mocks["reporter"].generate.call_args
        report_arg = call_args[0][0]
        assert isinstance(report_arg, SessionReport)
        assert report_arg.session_id == "abc"


# -----------------------------------------------------------------------
# SessionReport 組み立て
# -----------------------------------------------------------------------


class TestSessionReportAssembly:
    def test_session_report_contains_correct_session_id(self, tmp_path: Path) -> None:
        """run() が組み立てる SessionReport に正しい session_id が含まれる"""
        session_files = _make_session_files(tmp_path)
        parsed = _make_parsed_session()
        report = _make_session_report()
        output = tmp_path / "out.html"
        captured_report: list[SessionReport] = []

        def fake_generate(r: SessionReport, parsed, agent_link_map, p: Path) -> Path:
            captured_report.append(r)
            return p

        with (
            patch("session_analyzer.session_analyzer.LogDiscovery") as MockDiscovery,
            patch("session_analyzer.session_analyzer.LogParser") as MockParser,
            patch("session_analyzer.session_analyzer.TokenAnalyzer") as MockToken,
            patch("session_analyzer.session_analyzer.SkillAnalyzer") as MockSkill,
            patch("session_analyzer.session_analyzer.ToolAnalyzer") as MockTool,
            patch("session_analyzer.session_analyzer.SubAgentAnalyzer") as MockSubAgent,
            patch("session_analyzer.session_analyzer.ThinkingAnalyzer") as MockThinking,
            patch("session_analyzer.session_analyzer.HtmlReporter") as MockReporter,
        ):
            MockDiscovery.return_value.discover.return_value = session_files
            MockParser.return_value.parse.return_value = parsed
            MockToken.return_value.analyze.return_value = report.token
            MockSkill.return_value.analyze.return_value = report.skills
            MockTool.return_value.analyze.return_value = report.tools
            MockSubAgent.return_value.analyze.return_value = report.sub_agents
            MockThinking.return_value.analyze.return_value = report.thinking
            MockReporter.return_value.generate.side_effect = fake_generate

            SessionAnalyzer().run("abc", tmp_path, output)

        assert len(captured_report) == 1
        assert captured_report[0].session_id == "abc"


# -----------------------------------------------------------------------
# _run_pipeline との統合（CLI 接続）
# -----------------------------------------------------------------------


# -----------------------------------------------------------------------
# _build_agent_link_map
# -----------------------------------------------------------------------


def _make_assistant_entry(
    blocks: list, timestamp: str = "2026-01-01T00:00:00Z"
) -> AssistantEntry:
    """テスト用 AssistantEntry を生成するヘルパー"""
    return AssistantEntry(
        uuid="uuid-test",
        parent_uuid=None,
        timestamp=timestamp,
        model="claude-test",
        content=blocks,
        usage=UsageData(),
        agent_id=None,
    )


class TestBuildAgentLinkMap:
    def test_agent_tool_use_blocks_mapped_to_subagent_keys(self) -> None:
        """Agent ToolUseBlock が 2 件、サブエージェントキーが 2 件の場合に正しくマッピングされる"""
        block1 = ToolUseBlock(type="tool_use", id="id-001", name="Agent", input={})
        block2 = ToolUseBlock(type="tool_use", id="id-002", name="Agent", input={})
        entry = _make_assistant_entry([block1, block2])
        parsed = ParsedSession(
            session_id="s1",
            main_entries=[entry],
            subagent_entries={"agent-aaa": [], "agent-bbb": []},
        )

        result = _build_agent_link_map(parsed)

        assert result == {"id-001": "agent-aaa", "id-002": "agent-bbb"}

    def test_task_tool_use_blocks_are_also_mapped(self) -> None:
        """Task ToolUseBlock も Agent と同様にマッピングされる"""
        block = ToolUseBlock(type="tool_use", id="id-task-1", name="Task", input={})
        entry = _make_assistant_entry([block])
        parsed = ParsedSession(
            session_id="s2",
            main_entries=[entry],
            subagent_entries={"agent-ccc": []},
        )

        result = _build_agent_link_map(parsed)

        assert result == {"id-task-1": "agent-ccc"}

    def test_excess_agent_calls_not_in_map_when_fewer_subagents(self) -> None:
        """Agent 呼び出し数よりサブエージェント数が少ない場合、超過分はマッピングに含まれない"""
        block1 = ToolUseBlock(type="tool_use", id="id-a", name="Agent", input={})
        block2 = ToolUseBlock(type="tool_use", id="id-b", name="Agent", input={})
        block3 = ToolUseBlock(type="tool_use", id="id-c", name="Agent", input={})
        entry = _make_assistant_entry([block1, block2, block3])
        parsed = ParsedSession(
            session_id="s3",
            main_entries=[entry],
            subagent_entries={"agent-x": []},
        )

        result = _build_agent_link_map(parsed)

        assert result == {"id-a": "agent-x"}
        assert "id-b" not in result
        assert "id-c" not in result

    def test_non_subagent_tools_not_in_map(self) -> None:
        """Agent および Task 以外のツール呼び出しがマッピングに含まれない"""
        bash_block = ToolUseBlock(type="tool_use", id="id-bash", name="Bash", input={})
        agent_block = ToolUseBlock(
            type="tool_use", id="id-agent", name="Agent", input={}
        )
        read_block = ToolUseBlock(type="tool_use", id="id-read", name="Read", input={})
        entry = _make_assistant_entry([bash_block, agent_block, read_block])
        parsed = ParsedSession(
            session_id="s4",
            main_entries=[entry],
            subagent_entries={"agent-y": []},
        )

        result = _build_agent_link_map(parsed)

        assert result == {"id-agent": "agent-y"}
        assert "id-bash" not in result
        assert "id-read" not in result

    def test_empty_main_entries_returns_empty_map(self) -> None:
        """main_entries が空の場合に空の辞書を返す"""
        parsed = ParsedSession(
            session_id="s5",
            main_entries=[],
            subagent_entries={"agent-z": []},
        )

        result = _build_agent_link_map(parsed)

        assert result == {}

    def test_no_subagent_entries_returns_empty_map(self) -> None:
        """サブエージェントエントリがない場合に空の辞書を返す"""
        block = ToolUseBlock(type="tool_use", id="id-a1", name="Agent", input={})
        entry = _make_assistant_entry([block])
        parsed = ParsedSession(
            session_id="s6",
            main_entries=[entry],
            subagent_entries={},
        )

        result = _build_agent_link_map(parsed)

        assert result == {}

    def test_user_entries_are_skipped(self) -> None:
        """UserEntry はスキップされる（ToolUseBlock があっても無視）"""
        user_entry = UserEntry(
            uuid="u1",
            parent_uuid=None,
            timestamp="2026-01-01T00:00:00Z",
            is_meta=False,
            content=[
                ToolUseBlock(
                    type="tool_use", id="id-user-block", name="Agent", input={}
                )
            ],
            agent_id=None,
        )
        agent_block = ToolUseBlock(
            type="tool_use", id="id-assistant", name="Agent", input={}
        )
        assistant_entry = _make_assistant_entry([agent_block])
        parsed = ParsedSession(
            session_id="s7",
            main_entries=[user_entry, assistant_entry],
            subagent_entries={"agent-w": []},
        )

        result = _build_agent_link_map(parsed)

        # AssistantEntry 内の Agent ブロックのみがマッピングされる
        assert result == {"id-assistant": "agent-w"}
        assert "id-user-block" not in result


class TestCliIntegration:
    def test_run_pipeline_uses_session_analyzer(self, tmp_path: Path) -> None:
        """CLI の _run_pipeline() が SessionAnalyzer.run() を呼び出す"""
        from session_analyzer.__main__ import _run_pipeline

        expected = tmp_path / "out.html"
        with patch("session_analyzer.__main__.SessionAnalyzer") as MockAnalyzer:
            MockAnalyzer.return_value.run.return_value = expected
            result = _run_pipeline("abc", tmp_path, expected)

        MockAnalyzer.return_value.run.assert_called_once_with("abc", tmp_path, expected)
        assert result == expected

    def test_main_success_with_session_analyzer(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """main() が SessionAnalyzer 経由で成功する場合は exit code 0 を返す"""
        from session_analyzer.__main__ import main

        expected = tmp_path / "session-testid.html"
        with patch("session_analyzer.__main__.SessionAnalyzer") as MockAnalyzer:
            MockAnalyzer.return_value.run.return_value = expected
            result = main(["testid", "--output", str(expected)])

        assert result == 0
        out = capsys.readouterr().out
        assert str(expected) in out
