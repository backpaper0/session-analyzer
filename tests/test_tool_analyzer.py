"""タスク4.3: ツール使用サマリーと Bash コマンド集計テスト"""

from session_analyzer.analyzers.tool import ToolAnalyzer
from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    ToolReport,
    ToolResultBlock,
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


def _make_assistant(
    content: list, timestamp: str = "2024-01-01T00:00:00Z", agent_id: str | None = None
) -> AssistantEntry:
    return AssistantEntry(
        uuid="a1",
        parent_uuid=None,
        timestamp=timestamp,
        model="claude-sonnet-4-6",
        content=content,
        usage=UsageData(),
        agent_id=agent_id,
    )


def _make_user_with_result(
    tool_use_id: str,
    content: str,
    is_error: bool = False,
    timestamp: str = "2024-01-01T00:00:01Z",
) -> UserEntry:
    return UserEntry(
        uuid="u1",
        parent_uuid=None,
        timestamp=timestamp,
        is_meta=False,
        content=[
            ToolResultBlock(
                type="tool_result",
                tool_use_id=tool_use_id,
                content=content,
                is_error=is_error,
            )
        ],
        agent_id=None,
    )


def _tool_use(tool_id: str, name: str, cmd: str | None = None) -> ToolUseBlock:
    inp = {"command": cmd} if cmd else {}
    return ToolUseBlock(type="tool_use", id=tool_id, name=name, input=inp)


# --- 戻り値の型 ---


def test_analyze_returns_tool_report():
    result = ToolAnalyzer().analyze(_make_session())
    assert isinstance(result, ToolReport)


def test_analyze_empty_session():
    result = ToolAnalyzer().analyze(_make_session())
    assert result.tool_counts == {}
    assert result.bash_invocations == []
    assert result.bash_aggregation == []


# --- ツール使用カウント ---


def test_analyze_counts_tool_by_name():
    """tool_useブロックがツール名別にカウントされること"""
    entries = [
        _make_assistant([_tool_use("t1", "Read"), _tool_use("t2", "Read")]),
        _make_assistant([_tool_use("t3", "Bash", "ls")]),
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))

    assert result.tool_counts["Read"] == 2
    assert result.tool_counts["Bash"] == 1


def test_analyze_counts_from_subagents():
    """サブエージェントのtool_useも集計対象であること"""
    main_entries = [_make_assistant([_tool_use("t1", "Read")])]
    sub_entries = [
        _make_assistant(
            [_tool_use("t2", "Read"), _tool_use("t3", "Write")], agent_id="sub1"
        )
    ]
    result = ToolAnalyzer().analyze(_make_session(main_entries, {"sub1": sub_entries}))

    assert result.tool_counts["Read"] == 2
    assert result.tool_counts["Write"] == 1


def test_analyze_user_entries_not_counted():
    """userエントリのtool_resultはtool_countsに含まれないこと"""
    entries = [_make_user_with_result("t1", "output")]
    result = ToolAnalyzer().analyze(_make_session(entries))
    assert result.tool_counts == {}


# --- Bash 実行一覧 ---


def test_analyze_bash_invocation_command():
    """Bashツール実行がbash_invocationsに記録されること"""
    entries = [
        _make_assistant([_tool_use("t1", "Bash", "ls -la")]),
        _make_user_with_result("t1", "file1\nfile2"),
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))

    assert len(result.bash_invocations) == 1
    assert result.bash_invocations[0].command == "ls -la"


def test_analyze_bash_invocation_not_error():
    """正常終了のBash実行はis_error=Falseであること"""
    entries = [
        _make_assistant([_tool_use("t1", "Bash", "ls")]),
        _make_user_with_result("t1", "output", is_error=False),
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))
    assert result.bash_invocations[0].is_error is False
    assert result.bash_invocations[0].error_message is None


def test_analyze_bash_invocation_is_error():
    """エラー終了のBash実行はis_error=True, error_messageがセットされること"""
    entries = [
        _make_assistant([_tool_use("t1", "Bash", "bad-cmd")]),
        _make_user_with_result("t1", "command not found", is_error=True),
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))

    inv = result.bash_invocations[0]
    assert inv.is_error is True
    assert inv.error_message == "command not found"


def test_analyze_bash_invocation_timestamp():
    """BashInvocationにassistantエントリのタイムスタンプが設定されること"""
    entries = [
        _make_assistant(
            [_tool_use("t1", "Bash", "ls")], timestamp="2024-06-01T12:00:00Z"
        ),
        _make_user_with_result("t1", "output"),
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))
    assert result.bash_invocations[0].timestamp == "2024-06-01T12:00:00Z"


def test_analyze_bash_invocation_source_main():
    """メインエントリのBash実行はsource='main'であること"""
    entries = [
        _make_assistant([_tool_use("t1", "Bash", "ls")]),
        _make_user_with_result("t1", "output"),
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))
    assert result.bash_invocations[0].source == "main"


