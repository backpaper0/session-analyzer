"""タスク5.2: 各セクションのデータ描画テスト"""
import json
from pathlib import Path

import pytest

from session_analyzer.models import (
    BashInvocation,
    CommandAggregation,
    InvocationMethod,
    SessionReport,
    SkillInvocation,
    SkillReport,
    SubAgentInfo,
    SubAgentReport,
    ThinkingEntry,
    ThinkingReport,
    TokenReport,
    TokenUsageStats,
    ToolReport,
)
from session_analyzer.reporter import HtmlReporter


def _make_report() -> SessionReport:
    total = TokenUsageStats(
        model="total",
        input_tokens=1500,
        output_tokens=800,
        cache_creation_tokens=200,
        cache_read_tokens=100,
        estimated_cost_usd=0.0123,
    )
    token_report = TokenReport(
        by_model=[
            TokenUsageStats(
                model="claude-sonnet-4-6",
                input_tokens=1000,
                output_tokens=500,
                cache_creation_tokens=100,
                cache_read_tokens=50,
                estimated_cost_usd=0.0100,
            ),
            TokenUsageStats(
                model="claude-haiku-4-5-20251001",
                input_tokens=500,
                output_tokens=300,
                cache_creation_tokens=100,
                cache_read_tokens=50,
                estimated_cost_usd=0.0023,
            ),
        ],
        total=total,
    )
    skills = SkillReport(
        invocations=[
            SkillInvocation(
                skill_name="kiro:spec-impl",
                method=InvocationMethod.USER_SLASH_COMMAND,
                timestamp="2026-03-06T00:00:00Z",
                uuid="uuid-skill-1",
            ),
            SkillInvocation(
                skill_name="kiro:validate-design",
                method=InvocationMethod.LLM_AUTO,
                timestamp="2026-03-06T00:01:00Z",
                uuid="uuid-skill-2",
            ),
        ],
        summary={"kiro:spec-impl": 1, "kiro:validate-design": 1},
    )
    tools = ToolReport(
        tool_counts={"Bash": 3, "Read": 5, "Edit": 2},
        bash_invocations=[
            BashInvocation(
                command="git status",
                is_error=False,
                error_message=None,
                timestamp="2026-03-06T00:00:00Z",
                source="main",
            ),
            BashInvocation(
                command="npm run fail",
                is_error=True,
                error_message="Command failed: npm run fail",
                timestamp="2026-03-06T00:01:00Z",
                source="main",
            ),
        ],
        bash_aggregation=[
            CommandAggregation(base_command="git", count=1, sub_commands={"status": 1}),
            CommandAggregation(base_command="npm", count=1, sub_commands={"run": 1}),
        ],
    )
    sub_agents = SubAgentReport(
        agents=[
            SubAgentInfo(
                agent_id="agent-abc12345",
                tool_name="Task",
                subagent_type="Explore",
                prompt="Explore the codebase for session files",
                launched_at="2026-03-06T00:00:00Z",
                token_usage=TokenUsageStats(
                    model="claude-sonnet-4-6",
                    input_tokens=300,
                    output_tokens=150,
                    cache_creation_tokens=0,
                    cache_read_tokens=0,
                    estimated_cost_usd=0.0030,
                ),
            )
        ]
    )
    thinking = ThinkingReport(
        entries=[
            ThinkingEntry(
                content="I need to think about this carefully...",
                message_uuid="msg-uuid-1",
                timestamp="2026-03-06T00:00:00Z",
                source="main",
            )
        ],
        has_thinking=True,
    )
    return SessionReport(
        session_id="test-session-5-2",
        token=token_report,
        skills=skills,
        tools=tools,
        sub_agents=sub_agents,
        thinking=thinking,
    )


# -----------------------------------------------------------------------
# JSON埋め込みテスト
# -----------------------------------------------------------------------

