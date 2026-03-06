"""タスク4.2: スキル使用サマリーの解析テスト"""
import pytest
from session_analyzer.analyzers.skill import SkillAnalyzer
from session_analyzer.models import (
    ParsedSession, UserEntry, AssistantEntry, UsageData,
    SkillReport, SkillInvocation, InvocationMethod,
)


def _make_session(main_entries=None) -> ParsedSession:
    return ParsedSession(
        session_id="test",
        main_entries=main_entries or [],
        subagent_entries={},
    )


def _make_user(content: str, uuid: str = "u1",
               is_meta: bool = False,
               timestamp: str = "2024-01-01T00:00:00Z") -> UserEntry:
    return UserEntry(
        uuid=uuid,
        parent_uuid=None,
        timestamp=timestamp,
        is_meta=is_meta,
        content=content,
        agent_id=None,
    )


def _make_assistant() -> AssistantEntry:
    return AssistantEntry(
        uuid="a1", parent_uuid=None, timestamp="2024-01-01T00:00:00Z",
        model="claude-sonnet-4-6", content=[],
        usage=UsageData(), agent_id=None,
    )


# --- 戻り値の型 ---

def test_analyze_returns_skill_report():
    """analyze()がSkillReportを返すこと"""
    result = SkillAnalyzer().analyze(_make_session())
    assert isinstance(result, SkillReport)


def test_analyze_empty_session():
    """エントリがない場合はinvocationsが空、summaryが空であること"""
    result = SkillAnalyzer().analyze(_make_session())
    assert result.invocations == []
    assert result.summary == {}


# --- command-name タグ抽出 ---

def test_analyze_extracts_skill_from_command_name_tag():
    """<command-name>タグからスキル名を抽出できること"""
    entry = _make_user("<command-name>/kiro:spec-impl</command-name>")
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert len(result.invocations) == 1
    assert result.invocations[0].skill_name == "kiro:spec-impl"


def test_analyze_strips_leading_slash():
    """スキル名の先頭スラッシュが除去されること"""
    entry = _make_user("<command-name>/my-skill</command-name>")
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert result.invocations[0].skill_name == "my-skill"


def test_analyze_skill_without_slash():
    """スラッシュなしのスキル名も正しく抽出されること"""
    entry = _make_user("<command-name>my-skill</command-name>")
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert result.invocations[0].skill_name == "my-skill"


def test_analyze_no_command_name_tag_ignored():
    """<command-name>タグがないuserエントリは無視されること"""
    entry = _make_user("just a regular message")
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert result.invocations == []


def test_analyze_assistant_entries_ignored():
    """assistantエントリはスキル解析に含まれないこと"""
    result = SkillAnalyzer().analyze(_make_session([_make_assistant()]))
    assert result.invocations == []


# --- 起動方法の分類 ---

def test_analyze_user_slash_command_when_not_meta():
    """isMeta=falseの場合はUSER_SLASH_COMMANDに分類されること"""
    entry = _make_user("<command-name>/kiro:spec-impl</command-name>", is_meta=False)
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert result.invocations[0].method == InvocationMethod.USER_SLASH_COMMAND


def test_analyze_llm_auto_when_meta():
    """isMeta=trueの場合はLLM_AUTOに分類されること"""
    entry = _make_user("<command-name>/kiro:spec-impl</command-name>", is_meta=True)
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert result.invocations[0].method == InvocationMethod.LLM_AUTO


# --- タイムスタンプ・UUID ---

def test_analyze_invocation_has_timestamp():
    """SkillInvocationにタイムスタンプが設定されること"""
    entry = _make_user("<command-name>/skill</command-name>",
                       timestamp="2024-06-15T12:30:00Z")
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert result.invocations[0].timestamp == "2024-06-15T12:30:00Z"


def test_analyze_invocation_has_uuid():
    """SkillInvocationにUUIDが設定されること"""
    entry = _make_user("<command-name>/skill</command-name>", uuid="my-uuid-123")
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert result.invocations[0].uuid == "my-uuid-123"


# --- 時系列順 ---

def test_analyze_invocations_in_chronological_order():
    """invocationsが時系列順に並ぶこと"""
    entries = [
        _make_user("<command-name>/skill-a</command-name>",
                   uuid="u1", timestamp="2024-01-01T00:00:00Z"),
        _make_user("<command-name>/skill-b</command-name>",
                   uuid="u2", timestamp="2024-01-01T01:00:00Z"),
        _make_user("<command-name>/skill-c</command-name>",
                   uuid="u3", timestamp="2024-01-01T02:00:00Z"),
    ]
    result = SkillAnalyzer().analyze(_make_session(entries))

    names = [i.skill_name for i in result.invocations]
    assert names == ["skill-a", "skill-b", "skill-c"]


# --- サマリー集計 ---

def test_analyze_summary_counts():
    """スキル名別の呼び出し回数が正しく集計されること"""
    entries = [
        _make_user("<command-name>/skill-a</command-name>", uuid="u1"),
        _make_user("<command-name>/skill-a</command-name>", uuid="u2"),
        _make_user("<command-name>/skill-b</command-name>", uuid="u3"),
    ]
    result = SkillAnalyzer().analyze(_make_session(entries))

    assert result.summary["skill-a"] == 2
    assert result.summary["skill-b"] == 1


def test_analyze_content_with_extra_text():
    """<command-name>タグ以外のテキストが含まれても正しく抽出されること"""
    content = (
        "<command-message>kiro:spec-impl</command-message>\n"
        "<command-name>/kiro:spec-impl</command-name>\n"
        "<command-args>session-analyzer 4.2</command-args>"
    )
    entry = _make_user(content)
    result = SkillAnalyzer().analyze(_make_session([entry]))

    assert len(result.invocations) == 1
    assert result.invocations[0].skill_name == "kiro:spec-impl"
