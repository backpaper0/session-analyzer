"""タスク5.1: HTMLテンプレートとデザイン基盤テスト"""
from pathlib import Path

import pytest

from session_analyzer.models import (
    BashInvocation,
    CommandAggregation,
    SessionReport,
    SkillReport,
    SubAgentReport,
    ThinkingReport,
    TokenReport,
    TokenUsageStats,
    ToolReport,
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
