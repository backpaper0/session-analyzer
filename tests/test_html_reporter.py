"""タスク5.1: HTMLテンプレートとデザイン基盤テスト"""
from pathlib import Path

import pytest

from session_analyzer.models import (
    AssistantEntry,
    BashInvocation,
    CommandAggregation,
    ParsedSession,
    SessionReport,
    SkillReport,
    SubAgentReport,
    TextBlock,
    ThinkingReport,
    TokenReport,
    TokenUsageStats,
    ToolReport,
    UserEntry,
    UsageData,
)
from session_analyzer.reporter import HtmlReporter


def _make_session_report(session_id: str = "test-abc") -> SessionReport:
    total = TokenUsageStats(
        model="total",
        input_tokens=0,
        output_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        estimated_cost_usd=0.0,
    )
    return SessionReport(
        session_id=session_id,
        token=TokenReport(by_model=[], total=total),
        skills=SkillReport(invocations=[], summary={}),
        tools=ToolReport(tool_counts={}, bash_invocations=[], bash_aggregation=[]),
        sub_agents=SubAgentReport(agents=[]),
        thinking=ThinkingReport(entries=[], has_thinking=False),
    )


class TestHtmlReporterBasic:
    def test_generate_returns_path(self, tmp_path: Path) -> None:
        """generate() が Path を返す"""
        result = HtmlReporter().generate(_make_session_report(), tmp_path / "out.html")
        assert isinstance(result, Path)

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        """generate() がファイルを生成する"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        assert out.exists()

    def test_generate_returns_absolute_path(self, tmp_path: Path) -> None:
        """generate() が絶対パスを返す"""
        out = tmp_path / "out.html"
        result = HtmlReporter().generate(_make_session_report(), out)
        assert result.is_absolute()

    def test_session_id_in_content(self, tmp_path: Path) -> None:
        """セッション ID がレポートに含まれる"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report("my-session-123"), out)
        assert "my-session-123" in out.read_text()


