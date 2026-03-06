"""LogRenderer のユニットテスト"""
from __future__ import annotations

import pytest

from session_analyzer.log_renderer import render_log_detail_tab
from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UsageData,
    UserEntry,
)


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


def _make_assistant(content, timestamp="2025-01-01T00:00:00Z") -> AssistantEntry:
    return AssistantEntry(
        uuid="uuid-1",
        parent_uuid=None,
        timestamp=timestamp,
        model="claude-test",
        content=content,
        usage=UsageData(),
        agent_id=None,
    )


def _make_user(content, timestamp="2025-01-01T00:00:00Z", is_meta=False) -> UserEntry:
    return UserEntry(
        uuid="uuid-2",
        parent_uuid=None,
        timestamp=timestamp,
        is_meta=is_meta,
        content=content,
        agent_id=None,
    )


# ---------------------------------------------------------------------------
# タスク 1.1: ContentBlock の種別ごとの HTML 変換
# ---------------------------------------------------------------------------

class TestTextBlock:
    """TextBlock をプレーンテキスト表示として変換する"""

    def test_text_block_content_appears_in_html(self):
        """TextBlock のテキストが HTML に含まれる"""
        block = TextBlock(type="text", text="Hello, world!")
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "Hello, world!" in html

    def test_text_block_xss_escaped(self):
        """TextBlock の XSS 文字がエスケープされる"""
        block = TextBlock(type="text", text='<script>alert("xss")</script>')
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "&quot;" in html

    def test_text_block_ampersand_escaped(self):
        """TextBlock の & がエスケープされる"""
        block = TextBlock(type="text", text="foo & bar")
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "&amp;" in html
        assert "foo & bar" not in html


class TestToolUseBlock:
    """ToolUseBlock を折りたたみ可能な入力パラメータ表示として変換する"""

    def test_tool_use_block_name_appears(self):
        """ToolUseBlock のツール名が HTML に含まれる"""
        block = ToolUseBlock(type="tool_use", id="id-1", name="Bash", input={"command": "ls"})
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "Bash" in html

    def test_tool_use_block_uses_details_summary(self):
        """ToolUseBlock が <details>/<summary> パターンで折りたたまれる"""
        block = ToolUseBlock(type="tool_use", id="id-1", name="Read", input={"file_path": "/tmp/x"})
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "<details" in html
        assert "<summary" in html

    def test_tool_use_block_input_appears(self):
        """ToolUseBlock の入力パラメータが HTML に含まれる"""
        block = ToolUseBlock(type="tool_use", id="id-1", name="Bash", input={"command": "echo hello"})
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "echo hello" in html

    def test_tool_use_block_xss_in_input_escaped(self):
        """ToolUseBlock の入力パラメータ内 XSS がエスケープされる"""
        block = ToolUseBlock(type="tool_use", id="id-1", name="Write", input={"content": "<b>bold</b>"})
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "<b>bold</b>" not in html


class TestThinkingBlock:
    """ThinkingBlock を既存の thinking セクションと同じ折りたたみ形式として変換する"""

    def test_thinking_block_uses_details_summary(self):
        """ThinkingBlock が <details>/<summary> パターンで表示される"""
        block = ThinkingBlock(type="thinking", thinking="I think...", signature="sig")
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "<details" in html
        assert "<summary" in html

    def test_thinking_block_content_appears(self):
        """ThinkingBlock のテキストが HTML に含まれる"""
        block = ThinkingBlock(type="thinking", thinking="Deep thoughts here", signature="sig")
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "Deep thoughts here" in html

    def test_thinking_block_xss_escaped(self):
        """ThinkingBlock の XSS がエスケープされる"""
        block = ThinkingBlock(type="thinking", thinking="<script>evil()</script>", signature="sig")
        parsed = _make_parsed(main_entries=[_make_assistant([block])])
        html = render_log_detail_tab(parsed, {})
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestToolResultBlock:
    """ToolResultBlock をエラーフラグ付きで変換する"""

    def test_tool_result_content_appears(self):
        """ToolResultBlock のコンテンツが HTML に含まれる"""
        block = ToolResultBlock(
            type="tool_result", tool_use_id="id-1", content="result text", is_error=False
        )
        parsed = _make_parsed(main_entries=[_make_user([block])])
        html = render_log_detail_tab(parsed, {})
        assert "result text" in html

    def test_tool_result_error_flag_shown(self):
        """ToolResultBlock の is_error=True でエラー表示が含まれる"""
        block = ToolResultBlock(
            type="tool_result", tool_use_id="id-1", content="error output", is_error=True
        )
        parsed = _make_parsed(main_entries=[_make_user([block])])
        html = render_log_detail_tab(parsed, {})
        # エラーであることを示す何らかの表示（クラスやテキスト）
        assert "error" in html.lower() or "エラー" in html

    def test_tool_result_xss_escaped(self):
        """ToolResultBlock の XSS がエスケープされる"""
        block = ToolResultBlock(
            type="tool_result", tool_use_id="id-1", content="<img src=x onerror=alert()>", is_error=False
        )
        parsed = _make_parsed(main_entries=[_make_user([block])])
        html = render_log_detail_tab(parsed, {})
        assert "<img" not in html
        assert "&lt;img" in html


