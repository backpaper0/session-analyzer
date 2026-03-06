"""タスク4.5: 思考ログの抽出と整理テスト"""

from session_analyzer.analyzers.thinking import ThinkingAnalyzer
from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    TextBlock,
    ThinkingBlock,
    ThinkingReport,
    UsageData,
    UserEntry,
)


def _make_session(main_entries=None, subagent_entries=None) -> ParsedSession:
    return ParsedSession(
        session_id="test",
        main_entries=main_entries or [],
        subagent_entries=subagent_entries or {},
    )


def _make_assistant(
    uuid: str,
    thinking: str | None = None,
    timestamp: str = "2024-01-01T00:00:00Z",
    agent_id: str | None = None,
) -> AssistantEntry:
    content = []
    if thinking is not None:
        content.append(
            ThinkingBlock(type="thinking", thinking=thinking, signature="sig")
        )
    content.append(TextBlock(type="text", text="response"))
    return AssistantEntry(
        uuid=uuid,
        parent_uuid=None,
        timestamp=timestamp,
        model="claude-sonnet-4-6",
        content=content,
        usage=UsageData(),
        agent_id=agent_id,
    )


# --- 戻り値の型 ---


def test_analyze_returns_thinking_report():
    result = ThinkingAnalyzer().analyze(_make_session())
    assert isinstance(result, ThinkingReport)


def test_analyze_empty_session_has_no_thinking():
    result = ThinkingAnalyzer().analyze(_make_session())
    assert result.has_thinking is False
    assert result.entries == []


# --- thinkingブロックの抽出 ---


def test_analyze_extracts_thinking_block():
    """thinkingブロックを含むassistantエントリからThinkingEntryが生成されること"""
    entries = [_make_assistant("uuid1", thinking="I am thinking...")]
    result = ThinkingAnalyzer().analyze(_make_session(entries))

    assert len(result.entries) == 1
    assert result.entries[0].content == "I am thinking..."


def test_analyze_has_thinking_true_when_thinking_exists():
    """thinkingブロックが存在する場合はhas_thinking=Trueであること"""
    entries = [_make_assistant("uuid1", thinking="thinking")]
    result = ThinkingAnalyzer().analyze(_make_session(entries))

    assert result.has_thinking is True


def test_analyze_no_thinking_blocks_in_entry():
    """thinkingブロックを含まないassistantエントリは無視されること"""
    entry = AssistantEntry(
        uuid="u1",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        model="claude-sonnet-4-6",
        content=[TextBlock(type="text", text="just text")],
        usage=UsageData(),
        agent_id=None,
    )
    result = ThinkingAnalyzer().analyze(_make_session([entry]))

    assert result.has_thinking is False
    assert result.entries == []


def test_analyze_user_entries_ignored():
    """userエントリはThinkingEntry作成に含まれないこと"""
    user = UserEntry(
        uuid="u1",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        is_meta=False,
        content="hi",
        agent_id=None,
    )
    result = ThinkingAnalyzer().analyze(_make_session([user]))
    assert result.entries == []


# --- フィールドの抽出 ---


def test_analyze_extracts_message_uuid():
    """message_uuidにassistantエントリのuuidが設定されること"""
    entries = [_make_assistant("my-uuid-123", thinking="thought")]
    result = ThinkingAnalyzer().analyze(_make_session(entries))

    assert result.entries[0].message_uuid == "my-uuid-123"


def test_analyze_extracts_timestamp():
    """timestampにassistantエントリのtimestampが設定されること"""
    entries = [
        _make_assistant("u1", thinking="thought", timestamp="2024-06-15T12:30:00Z")
    ]
    result = ThinkingAnalyzer().analyze(_make_session(entries))

    assert result.entries[0].timestamp == "2024-06-15T12:30:00Z"


def test_analyze_source_is_main_for_main_entries():
    """メインエントリのsourceは'main'であること"""
    entries = [_make_assistant("u1", thinking="thought")]
    result = ThinkingAnalyzer().analyze(_make_session(entries))

    assert result.entries[0].source == "main"


def test_analyze_source_is_agent_id_for_subagent():
    """サブエージェントエントリのsourceはagent_idであること"""
    sub_entry = _make_assistant("u1", thinking="sub thought", agent_id="agent-abc")
    result = ThinkingAnalyzer().analyze(
        _make_session(subagent_entries={"agent-abc": [sub_entry]})
    )

    assert result.entries[0].source == "agent-abc"


# --- 複数thinkingブロックの処理 ---


def test_analyze_multiple_thinking_blocks_in_one_entry():
    """1つのassistantエントリに複数のthinkingブロックがある場合、全て抽出されること"""
    entry = AssistantEntry(
        uuid="u1",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        model="claude-sonnet-4-6",
        content=[
            ThinkingBlock(type="thinking", thinking="first thought", signature="s1"),
            ThinkingBlock(type="thinking", thinking="second thought", signature="s2"),
        ],
        usage=UsageData(),
        agent_id=None,
    )
    result = ThinkingAnalyzer().analyze(_make_session([entry]))

    assert len(result.entries) == 2
    assert result.entries[0].content == "first thought"
    assert result.entries[1].content == "second thought"


# --- 時系列順 ---


def test_analyze_sorted_chronologically():
    """複数のthinkingエントリが時系列順（timestamp昇順）に並ぶこと"""
    entries = [
        _make_assistant("u1", thinking="first", timestamp="2024-01-01T00:00:00Z"),
        _make_assistant("u2", thinking="second", timestamp="2024-01-01T01:00:00Z"),
    ]
    result = ThinkingAnalyzer().analyze(_make_session(entries))

    assert result.entries[0].content == "first"
    assert result.entries[1].content == "second"


# --- サブエージェントのthinkingも含まれること ---


def test_analyze_includes_subagent_thinking():
    """サブエージェントのthinkingブロックも含まれること"""
    main_entry = _make_assistant("m1", thinking="main thought")
    sub_entry = _make_assistant("s1", thinking="sub thought", agent_id="agent-xyz")

    result = ThinkingAnalyzer().analyze(
        _make_session([main_entry], {"agent-xyz": [sub_entry]})
    )

    contents = {e.content for e in result.entries}
    assert "main thought" in contents
    assert "sub thought" in contents


def test_analyze_no_thinking_in_session_message():
    """thinkingブロックが0件の場合はhas_thinking=Falseで空リストが返ること"""
    entry = _make_assistant("u1", thinking=None)  # thinkingなし
    result = ThinkingAnalyzer().analyze(_make_session([entry]))

    assert result.has_thinking is False
    assert result.entries == []