class TestHtmlReporterStructure:
    def test_valid_html_doctype(self, tmp_path: Path) -> None:
        """DOCTYPE 宣言がある"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        content = out.read_text().lower()
        assert "<!doctype html>" in content

    def test_has_head_and_body(self, tmp_path: Path) -> None:
        """<head> と <body> タグがある"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        content = out.read_text()
        assert "<head>" in content
        assert "<body>" in content

    def test_has_tab_navigation(self, tmp_path: Path) -> None:
        """5つのタブナビゲーション（トークン / スキル / ツール / サブエージェント / 思考ログ）が含まれる"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        content = out.read_text()
        for tab_label in ["トークン", "スキル", "ツール", "サブエージェント", "思考ログ"]:
            assert tab_label in content, f"タブ '{tab_label}' が見つからない"


class TestHtmlReporterInlineResources:
    def test_no_external_urls(self, tmp_path: Path) -> None:
        """外部リソース URL（https://）を含まない"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        assert "https://" not in out.read_text()

    def test_no_http_urls(self, tmp_path: Path) -> None:
        """http:// URL を含まない"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        assert "http://" not in out.read_text()

    def test_css_is_inline(self, tmp_path: Path) -> None:
        """CSS が <style> タグにインライン埋め込みされている"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        assert "<style>" in out.read_text()

    def test_js_is_inline(self, tmp_path: Path) -> None:
        """JS が <script> タグにインライン埋め込みされている"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        assert "<script>" in out.read_text()


class TestHtmlReporterDesign:
    def test_has_css_custom_properties(self, tmp_path: Path) -> None:
        """CSS カスタムプロパティ（--xxx）が定義されている（パステルカラーパレット）"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        content = out.read_text()
        assert "--" in content  # CSS custom property prefix

    def test_tab_switching_js_exists(self, tmp_path: Path) -> None:
        """タブ切り替え用の JS が存在する"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        content = out.read_text()
        # タブ切り替えには関数またはイベントリスナーが必要
        assert "function" in content or "addEventListener" in content


def _make_parsed_session(
    session_id: str = "test-session",
    with_subagent: bool = False,
) -> ParsedSession:
    """テスト用の ParsedSession を構築するヘルパー"""
    usage = UsageData(input_tokens=10, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=0)
    main_entry = AssistantEntry(
        uuid="uuid-1",
        parent_uuid=None,
        timestamp="2026-01-01T00:00:00Z",
        model="claude-test",
        content=[TextBlock(type="text", text="テストメッセージ")],
        usage=usage,
        agent_id=None,
    )
    subagent_entries: dict[str, list] = {}
    if with_subagent:
        sub_entry = UserEntry(
            uuid="uuid-2",
            parent_uuid=None,
            timestamp="2026-01-01T00:00:01Z",
            is_meta=False,
            content="サブエージェントメッセージ",
            agent_id="agent-abc123",
        )
        subagent_entries["agent-abc123"] = [sub_entry]
    return ParsedSession(
        session_id=session_id,
        main_entries=[main_entry],
        subagent_entries=subagent_entries,
    )


class TestHtmlReporterLogTab:
    """タスク 3.1: ログ詳細タブ統合テスト"""

    def test_log_tab_appears_in_html(self, tmp_path: Path) -> None:
        """generate() に ParsedSession を渡すと「ログ詳細」タブが生成 HTML に含まれる"""
        out = tmp_path / "out.html"
        parsed = _make_parsed_session()
        HtmlReporter().generate(_make_session_report(), parsed, {}, out)
        assert "ログ詳細" in out.read_text()

    def test_subagent_section_anchor_exists(self, tmp_path: Path) -> None:
        """サブエージェントが存在する場合、ページ内アンカーが生成 HTML に含まれる"""
        out = tmp_path / "out.html"
        parsed = _make_parsed_session(with_subagent=True)
        HtmlReporter().generate(_make_session_report(), parsed, {}, out)
        assert 'id="subagent-agent-abc123"' in out.read_text()

    def test_session_data_unchanged(self, tmp_path: Path) -> None:
        """SESSION_DATA が SessionReport の JSON のみを含む（ParsedSession は含まれない）"""
        out = tmp_path / "out.html"
        parsed = _make_parsed_session()
        HtmlReporter().generate(_make_session_report("data-check-session"), parsed, {}, out)
        content = out.read_text()
        # SESSION_DATA に session_id は含まれる（SessionReport の一部）
        assert "data-check-session" in content
        # parsed のエントリデータ（テキストコンテンツ）は SESSION_DATA には含まれない
        # ログ詳細タブのコンテンツとして表示されるが、SESSION_DATA の JSON には含まれない
        session_data_start = content.find("SESSION_DATA")
        session_data_end = content.find(";", session_data_start)
        session_data_json = content[session_data_start:session_data_end]
        assert "main_entries" not in session_data_json


class TestHtmlReporterLogDetailStyle:
    """タスク 3.3: ログ詳細タブの CSS/JS 統合テスト"""

    def _get_style_section(self, html: str) -> str:
        """<style> タグの内容を抽出する"""
        start = html.find("<style>") + len("<style>")
        end = html.find("</style>")
        return html[start:end]

    def test_log_entry_hidden_css_defined(self, tmp_path: Path) -> None:
        """log-entry-hidden クラスに display:none の CSS が定義されている"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        css = self._get_style_section(out.read_text())
        assert "log-entry-hidden" in css

    def test_agent_launch_css_defined(self, tmp_path: Path) -> None:
        """agent-launch クラスにハイライト CSS が定義されている"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        css = self._get_style_section(out.read_text())
        assert "agent-launch" in css

    def test_log_entries_container_scroll_css_defined(self, tmp_path: Path) -> None:
        """log-entries-container クラスにスクロール CSS が定義されている（要件 3.2）"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        css = self._get_style_section(out.read_text())
        assert "log-entries-container" in css

    def test_show_all_log_entries_js_defined(self, tmp_path: Path) -> None:
        """showAllLogEntries JS 関数がレポートに含まれる（要件 4.5）"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_session_report(), out)
        assert "showAllLogEntries" in out.read_text()
