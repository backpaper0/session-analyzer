"""タスク4.4: サブエージェント情報の集計テスト"""

from session_analyzer.analyzers.subagent import SubAgentAnalyzer
from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    SubAgentReport,
    ToolUseBlock,
    UsageData,
    UserEntry,
)


def _make_session(main_entries=None, subagent_entries=None) -> ParsedSession:
    return ParsedSession(
        session_id="test",
        main_entries=main_entries or [],
        subagent_entries=subagent_entries or {},
    )


def _make_assistant_with_task(
    tool_id: str,
    tool_name: str = "Task",
    subagent_type: str | None = "Explore",
    prompt: str = "do something",
    description: str = "My task",
    timestamp: str = "2024-01-01T00:00:00Z",
) -> AssistantEntry:
    task_input: dict = {"prompt": prompt}
    if subagent_type:
        task_input["subagent_type"] = subagent_type
    if description:
        task_input["description"] = description
    return AssistantEntry(
        uuid="a1",
        parent_uuid=None,
        timestamp=timestamp,
        model="claude-sonnet-4-6",
        content=[
            ToolUseBlock(type="tool_use", id=tool_id, name=tool_name, input=task_input)
        ],
        usage=UsageData(),
        agent_id=None,
    )


def _make_sub_assistant(
    model: str, input_tokens: int, output_tokens: int, agent_id: str
) -> AssistantEntry:
    return AssistantEntry(
        uuid="sa1",
        parent_uuid=None,
        timestamp="2024-01-01T00:01:00Z",
        model=model,
        content=[],
        usage=UsageData(input_tokens=input_tokens, output_tokens=output_tokens),
        agent_id=agent_id,
    )


# --- 戻り値の型 ---


def test_analyze_returns_sub_agent_report():
    result = SubAgentAnalyzer().analyze(_make_session())
    assert isinstance(result, SubAgentReport)


def test_analyze_empty_session():
    result = SubAgentAnalyzer().analyze(_make_session())
    assert result.agents == []


# --- Task/Agent tool_use の検出 ---


def test_analyze_detects_task_tool_use():
    """Taskツール呼び出しがSubAgentInfoとして記録されること"""
    entries = [_make_assistant_with_task("t1", "Task")]
    result = SubAgentAnalyzer().analyze(_make_session(entries))

    assert len(result.agents) == 1
    assert result.agents[0].tool_name == "Task"


def test_analyze_detects_agent_tool_use():
    """Agentツール呼び出しもSubAgentInfoとして記録されること"""
    entries = [_make_assistant_with_task("t1", "Agent")]
    result = SubAgentAnalyzer().analyze(_make_session(entries))

    assert len(result.agents) == 1
    assert result.agents[0].tool_name == "Agent"


def test_analyze_non_task_tools_ignored():
    """Task/Agent以外のtool_useは無視されること"""
    entry = AssistantEntry(
        uuid="a1",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        model="claude-sonnet-4-6",
        content=[ToolUseBlock(type="tool_use", id="t1", name="Read", input={})],
        usage=UsageData(),
        agent_id=None,
    )
    result = SubAgentAnalyzer().analyze(_make_session([entry]))
    assert result.agents == []


def test_analyze_user_entries_ignored():
    """userエントリはSubAgentInfo作成に含まれないこと"""
    user = UserEntry(
        uuid="u1",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        is_meta=False,
        content="hi",
        agent_id=None,
    )
    result = SubAgentAnalyzer().analyze(_make_session([user]))
    assert result.agents == []


# --- フィールドの抽出 ---


def test_analyze_extracts_subagent_type():
    """subagent_typeが正しく抽出されること"""
    entries = [_make_assistant_with_task("t1", subagent_type="Explore")]
    result = SubAgentAnalyzer().analyze(_make_session(entries))

    assert result.agents[0].subagent_type == "Explore"


def test_analyze_subagent_type_none_when_missing():
    """subagent_typeがない場合はNoneになること"""
    entry = AssistantEntry(
        uuid="a1",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        model="claude-sonnet-4-6",
        content=[
            ToolUseBlock(
                type="tool_use", id="t1", name="Task", input={"prompt": "do something"}
            )
        ],
        usage=UsageData(),
        agent_id=None,
    )
    result = SubAgentAnalyzer().analyze(_make_session([entry]))
    assert result.agents[0].subagent_type is None