class TestJsonEmbedding:
    def test_session_data_is_embedded_as_json(self, tmp_path: Path) -> None:
        """SESSION_DATA という JS 変数にJSONが埋め込まれている"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "SESSION_DATA" in content

    def test_embedded_json_contains_session_id(self, tmp_path: Path) -> None:
        """埋め込みJSONにセッションIDが含まれる"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "test-session-5-2" in content

    def test_embedded_json_is_parseable(self, tmp_path: Path) -> None:
        """埋め込まれたJSONが有効なJSON文字列である"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        # <script>const SESSION_DATA = {...};</script> から JSON 部分を抽出
        marker = "const SESSION_DATA = "
        start = content.find(marker)
        assert start != -1, "SESSION_DATA が見つからない"
        json_start = start + len(marker)
        # 最後の "};" を探す（最後の '}' + ';' の前に終わる）
        json_end = content.find(";\n", json_start)
        if json_end == -1:
            json_end = content.find(";", json_start)
        json_str = content[json_start:json_end]
        parsed = json.loads(json_str)
        assert parsed["session_id"] == "test-session-5-2"


# -----------------------------------------------------------------------
# トークンセクション
# -----------------------------------------------------------------------

class TestTokenSection:
    def test_model_name_appears(self, tmp_path: Path) -> None:
        """モデル名がトークンセクションに表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "claude-sonnet-4-6" in content
        assert "claude-haiku-4-5-20251001" in content

    def test_cost_appears(self, tmp_path: Path) -> None:
        """コスト値がトークンセクションに表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "$0.01" in content  # 0.0100 か 0.0123 のどちらか

    def test_total_row_appears(self, tmp_path: Path) -> None:
        """合計行が表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "合計" in content

    def test_na_for_unknown_model(self, tmp_path: Path) -> None:
        """未知モデルのコストはN/Aと表示される"""
        from session_analyzer.models import TokenReport, TokenUsageStats, SessionReport
        report = _make_report()
        report.token.by_model.append(
            TokenUsageStats(
                model="unknown-model-x",
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                estimated_cost_usd=None,
            )
        )
        out = tmp_path / "out.html"
        HtmlReporter().generate(report, out)
        content = out.read_text()
        assert "N/A" in content


# -----------------------------------------------------------------------
# スキルセクション
# -----------------------------------------------------------------------

class TestSkillsSection:
    def test_skill_name_appears(self, tmp_path: Path) -> None:
        """スキル名がスキルセクションに表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "kiro:spec-impl" in content
        assert "kiro:validate-design" in content

    def test_invocation_method_appears(self, tmp_path: Path) -> None:
        """起動方法（LLM自動起動 / ユーザー起動）が表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "LLM自動起動" in content
        assert "ユーザー起動" in content

    def test_timestamp_appears(self, tmp_path: Path) -> None:
        """タイムスタンプが表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "2026-03-06" in content


# -----------------------------------------------------------------------
# ツールセクション
# -----------------------------------------------------------------------

class TestToolsSection:
    def test_tool_counts_appear(self, tmp_path: Path) -> None:
        """ツール使用カウントが表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "Bash" in content
        assert "Read" in content
        assert "Edit" in content

    def test_bash_command_appears(self, tmp_path: Path) -> None:
        """Bash コマンドが表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "git status" in content
        assert "npm run fail" in content

    def test_success_color_class(self, tmp_path: Path) -> None:
        """成功した Bash コマンドに success クラスが付く"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "bash-row success" in content

    def test_failure_color_class(self, tmp_path: Path) -> None:
        """失敗した Bash コマンドに failure クラスが付く"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "bash-row failure" in content

    def test_subcommand_aggregation_appears(self, tmp_path: Path) -> None:
        """サブコマンド集計が表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "status" in content  # git status の sub_commands


# -----------------------------------------------------------------------
# サブエージェントセクション
# -----------------------------------------------------------------------

class TestSubAgentsSection:
    def test_agent_id_appears(self, tmp_path: Path) -> None:
        """エージェント ID が表示される（短縮形でも可）"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "agent-abc12345"[:12] in content

    def test_prompt_appears(self, tmp_path: Path) -> None:
        """プロンプトが表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "Explore the codebase" in content

    def test_subagent_type_appears(self, tmp_path: Path) -> None:
        """サブエージェントタイプが表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "Explore" in content

    def test_token_usage_appears(self, tmp_path: Path) -> None:
        """サブエージェントのトークン使用量が表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "300" in content  # input_tokens=300


# -----------------------------------------------------------------------
# 思考ログセクション
# -----------------------------------------------------------------------

class TestThinkingSection:
    def test_details_summary_used(self, tmp_path: Path) -> None:
        """<details>/<summary> 要素が使われている"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "<details>" in content
        assert "<summary>" in content

    def test_thinking_content_appears(self, tmp_path: Path) -> None:
        """thinking コンテンツが表示される"""
        out = tmp_path / "out.html"
        HtmlReporter().generate(_make_report(), out)
        content = out.read_text()
        assert "I need to think about this carefully" in content

    def test_no_thinking_shows_empty_message(self, tmp_path: Path) -> None:
        """thinking なしの場合は空メッセージが表示される"""
        from session_analyzer.models import ThinkingReport
        report = _make_report()
        report.thinking = ThinkingReport(entries=[], has_thinking=False)
        out = tmp_path / "out.html"
        HtmlReporter().generate(report, out)
        content = out.read_text()
        assert "thinking ブロックなし" in content
