"""タスク1.2: ドメインモデルのテスト"""
import pytest
from dataclasses import fields


# --- ログエントリデータクラス ---

def test_usage_data_defaults():
    from session_analyzer.models import UsageData
    u = UsageData()
    assert u.input_tokens == 0
    assert u.output_tokens == 0
    assert u.cache_creation_input_tokens == 0
    assert u.cache_read_input_tokens == 0


def test_usage_data_with_values():
    from session_analyzer.models import UsageData
    u = UsageData(input_tokens=100, output_tokens=50)
    assert u.input_tokens == 100
    assert u.output_tokens == 50


def test_text_block_type_literal():
    from session_analyzer.models import TextBlock
    b = TextBlock(type="text", text="hello")
    assert b.type == "text"
    assert b.text == "hello"


def test_tool_use_block():
    from session_analyzer.models import ToolUseBlock
    b = ToolUseBlock(type="tool_use", id="tid", name="Bash", input={"command": "ls"})
    assert b.type == "tool_use"
    assert b.id == "tid"
    assert b.name == "Bash"
    assert b.input == {"command": "ls"}


def test_thinking_block():
    from session_analyzer.models import ThinkingBlock
    b = ThinkingBlock(type="thinking", thinking="I think...", signature="sig123")
    assert b.type == "thinking"
    assert b.thinking == "I think..."
    assert b.signature == "sig123"


def test_tool_result_block():
    from session_analyzer.models import ToolResultBlock
    b = ToolResultBlock(type="tool_result", tool_use_id="tid", content="output", is_error=False)
    assert b.type == "tool_result"
    assert b.tool_use_id == "tid"
    assert b.is_error is False


def test_assistant_entry():
    from session_analyzer.models import AssistantEntry, UsageData
    entry = AssistantEntry(
        uuid="uuid1",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        model="claude-sonnet-4-6",
        content=[],
        usage=UsageData(),
        agent_id=None,
    )
    assert entry.uuid == "uuid1"
    assert entry.model == "claude-sonnet-4-6"
    assert entry.agent_id is None


def test_user_entry():
    from session_analyzer.models import UserEntry
    entry = UserEntry(
        uuid="uuid2",
        parent_uuid="uuid1",
        timestamp="2024-01-01T00:00:00Z",
        is_meta=False,
        content="hello",
        agent_id=None,
    )
    assert entry.is_meta is False
    assert entry.content == "hello"


# --- セッション集約モデル ---

def test_session_files():
    from session_analyzer.models import SessionFiles
    from pathlib import Path
    sf = SessionFiles(main=Path("/tmp/main.jsonl"), subagents=[])
    assert sf.main == Path("/tmp/main.jsonl")
    assert sf.subagents == []


def test_session_files_is_frozen():
    from session_analyzer.models import SessionFiles
    from pathlib import Path
    sf = SessionFiles(main=Path("/tmp/main.jsonl"), subagents=[])
    with pytest.raises((AttributeError, TypeError)):
        sf.main = Path("/tmp/other.jsonl")  # type: ignore


def test_parsed_session():
    from session_analyzer.models import ParsedSession
    ps = ParsedSession(session_id="abc123", main_entries=[], subagent_entries={})
    assert ps.session_id == "abc123"
    assert ps.main_entries == []
    assert ps.subagent_entries == {}


# --- アナライザー出力型 ---

def test_token_usage_stats():
    from session_analyzer.models import TokenUsageStats
    stats = TokenUsageStats(
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=10,
        cache_read_tokens=5,
        estimated_cost_usd=0.001,
    )
    assert stats.model == "claude-sonnet-4-6"
    assert stats.estimated_cost_usd == 0.001


def test_token_usage_stats_unknown_model():
    from session_analyzer.models import TokenUsageStats
    stats = TokenUsageStats(
        model="claude-unknown",
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        estimated_cost_usd=None,
    )
    assert stats.estimated_cost_usd is None


def test_token_report():
    from session_analyzer.models import TokenReport, TokenUsageStats
    total = TokenUsageStats("total", 100, 50, 0, 0, None)
    report = TokenReport(by_model=[], total=total)
    assert report.total is total


def test_invocation_method_values():
    from session_analyzer.models import InvocationMethod
    assert InvocationMethod.USER_SLASH_COMMAND == "ユーザー起動（スラッシュコマンド）"
    assert InvocationMethod.LLM_AUTO == "LLM自動起動"


