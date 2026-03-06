"""タスク4: SessionAnalyzer パイプライン接続テスト"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    SessionReport,
    SkillReport,
    SubAgentReport,
    TextBlock,
    ThinkingReport,
    TokenReport,
    TokenUsageStats,
    ToolReport,
    ToolUseBlock,
    UsageData,
    UserEntry,
)
from session_analyzer.session_analyzer import SessionAnalyzer


def _make_minimal_report(session_id: str = "test-session") -> SessionReport:
    """最小構成の SessionReport を返す"""
    total = TokenUsageStats(
        model="total",
        input_tokens=0,
        output_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        estimated_cost_usd=None,
    )
    return SessionReport(
        session_id=session_id,
        token=TokenReport(by_model=[], total=total),
        skills=SkillReport(invocations=[], summary={}),
        tools=ToolReport(tool_counts={}, bash_invocations=[], bash_aggregation=[]),
        sub_agents=SubAgentReport(agents=[]),
        thinking=ThinkingReport(entries=[], has_thinking=False),
    )


def _make_parsed_session(session_id: str = "test-session") -> ParsedSession:
    """最小構成の ParsedSession を返す"""
    entry = AssistantEntry(
        uuid="msg-001",
        parent_uuid=None,
        timestamp="2026-01-01T00:00:00Z",
        model="claude-sonnet-4-6",
        content=[TextBlock(type="text", text="こんにちは")],
        usage=UsageData(),
        agent_id=None,
    )
    return ParsedSession(
        session_id=session_id,
        main_entries=[entry],
        subagent_entries={},
    )


class TestSessionAnalyzerPipeline:
    """SessionAnalyzer.run() が parsed と agent_link_map を HtmlReporter に渡すことを検証する"""

    def test_run_passes_parsed_to_html_reporter(self, tmp_path: Path) -> None:
        """run() が HtmlReporter.generate() に parsed を渡すこと"""
        output = tmp_path / "out.html"
        parsed = _make_parsed_session("sess-task4")
        report = _make_minimal_report("sess-task4")

        with (
            patch(
                "session_analyzer.session_analyzer.LogDiscovery"
            ) as mock_discovery,
            patch(
                "session_analyzer.session_analyzer.LogParser"
            ) as mock_parser,
            patch(
                "session_analyzer.session_analyzer.TokenAnalyzer"
            ) as mock_token,
            patch(
                "session_analyzer.session_analyzer.SkillAnalyzer"
            ) as mock_skill,
            patch(
                "session_analyzer.session_analyzer.ToolAnalyzer"
            ) as mock_tool,
            patch(
                "session_analyzer.session_analyzer.SubAgentAnalyzer"
            ) as mock_subagent,
            patch(
                "session_analyzer.session_analyzer.ThinkingAnalyzer"
            ) as mock_thinking,
            patch(
                "session_analyzer.session_analyzer.HtmlReporter"
            ) as mock_reporter_cls,
        ):
            # ディスカバリとパーサーのモック設定
            mock_discovery.return_value.discover.return_value = []
            mock_parser.return_value.parse.return_value = parsed
            mock_token.return_value.analyze.return_value = report.token
            mock_skill.return_value.analyze.return_value = report.skills
            mock_tool.return_value.analyze.return_value = report.tools
            mock_subagent.return_value.analyze.return_value = report.sub_agents
            mock_thinking.return_value.analyze.return_value = report.thinking

            mock_reporter = MagicMock()
            mock_reporter.generate.return_value = output
            mock_reporter_cls.return_value = mock_reporter

            SessionAnalyzer().run("sess-task4", Path("/fake"), output)

            # HtmlReporter.generate() が parsed を引数に含めて呼ばれたか検証
            call_args = mock_reporter.generate.call_args
            assert call_args is not None, "HtmlReporter.generate() が呼ばれていない"
            # positional args を確認: (report, parsed, agent_link_map, output_path)
            args = call_args.args
            assert len(args) >= 2, "parsed が渡されていない"
            assert args[1] is parsed, "parsed が正しく渡されていない"

    def test_run_passes_agent_link_map_to_html_reporter(self, tmp_path: Path) -> None:
        """run() が HtmlReporter.generate() に agent_link_map を渡すこと"""
        output = tmp_path / "out.html"

        # サブエージェント付き ParsedSession を作成
        agent_block = ToolUseBlock(type="tool_use", id="tool-001", name="Agent", input={"prompt": "do something"})
        entry = AssistantEntry(
            uuid="msg-001",
            parent_uuid=None,
            timestamp="2026-01-01T00:00:00Z",
            model="claude-sonnet-4-6",
            content=[agent_block],
            usage=UsageData(),
            agent_id=None,
        )
        subagent_entry = UserEntry(
            uuid="msg-002",
            parent_uuid=None,
            timestamp="2026-01-01T00:01:00Z",
            is_meta=False,
            content="hello",
            agent_id=None,
        )
        parsed = ParsedSession(
            session_id="sess-link-test",
            main_entries=[entry],
            subagent_entries={"subagent-file-001.jsonl": [subagent_entry]},
        )
        report = _make_minimal_report("sess-link-test")

        with (
            patch("session_analyzer.session_analyzer.LogDiscovery") as mock_discovery,
            patch("session_analyzer.session_analyzer.LogParser") as mock_parser,
            patch("session_analyzer.session_analyzer.TokenAnalyzer") as mock_token,
            patch("session_analyzer.session_analyzer.SkillAnalyzer") as mock_skill,
            patch("session_analyzer.session_analyzer.ToolAnalyzer") as mock_tool,
            patch("session_analyzer.session_analyzer.SubAgentAnalyzer") as mock_subagent,
            patch("session_analyzer.session_analyzer.ThinkingAnalyzer") as mock_thinking,
            patch("session_analyzer.session_analyzer.HtmlReporter") as mock_reporter_cls,
        ):
            mock_discovery.return_value.discover.return_value = []
            mock_parser.return_value.parse.return_value = parsed
            mock_token.return_value.analyze.return_value = report.token
            mock_skill.return_value.analyze.return_value = report.skills
            mock_tool.return_value.analyze.return_value = report.tools
            mock_subagent.return_value.analyze.return_value = report.sub_agents
            mock_thinking.return_value.analyze.return_value = report.thinking

            mock_reporter = MagicMock()
            mock_reporter.generate.return_value = output
            mock_reporter_cls.return_value = mock_reporter

            SessionAnalyzer().run("sess-link-test", Path("/fake"), output)

            call_args = mock_reporter.generate.call_args
            args = call_args.args
            # 3番目の引数が agent_link_map
            assert len(args) >= 3, "agent_link_map が渡されていない"
            agent_link_map = args[2]
            assert isinstance(agent_link_map, dict), "agent_link_map が dict でない"
            # tool-001 が subagent-file-001.jsonl にマッピングされているか
            assert "tool-001" in agent_link_map, "Agent ToolUseBlock.id がマップに含まれていない"
            assert agent_link_map["tool-001"] == "subagent-file-001.jsonl"

    def test_generated_html_has_no_external_resources(self, tmp_path: Path) -> None:
        """生成 HTML に http:// や https:// などの外部リソース参照がないこと（file:// 完全動作維持）"""
        output = tmp_path / "out.html"
        parsed = _make_parsed_session("sess-no-ext")
        report = _make_minimal_report("sess-no-ext")

        with (
            patch("session_analyzer.session_analyzer.LogDiscovery") as mock_discovery,
            patch("session_analyzer.session_analyzer.LogParser") as mock_parser,
            patch("session_analyzer.session_analyzer.TokenAnalyzer") as mock_token,
            patch("session_analyzer.session_analyzer.SkillAnalyzer") as mock_skill,
            patch("session_analyzer.session_analyzer.ToolAnalyzer") as mock_tool,
            patch("session_analyzer.session_analyzer.SubAgentAnalyzer") as mock_subagent,
            patch("session_analyzer.session_analyzer.ThinkingAnalyzer") as mock_thinking,
        ):
            mock_discovery.return_value.discover.return_value = []
            mock_parser.return_value.parse.return_value = parsed
            mock_token.return_value.analyze.return_value = report.token
            mock_skill.return_value.analyze.return_value = report.skills
            mock_tool.return_value.analyze.return_value = report.tools
            mock_subagent.return_value.analyze.return_value = report.sub_agents
            mock_thinking.return_value.analyze.return_value = report.thinking

            # 実際の HtmlReporter を使ってファイルを生成
            from session_analyzer.reporter import HtmlReporter
            with patch("session_analyzer.session_analyzer.HtmlReporter", HtmlReporter):
                SessionAnalyzer().run("sess-no-ext", Path("/fake"), output)

        content = output.read_text(encoding="utf-8")
        # 外部 URL 参照がないことを確認（src=, href= などで始まる外部リンク）
        import re
        external_refs = re.findall(r'(?:src|href)=["\']https?://', content)
        assert not external_refs, f"外部リソース参照が含まれている: {external_refs}"

    def test_generated_html_contains_log_detail_tab(self, tmp_path: Path) -> None:
        """生成 HTML に「ログ詳細」タブが含まれること"""
        output = tmp_path / "out.html"
        parsed = _make_parsed_session("sess-log-tab")
        report = _make_minimal_report("sess-log-tab")

        with (
            patch("session_analyzer.session_analyzer.LogDiscovery") as mock_discovery,
            patch("session_analyzer.session_analyzer.LogParser") as mock_parser,
            patch("session_analyzer.session_analyzer.TokenAnalyzer") as mock_token,
            patch("session_analyzer.session_analyzer.SkillAnalyzer") as mock_skill,
            patch("session_analyzer.session_analyzer.ToolAnalyzer") as mock_tool,
            patch("session_analyzer.session_analyzer.SubAgentAnalyzer") as mock_subagent,
            patch("session_analyzer.session_analyzer.ThinkingAnalyzer") as mock_thinking,
        ):
            mock_discovery.return_value.discover.return_value = []
            mock_parser.return_value.parse.return_value = parsed
            mock_token.return_value.analyze.return_value = report.token
            mock_skill.return_value.analyze.return_value = report.skills
            mock_tool.return_value.analyze.return_value = report.tools
            mock_subagent.return_value.analyze.return_value = report.sub_agents
            mock_thinking.return_value.analyze.return_value = report.thinking

            from session_analyzer.reporter import HtmlReporter
            with patch("session_analyzer.session_analyzer.HtmlReporter", HtmlReporter):
                SessionAnalyzer().run("sess-log-tab", Path("/fake"), output)

        content = output.read_text(encoding="utf-8")
        assert "ログ詳細" in content, "「ログ詳細」タブが HTML に含まれていない"
        # ログエントリのコンテンツが含まれること
        assert "こんにちは" in content, "ログエントリの内容が HTML に含まれていない"