def test_analyze_extracts_prompt():
    """promptフィールドが正しく抽出されること"""
    entries = [_make_assistant_with_task("t1", prompt="Explore the codebase")]
    result = SubAgentAnalyzer().analyze(_make_session(entries))

    assert result.agents[0].prompt == "Explore the codebase"


def test_analyze_extracts_description_when_no_prompt():
    """promptがない場合はdescriptionがpromptとして使われること"""
    entry = AssistantEntry(
        uuid="a1",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        model="claude-sonnet-4-6",
        content=[
            ToolUseBlock(
                type="tool_use",
                id="t1",
                name="Task",
                input={"description": "Explore codebase"},
            )
        ],
        usage=UsageData(),
        agent_id=None,
    )
    result = SubAgentAnalyzer().analyze(_make_session([entry]))
    assert result.agents[0].prompt == "Explore codebase"


def test_analyze_extracts_launched_at():
    """launched_atにassistantエントリのタイムスタンプが設定されること"""
    entries = [_make_assistant_with_task("t1", timestamp="2024-06-01T10:00:00Z")]
    result = SubAgentAnalyzer().analyze(_make_session(entries))

    assert result.agents[0].launched_at == "2024-06-01T10:00:00Z"


def test_analyze_agent_id_is_tool_use_id():
    """agent_idにtool_use.idが設定されること"""
    entries = [_make_assistant_with_task("toolu_abc123")]
    result = SubAgentAnalyzer().analyze(_make_session(entries))

    assert result.agents[0].agent_id == "toolu_abc123"


# --- 時系列順 ---


def test_analyze_sorted_by_launch_time():
    """複数エージェントが起動順に並ぶこと"""
    entries = [
        _make_assistant_with_task(
            "t1", prompt="first", timestamp="2024-01-01T00:00:00Z"
        ),
        _make_assistant_with_task(
            "t2", prompt="second", timestamp="2024-01-01T01:00:00Z"
        ),
    ]
    result = SubAgentAnalyzer().analyze(_make_session(entries))

    assert result.agents[0].prompt == "first"
    assert result.agents[1].prompt == "second"


# --- token_usage の紐づけ ---


def test_analyze_token_usage_none_when_no_subagent_entries():
    """対応するサブエージェントログがない場合はtoken_usage=Noneであること"""
    entries = [_make_assistant_with_task("t1")]
    result = SubAgentAnalyzer().analyze(_make_session(entries))

    assert result.agents[0].token_usage is None


def test_analyze_token_usage_computed_from_subagent_entries():
    """サブエージェントエントリが存在する場合はtoken_usageが計算されること"""
    main_entries = [_make_assistant_with_task("t1")]
    sub_entries = [_make_sub_assistant("claude-sonnet-4-6", 200, 80, "sub1")]

    session = _make_session(main_entries, {"sub1": sub_entries})
    result = SubAgentAnalyzer().analyze(session)

    assert result.agents[0].token_usage is not None
    assert result.agents[0].token_usage.input_tokens == 200
    assert result.agents[0].token_usage.output_tokens == 80


def test_analyze_multiple_subagents_token_usage():
    """複数サブエージェントのtoken_usageが正しく紐づけられること"""
    main_entries = [
        _make_assistant_with_task(
            "t1", prompt="first", timestamp="2024-01-01T00:00:00Z"
        ),
        _make_assistant_with_task(
            "t2", prompt="second", timestamp="2024-01-01T01:00:00Z"
        ),
    ]
    sub1_entries = [_make_sub_assistant("claude-sonnet-4-6", 100, 40, "sub1")]
    sub2_entries = [_make_sub_assistant("claude-opus-4-6", 300, 120, "sub2")]

    session = _make_session(main_entries, {"sub1": sub1_entries, "sub2": sub2_entries})
    result = SubAgentAnalyzer().analyze(session)

    # 両エージェントのtoken_usageが計算されていること
    token_inputs = {a.token_usage.input_tokens for a in result.agents if a.token_usage}
    assert 100 in token_inputs
    assert 300 in token_inputs
