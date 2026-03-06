"""_build_agent_link_map のユニットテスト"""

from __future__ import annotations

from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    ToolUseBlock,
    UsageData,
    UserEntry,
)
from session_analyzer.session_analyzer import _build_agent_link_map

# ---------------------------------------------------------------------------
# テストヘルパー
# ---------------------------------------------------------------------------


def _make_parsed(
    main_entries=None,
    subagent_entries=None,
) -> ParsedSession:
    return ParsedSession(
        session_id="test-session",
        main_entries=main_entries or [],
        subagent_entries=subagent_entries or {},
    )


def _make_assistant(content) -> AssistantEntry:
    return AssistantEntry(
        uuid="uuid-1",
        parent_uuid=None,
        timestamp="2025-01-01T00:00:00Z",
        model="claude-test",
        content=content,
        usage=UsageData(),
        agent_id=None,
    )


def _make_user(content="msg") -> UserEntry:
    return UserEntry(
        uuid="uuid-2",
        parent_uuid=None,
        timestamp="2025-01-01T00:00:00Z",
        is_meta=False,
        content=content,
        agent_id=None,
    )


def _tool_use(id: str, name: str) -> ToolUseBlock:
    return ToolUseBlock(type="tool_use", id=id, name=name, input={})


# ---------------------------------------------------------------------------
# タスク 5.2: リンクマップ構築ロジックの単体テスト
# ---------------------------------------------------------------------------


class TestBuildAgentLinkMap:
    """_build_agent_link_map の動作検証"""

    def test_two_agent_calls_two_subagents_mapped_correctly(self):
        """Agent ToolUseBlock が 2 件、サブエージェントキーが 2 件の場合に正しくマッピングされる"""
        block1 = _tool_use("tool-id-1", "Agent")
        block2 = _tool_use("tool-id-2", "Agent")
        parsed = _make_parsed(
            main_entries=[_make_assistant([block1, block2])],
            subagent_entries={
                "agent-sub-001": [_make_user()],
                "agent-sub-002": [_make_user()],
            },
        )
        result = _build_agent_link_map(parsed)
        assert result == {
            "tool-id-1": "agent-sub-001",
            "tool-id-2": "agent-sub-002",
        }

    def test_task_tool_also_mapped(self):
        """Task ToolUseBlock も Agent と同様にマッピングされる"""
        block1 = _tool_use("task-id-1", "Task")
        block2 = _tool_use("task-id-2", "Task")
        parsed = _make_parsed(
            main_entries=[_make_assistant([block1, block2])],
            subagent_entries={
                "agent-sub-001": [_make_user()],
                "agent-sub-002": [_make_user()],
            },
        )
        result = _build_agent_link_map(parsed)
        assert result == {
            "task-id-1": "agent-sub-001",
            "task-id-2": "agent-sub-002",
        }

    def test_fewer_subagents_than_calls_excess_not_in_map(self):
        """Agent 呼び出し数よりサブエージェント数が少ない場合、超過分がマッピングに含まれない"""
        block1 = _tool_use("tool-id-1", "Agent")
        block2 = _tool_use("tool-id-2", "Agent")
        block3 = _tool_use("tool-id-3", "Agent")
        parsed = _make_parsed(
            main_entries=[_make_assistant([block1, block2, block3])],
            subagent_entries={
                "agent-sub-001": [_make_user()],
            },
        )
        result = _build_agent_link_map(parsed)
        assert result == {"tool-id-1": "agent-sub-001"}
        assert "tool-id-2" not in result
        assert "tool-id-3" not in result

    def test_non_agent_task_tools_not_in_map(self):
        """Agent および Task 以外のツール呼び出しがマッピングに含まれない"""
        bash_block = _tool_use("bash-id-1", "Bash")
        read_block = _tool_use("read-id-1", "Read")
        agent_block = _tool_use("agent-id-1", "Agent")
        parsed = _make_parsed(
            main_entries=[_make_assistant([bash_block, read_block, agent_block])],
            subagent_entries={
                "agent-sub-001": [_make_user()],
            },
        )
        result = _build_agent_link_map(parsed)
        # Bash, Read はマッピングに含まれない
        assert "bash-id-1" not in result
        assert "read-id-1" not in result
        # Agent のみがマッピングされる
        assert result == {"agent-id-1": "agent-sub-001"}

    def test_no_agent_calls_returns_empty_map(self):
        """Agent/Task 呼び出しが 0 件の場合、空のマッピングが返る"""
        block = _tool_use("bash-id-1", "Bash")
        parsed = _make_parsed(
            main_entries=[_make_assistant([block])],
            subagent_entries={"agent-sub-001": [_make_user()]},
        )
        result = _build_agent_link_map(parsed)
        assert result == {}

    def test_no_subagents_returns_empty_map(self):
        """サブエージェントが 0 件の場合、空のマッピングが返る"""
        block = _tool_use("agent-id-1", "Agent")
        parsed = _make_parsed(
            main_entries=[_make_assistant([block])],
            subagent_entries={},
        )
        result = _build_agent_link_map(parsed)
        assert result == {}

    def test_user_entries_ignored(self):
        """UserEntry 内のブロックは対象外（AssistantEntry のみ処理される）"""
        # UserEntry の中には ToolUseBlock は通常存在しないが、
        # AssistantEntry のみを走査することを確認する
        parsed = _make_parsed(
            main_entries=[_make_user("simple string")],
            subagent_entries={"agent-sub-001": [_make_user()]},
        )
        result = _build_agent_link_map(parsed)
        assert result == {}

    def test_position_based_mapping_preserves_insertion_order(self):
        """挿入順でのサブエージェントキー対応が保たれる"""
        block1 = _tool_use("tool-id-1", "Agent")
        block2 = _tool_use("tool-id-2", "Task")
        parsed = _make_parsed(
            main_entries=[_make_assistant([block1, block2])],
            subagent_entries={
                "agent-first": [_make_user()],
                "agent-second": [_make_user()],
            },
        )
        result = _build_agent_link_map(parsed)
        # 1 番目の呼び出し → 1 番目のサブエージェントキー
        assert result["tool-id-1"] == "agent-first"
        # 2 番目の呼び出し → 2 番目のサブエージェントキー
        assert result["tool-id-2"] == "agent-second"