def test_skill_invocation():
    from session_analyzer.models import SkillInvocation, InvocationMethod
    inv = SkillInvocation(
        skill_name="kiro:spec-impl",
        method=InvocationMethod.USER_SLASH_COMMAND,
        timestamp="2024-01-01T00:00:00Z",
        uuid="uuid1",
    )
    assert inv.skill_name == "kiro:spec-impl"


def test_skill_report():
    from session_analyzer.models import SkillReport
    report = SkillReport(invocations=[], summary={})
    assert report.invocations == []
    assert report.summary == {}


def test_bash_invocation():
    from session_analyzer.models import BashInvocation
    inv = BashInvocation(
        command="ls -la",
        is_error=False,
        error_message=None,
        timestamp="2024-01-01T00:00:00Z",
        source="main",
        entry_uuid="uuid-123",
    )
    assert inv.command == "ls -la"
    assert inv.is_error is False
    assert inv.entry_uuid == "uuid-123"


def test_command_aggregation():
    from session_analyzer.models import CommandAggregation
    agg = CommandAggregation(base_command="git", count=5, sub_commands={"commit": 3, "push": 2})
    assert agg.count == 5


def test_tool_report():
    from session_analyzer.models import ToolReport
    report = ToolReport(tool_counts={}, bash_invocations=[], bash_aggregation=[])
    assert report.tool_counts == {}


def test_sub_agent_info():
    from session_analyzer.models import SubAgentInfo
    info = SubAgentInfo(
        agent_id="agent-abc",
        tool_name="Task",
        subagent_type="Explore",
        prompt="do something",
        launched_at="2024-01-01T00:00:00Z",
        token_usage=None,
    )
    assert info.agent_id == "agent-abc"
    assert info.token_usage is None


def test_sub_agent_report():
    from session_analyzer.models import SubAgentReport
    report = SubAgentReport(agents=[])
    assert report.agents == []


def test_thinking_entry():
    from session_analyzer.models import ThinkingEntry
    entry = ThinkingEntry(
        content="deep thought",
        message_uuid="uuid1",
        timestamp="2024-01-01T00:00:00Z",
        source="main",
    )
    assert entry.content == "deep thought"


def test_thinking_report_with_entries():
    from session_analyzer.models import ThinkingReport, ThinkingEntry
    e = ThinkingEntry("thought", "u1", "2024-01-01", "main")
    report = ThinkingReport(entries=[e], has_thinking=True)
    assert report.has_thinking is True


def test_thinking_report_empty():
    from session_analyzer.models import ThinkingReport
    report = ThinkingReport(entries=[], has_thinking=False)
    assert report.has_thinking is False


def test_session_report():
    from session_analyzer.models import (
        SessionReport, TokenReport, TokenUsageStats,
        SkillReport, ToolReport, SubAgentReport, ThinkingReport,
    )
    total = TokenUsageStats("total", 0, 0, 0, 0, None)
    report = SessionReport(
        session_id="abc",
        token=TokenReport(by_model=[], total=total),
        skills=SkillReport(invocations=[], summary={}),
        tools=ToolReport(tool_counts={}, bash_invocations=[], bash_aggregation=[]),
        sub_agents=SubAgentReport(agents=[]),
        thinking=ThinkingReport(entries=[], has_thinking=False),
    )
    assert report.session_id == "abc"


# --- カスタム例外 ---

def test_session_not_found_error():
    from session_analyzer.exceptions import SessionNotFoundError
    with pytest.raises(SessionNotFoundError):
        raise SessionNotFoundError("abc123")


def test_session_not_found_error_message():
    from session_analyzer.exceptions import SessionNotFoundError
    err = SessionNotFoundError("abc123")
    assert "abc123" in str(err)


def test_ambiguous_session_error():
    from session_analyzer.exceptions import AmbiguousSessionError
    with pytest.raises(AmbiguousSessionError):
        raise AmbiguousSessionError("abc", ["file1.jsonl", "file2.jsonl"])


def test_ambiguous_session_error_message():
    from session_analyzer.exceptions import AmbiguousSessionError
    err = AmbiguousSessionError("abc", ["file1.jsonl", "file2.jsonl"])
    assert "abc" in str(err)
    assert "file1.jsonl" in str(err)


def test_report_generation_error():
    from session_analyzer.exceptions import ReportGenerationError
    with pytest.raises(ReportGenerationError):
        raise ReportGenerationError("write failed")