# ---------------------------------------------------------------------------
# タスク 1.2: 単一ログエントリの HTML 表示（ロール・タイムスタンプ・コンテンツ）
# ---------------------------------------------------------------------------

class TestRenderEntry:
    """ロール・タイムスタンプ・コンテンツを含む単一ログエントリの HTML 表示"""

    def test_assistant_role_badge_appears(self):
        """assistant エントリにロールバッジが表示される"""
        entry = _make_assistant([TextBlock(type="text", text="hello")])
        parsed = _make_parsed(main_entries=[entry])
        html = render_log_detail_tab(parsed, {})
        assert "assistant" in html

    def test_user_role_badge_appears(self):
        """user エントリにロールバッジが表示される"""
        entry = _make_user("user message")
        parsed = _make_parsed(main_entries=[entry])
        html = render_log_detail_tab(parsed, {})
        assert "user" in html

    def test_timestamp_appears_in_entry(self):
        """タイムスタンプが各エントリのヘッダーに表示される"""
        ts = "2025-06-15T12:34:56Z"
        entry = _make_assistant([TextBlock(type="text", text="hi")], timestamp=ts)
        parsed = _make_parsed(main_entries=[entry])
        html = render_log_detail_tab(parsed, {})
        assert ts in html

    def test_assistant_content_blocks_rendered(self):
        """assistant エントリの ContentBlock リストが一覧表示される"""
        blocks = [
            TextBlock(type="text", text="first"),
            TextBlock(type="text", text="second"),
        ]
        parsed = _make_parsed(main_entries=[_make_assistant(blocks)])
        html = render_log_detail_tab(parsed, {})
        assert "first" in html
        assert "second" in html

    def test_user_string_content_rendered(self):
        """user エントリの文字列コンテンツが表示される"""
        parsed = _make_parsed(main_entries=[_make_user("plain string content")])
        html = render_log_detail_tab(parsed, {})
        assert "plain string content" in html

    def test_user_content_block_list_rendered(self):
        """user エントリの ContentBlock リストが適切に表示される"""
        block = ToolResultBlock(
            type="tool_result", tool_use_id="id-1", content="result content", is_error=False
        )
        parsed = _make_parsed(main_entries=[_make_user([block])])
        html = render_log_detail_tab(parsed, {})
        assert "result content" in html

    def test_is_meta_true_shows_meta_badge(self):
        """isMeta=True のエントリが視覚的に区別される（meta バッジ等）"""
        entry = _make_user("system message", is_meta=True)
        parsed = _make_parsed(main_entries=[entry])
        html = render_log_detail_tab(parsed, {})
        assert "meta" in html.lower()

    def test_is_meta_false_no_meta_badge(self):
        """isMeta=False の通常エントリにはメタバッジが表示されない"""
        entry = _make_user("normal message", is_meta=False)
        parsed = _make_parsed(main_entries=[entry])
        html = render_log_detail_tab(parsed, {})
        # meta バッジが含まれないこと（ただし "meta-label" などのクラス名は除く）
        assert 'badge-meta' not in html

    def test_role_class_distinguishes_user_and_assistant(self):
        """user と assistant がロールクラスで区別される"""
        user_entry = _make_user("from user")
        assistant_entry = _make_assistant([TextBlock(type="text", text="from assistant")])
        parsed = _make_parsed(main_entries=[user_entry, assistant_entry])
        html = render_log_detail_tab(parsed, {})
        assert "role-user" in html
        assert "role-assistant" in html