def test_analyze_bash_invocation_source_subagent():
    """サブエージェントのBash実行はsource=agent_idであること"""
    sub_entries = [
        _make_assistant([_tool_use("t1", "Bash", "ls")], agent_id="sub1"),
        UserEntry(
            uuid="u1",
            parent_uuid=None,
            timestamp="2024-01-01T00:00:01Z",
            is_meta=False,
            content=[
                ToolResultBlock(
                    type="tool_result",
                    tool_use_id="t1",
                    content="output",
                    is_error=False,
                )
            ],
            agent_id="sub1",
        ),
    ]
    result = ToolAnalyzer().analyze(
        _make_session(subagent_entries={"sub1": sub_entries})
    )
    assert result.bash_invocations[0].source == "sub1"


def test_analyze_bash_without_tool_result():
    """tool_resultが見つからないBash実行もis_error=Falseで記録されること"""
    entries = [_make_assistant([_tool_use("t1", "Bash", "ls")])]
    result = ToolAnalyzer().analyze(_make_session(entries))

    assert len(result.bash_invocations) == 1
    assert result.bash_invocations[0].is_error is False


def test_analyze_non_bash_tool_not_in_bash_invocations():
    """Bash以外のtool_useはbash_invocationsに含まれないこと"""
    entries = [_make_assistant([_tool_use("t1", "Read")])]
    result = ToolAnalyzer().analyze(_make_session(entries))
    assert result.bash_invocations == []


# --- Bash コマンド集計 ---


def test_analyze_bash_aggregation_base_command():
    """コマンドのベースコマンドが正しく集計されること"""
    entries = [
        _make_assistant([_tool_use("t1", "Bash", "ls -la")]),
        _make_assistant([_tool_use("t2", "Bash", "ls /tmp")]),
        _make_assistant([_tool_use("t3", "Bash", "cat file.txt")]),
    ]
    for e in entries:
        pass  # no tool results needed for aggregation

    result = ToolAnalyzer().analyze(_make_session(entries))

    counts = {a.base_command: a.count for a in result.bash_aggregation}
    assert counts["ls"] == 2
    assert counts["cat"] == 1


def test_analyze_bash_aggregation_sorted_descending():
    """bash_aggregationが使用回数降順に並ぶこと"""
    entries = [
        _make_assistant([_tool_use(f"t{i}", "Bash", cmd)])
        for i, cmd in enumerate(["ls", "ls", "ls", "cat", "cat", "git status"])
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))

    counts = [a.count for a in result.bash_aggregation]
    assert counts == sorted(counts, reverse=True)


def test_analyze_subcommand_expansion_git():
    """gitコマンドはサブコマンドが展開されること"""
    entries = [
        _make_assistant([_tool_use("t1", "Bash", "git commit -m 'msg'")]),
        _make_assistant([_tool_use("t2", "Bash", "git push origin main")]),
        _make_assistant([_tool_use("t3", "Bash", "git commit --amend")]),
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))

    git_agg = next(a for a in result.bash_aggregation if a.base_command == "git")
    assert git_agg.sub_commands["commit"] == 2
    assert git_agg.sub_commands["push"] == 1


def test_analyze_subcommand_expansion_targets():
    """git/docker/mvn/npm/uvのみサブコマンド展開されること"""
    entries = [
        _make_assistant([_tool_use("t1", "Bash", "docker run nginx")]),
        _make_assistant([_tool_use("t2", "Bash", "npm install")]),
        _make_assistant([_tool_use("t3", "Bash", "uv pip install requests")]),
        _make_assistant([_tool_use("t4", "Bash", "ls -la")]),  # ls は展開対象外
    ]
    result = ToolAnalyzer().analyze(_make_session(entries))

    agg_map = {a.base_command: a for a in result.bash_aggregation}
    assert agg_map["docker"].sub_commands == {"run": 1}
    assert agg_map["npm"].sub_commands == {"install": 1}
    assert agg_map["uv"].sub_commands == {"pip": 1}
    assert agg_map["ls"].sub_commands == {}  # ls は展開なし


def test_analyze_bash_shlex_parse_error_handled():
    """shlexでパースできないコマンドも先頭トークンで集計されること"""
    # シングルクォートが閉じていないなど
    entries = [_make_assistant([_tool_use("t1", "Bash", "echo 'unclosed")])]
    result = ToolAnalyzer().analyze(_make_session(entries))
    # エラーにならずにbash_invocationsに記録されること
    assert len(result.bash_invocations) == 1


def test_analyze_bash_invocation_entry_uuid():
    """BashInvocationにassistantエントリのuuidが設定されること"""
    assistant = AssistantEntry(
        uuid="entry-uuid-abc",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        model="claude-sonnet-4-6",
        content=[_tool_use("t1", "Bash", "ls")],
        usage=UsageData(),
        agent_id=None,
    )
    result = ToolAnalyzer().analyze(_make_session([assistant]))
    assert result.bash_invocations[0].entry_uuid == "entry-uuid-abc"