# ---------------------------------------------------------------------------
# タスク 1.3: エントリリストの表示と 1,000 件超のパフォーマンス対応
# ---------------------------------------------------------------------------

class TestRenderLogEntries:
    """エントリリストの表示と 1,000 件超のパフォーマンス対応"""

    def test_empty_entries_shows_not_found_message(self):
        """エントリが空の場合に「ログエントリが見つかりません」が含まれる"""
        parsed = _make_parsed(main_entries=[])
        html = render_log_detail_tab(parsed, {})
        assert "ログエントリが見つかりません" in html

    def test_entries_wrapped_in_scrollable_container(self):
        """エントリがスクロール可能なコンテナ内に表示される"""
        entry = _make_user("some message")
        parsed = _make_parsed(main_entries=[entry])
        html = render_log_detail_tab(parsed, {})
        assert "log-entries-container" in html

    def test_1001_entries_shows_toggle_button(self):
        """エントリ数が 1,001 件の場合に「残りを表示」ボタン要素が出力される"""
        entries = [_make_user(f"msg {i}") for i in range(1001)]
        parsed = _make_parsed(main_entries=entries)
        html = render_log_detail_tab(parsed, {})
        assert "show-more-btn" in html

    def test_1001_entries_button_shows_remaining_count(self):
        """1,001 件時のボタンが残り 801 件を表示する"""
        entries = [_make_user(f"msg {i}") for i in range(1001)]
        parsed = _make_parsed(main_entries=entries)
        html = render_log_detail_tab(parsed, {})
        # 残り = 1001 - 200 = 801
        assert "801" in html

    def test_1001_entries_entries_after_200_are_hidden(self):
        """1,001 件の場合に 201 件目以降が log-entry-hidden クラスを持つ"""
        entries = [_make_user(f"msg {i}") for i in range(1001)]
        parsed = _make_parsed(main_entries=entries)
        html = render_log_detail_tab(parsed, {})
        assert "log-entry-hidden" in html

    def test_1000_entries_no_toggle_button(self):
        """エントリ数が 1,000 件以下の場合は「残りを表示」ボタンが出力されない"""
        entries = [_make_user(f"msg {i}") for i in range(1000)]
        parsed = _make_parsed(main_entries=entries)
        html = render_log_detail_tab(parsed, {})
        assert "show-more-btn" not in html

    def test_1000_entries_no_hidden_entries(self):
        """エントリ数が 1,000 件以下の場合は非表示エントリが存在しない"""
        entries = [_make_user(f"msg {i}") for i in range(1000)]
        parsed = _make_parsed(main_entries=entries)
        html = render_log_detail_tab(parsed, {})
        assert "log-entry-hidden" not in html


# ---------------------------------------------------------------------------
# タスク 1.4: サブエージェントセクションの HTML 実装
# ---------------------------------------------------------------------------

class TestRenderSubagentSection:
    """サブエージェントセクションの HTML 生成"""

    def test_subagent_section_has_anchor_id(self):
        """agent_id のページ内アンカーが設定される"""
        entry = _make_user("subagent message")
        parsed = _make_parsed(subagent_entries={"agent-abc": [entry]})
        html = render_log_detail_tab(parsed, {})
        assert 'id="subagent-agent-abc"' in html

    def test_subagent_section_shows_agent_id_in_header(self):
        """agent_id がセクションヘッダーに表示される"""
        entry = _make_user("subagent message")
        parsed = _make_parsed(subagent_entries={"agent-xyz": [entry]})
        html = render_log_detail_tab(parsed, {})
        assert "agent-xyz" in html

    def test_subagent_section_has_back_navigation_link(self):
        """メインセッションへ戻るページ内ナビゲーションリンクが提供される"""
        entry = _make_user("subagent message")
        parsed = _make_parsed(subagent_entries={"agent-001": [entry]})
        html = render_log_detail_tab(parsed, {})
        # #tab-log へのリンクが存在すること
        assert 'href="#tab-log"' in html

    def test_subagent_section_shows_entries(self):
        """サブエージェントのログエントリが一覧表示される"""
        entry = _make_user("subagent specific content")
        parsed = _make_parsed(subagent_entries={"agent-001": [entry]})
        html = render_log_detail_tab(parsed, {})
        assert "subagent specific content" in html

    def test_no_subagent_entries_omits_subagent_section(self):
        """サブエージェントが存在しない場合、サブエージェントセクションが出力されない"""
        parsed = _make_parsed(main_entries=[_make_user("main only")])
        html = render_log_detail_tab(parsed, {})
        assert "subagent-section" not in html

    def test_multiple_subagent_sections(self):
        """複数のサブエージェントが個別セクションで出力される"""
        parsed = _make_parsed(subagent_entries={
            "agent-001": [_make_user("msg from 001")],
            "agent-002": [_make_user("msg from 002")],
        })
        html = render_log_detail_tab(parsed, {})
        assert 'id="subagent-agent-001"' in html
        assert 'id="subagent-agent-002"' in html

    def test_subagent_agent_id_xss_escaped(self):
        """agent_id の XSS がアンカーでエスケープされる"""
        entry = _make_user("msg")
        parsed = _make_parsed(subagent_entries={'<script>evil</script>': [entry]})
        html = render_log_detail_tab(parsed, {})
        assert "<script>" not in html


# ---------------------------------------------------------------------------
# タスク 1.5: ログ詳細タブ全体を生成するメイン公開関数
# ---------------------------------------------------------------------------

class TestRenderLogDetailTab:
    """render_log_detail_tab のメイン公開関数テスト"""

    def test_agent_tool_with_link_map_shows_subagent_link(self):
        """Agent ToolUseBlock に agent_link_map が存在する場合のリンク HTML が出力される"""
        block = ToolUseBlock(type="tool_use", id="tool-id-1", name="Agent", input={"description": "do task"})
        entry = _make_assistant([block])
        parsed = _make_parsed(main_entries=[entry])
        agent_link_map = {"tool-id-1": "agent-sub-001"}
        html = render_log_detail_tab(parsed, agent_link_map)
        assert 'href="#subagent-agent-sub-001"' in html
        assert "subagent-link" in html

    def test_task_tool_with_link_map_shows_subagent_link(self):
        """Task ToolUseBlock に agent_link_map が存在する場合のリンク HTML が出力される"""
        block = ToolUseBlock(type="tool_use", id="tool-id-2", name="Task", input={"description": "run task"})
        entry = _make_assistant([block])
        parsed = _make_parsed(main_entries=[entry])
        agent_link_map = {"tool-id-2": "agent-sub-002"}
        html = render_log_detail_tab(parsed, agent_link_map)
        assert 'href="#subagent-agent-sub-002"' in html

    def test_agent_tool_without_link_map_shows_no_link(self):
        """agent_link_map に対応エントリがない場合にリンクなしで表示される"""
        block = ToolUseBlock(type="tool_use", id="tool-id-3", name="Agent", input={"description": "do task"})
        entry = _make_assistant([block])
        parsed = _make_parsed(main_entries=[entry])
        html = render_log_detail_tab(parsed, {})
        # agent-launch クラスは付くがリンクは出ない
        assert "agent-launch" in html
        assert "subagent-link" not in html

    def test_non_agent_tool_gets_no_agent_launch_class(self):
        """Agent/Task 以外の ToolUseBlock に agent-launch クラスが付かない"""
        block = ToolUseBlock(type="tool_use", id="tool-id-4", name="Bash", input={"command": "ls"})
        entry = _make_assistant([block])
        parsed = _make_parsed(main_entries=[entry])
        html = render_log_detail_tab(parsed, {"tool-id-4": "some-key"})
        assert "agent-launch" not in html

    def test_main_and_subagent_sections_both_present(self):
        """メインセクションとサブエージェントセクションが両方含まれる"""
        main_entry = _make_user("main message")
        sub_entry = _make_user("subagent message")
        parsed = _make_parsed(
            main_entries=[main_entry],
            subagent_entries={"agent-001": [sub_entry]},
        )
        html = render_log_detail_tab(parsed, {})
        assert "main message" in html
        assert "subagent message" in html
        assert 'id="subagent-agent-001"' in html

    def test_agent_link_map_passed_to_subagent_entries(self):
        """agent_link_map がサブエージェントエントリのレンダリング時にも渡される"""
        block = ToolUseBlock(type="tool_use", id="nested-tool", name="Agent", input={})
        sub_entry = _make_assistant([block])
        parsed = _make_parsed(
            main_entries=[],
            subagent_entries={"agent-001": [sub_entry]},
        )
        agent_link_map = {"nested-tool": "agent-002"}
        html = render_log_detail_tab(parsed, agent_link_map)
        assert 'href="#subagent-agent-002"' in html
