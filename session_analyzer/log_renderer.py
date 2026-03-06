"""ログ詳細タブ HTML レンダラー"""

from __future__ import annotations

import json

import markdown

from session_analyzer.models import (
    AssistantEntry,
    ContentBlock,
    LogEntry,
    ParsedSession,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserEntry,
)

# Agent/Task 起動ツール名（subagent.py と同値）
_SUBAGENT_TOOL_NAMES = {"Task", "Agent"}

# 1,000 件超時の初期表示件数
_MAX_INITIAL_ENTRIES = 200

# 折りたたみ閾値（この行数以上で折りたたみ表示）
_LONG_CONTENT_LINES = 5


def _render_markdown(text: str) -> str:
    # 生のHTMLタグを無効化（XSS防止）: < と & をエスケープしてから Markdown に渡す
    # > はエスケープしない（blockquote 構文 `> text` を保持するため）
    safe = text.replace("&", "&amp;").replace("<", "&lt;")
    return markdown.markdown(safe, extensions=["fenced_code", "tables"])


def _is_long(text: str) -> bool:
    return text.count("\n") >= _LONG_CONTENT_LINES


def _esc(text: str) -> str:
    """XSS 防止のための HTML エスケープ"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_content_block(block: ContentBlock, agent_link_map: dict[str, str]) -> str:
    """ContentBlock バリアント別 HTML 生成"""
    if isinstance(block, TextBlock):
        if _is_long(block.text):
            summary = _esc(block.text.split("\n")[0][:80])
            md_html = _render_markdown(block.text)
            return f"""<details class="log-text-collapsible">
  <summary>テキスト: {summary}…</summary>
  <div class="log-text-content log-text-md">{md_html}</div>
</details>"""
        return f'<div class="log-text-md">{_render_markdown(block.text)}</div>'

    if isinstance(block, ThinkingBlock):
        if block.thinking:
            summary_text = _esc(block.thinking[:80].replace("\n", " "))
            content_html = _esc(block.thinking)
        else:
            summary_text = "（暗号化済み）"
            content_html = '<em style="color:var(--color-text-muted)">この思考ブロックは暗号化されています。</em>'
        return f"""<details class="log-thinking">
  <summary>思考: {summary_text}</summary>
  <div class="thinking-content">{content_html}</div>
</details>"""

    if isinstance(block, ToolUseBlock):
        input_json = _esc(json.dumps(block.input, ensure_ascii=False, indent=2))
        extra_class = ""
        link_html = ""
        if block.name in _SUBAGENT_TOOL_NAMES:
            extra_class = " agent-launch"
            subagent_key = agent_link_map.get(block.id)
            if subagent_key:
                link_html = f' <a href="#subagent-{_esc(subagent_key)}" class="subagent-link">→ サブエージェントへ</a>'
        return f"""<details class="log-tool-use{extra_class}">
  <summary>ツール: {_esc(block.name)}{link_html}</summary>
  <pre class="tool-input">{input_json}</pre>
</details>"""

    if isinstance(block, ToolResultBlock):
        error_class = " tool-result-error" if block.is_error else ""
        error_badge = (
            '<span class="badge badge-failure">エラー</span> ' if block.is_error else ""
        )
        content_escaped = _esc(block.content)
        if _is_long(block.content):
            label = "エラー結果" if block.is_error else "ツール結果"
            summary_text = _esc(block.content.split("\n")[0][:80])
            return f"""<details class="log-tool-result-collapsible{error_class}">
  <summary>{error_badge}{label}: {summary_text}…</summary>
  <div class="log-tool-result-content">{content_escaped}</div>
</details>"""
        return f'<div class="log-tool-result{error_class}">{error_badge}<span class="tool-result-content">{content_escaped}</span></div>'

    return ""


def _render_entry(entry: LogEntry, agent_link_map: dict[str, str]) -> str:
    """単一ログエントリの HTML 生成"""
    if isinstance(entry, AssistantEntry):
        role_label = "assistant"
        role_class = "role-assistant"
        meta_html = f'<span class="log-model meta-label">{_esc(entry.model)}</span>'
        content_html = "".join(
            _render_content_block(b, agent_link_map) for b in entry.content
        )
    else:
        assert isinstance(entry, UserEntry)
        role_label = "user"
        role_class = "role-user"
        meta_badge = (
            ' <span class="badge badge-meta">meta</span>' if entry.is_meta else ""
        )
        meta_html = meta_badge
        if isinstance(entry.content, str):
            if _is_long(entry.content):
                summary = _esc(entry.content.split("\n")[0][:80])
                md_html = _render_markdown(entry.content)
                content_html = f"""<details class="log-text-collapsible">
  <summary>テキスト: {summary}…</summary>
  <div class="log-text-content log-text-md">{md_html}</div>
</details>"""
            else:
                content_html = (
                    f'<div class="log-text-md">{_render_markdown(entry.content)}</div>'
                )
        else:
            content_html = "".join(
                _render_content_block(b, agent_link_map) for b in entry.content
            )

    return f"""<div id="entry-{_esc(entry.uuid)}" class="log-entry {role_class}" data-log-entry>
  <div class="log-entry-header">
    <span class="log-role-badge">{role_label}</span>
    {meta_html}
    <span class="log-timestamp meta-label">{_esc(entry.timestamp)}</span>
  </div>
  <div class="log-entry-body">{content_html}</div>
</div>"""


def _render_log_entries(entries: list[LogEntry], agent_link_map: dict[str, str]) -> str:
    """エントリリストの HTML 生成（1,000 件超対応）"""
    if not entries:
        return '<p class="empty-msg">ログエントリが見つかりません</p>'

    total = len(entries)
    show_toggle = total > 1000
    html_parts: list[str] = []

    for i, entry in enumerate(entries):
        entry_html = _render_entry(entry, agent_link_map)
        if show_toggle and i >= _MAX_INITIAL_ENTRIES:
            # 201 件目以降は非表示
            entry_html = entry_html.replace(
                "data-log-entry", 'data-log-entry class="log-entry-hidden"', 1
            )
        html_parts.append(entry_html)

    result = "".join(html_parts)

    if show_toggle:
        remaining = total - _MAX_INITIAL_ENTRIES
        result += f'<button class="show-more-btn" onclick="showAllLogEntries(this)">{remaining} 件をさらに表示</button>'

    return f'<div class="log-entries-container">{result}</div>'


def _render_subagent_section(
    agent_id: str, entries: list[LogEntry], agent_link_map: dict[str, str]
) -> str:
    """サブエージェントセクション HTML 生成"""
    entries_html = _render_log_entries(entries, agent_link_map)
    return f"""<section id="subagent-{_esc(agent_id)}" class="subagent-section card">
  <h2>サブエージェント: {_esc(agent_id)}</h2>
  <p><a href="#tab-log" class="back-link">← メインセッションへ戻る</a></p>
  {entries_html}
</section>"""


def render_log_detail_tab(
    parsed: ParsedSession,
    agent_link_map: dict[str, str],
) -> str:
    """
    「ログ詳細」タブ全体の HTML 文字列を返す。

    Args:
        parsed: パース済みセッション（main + subagent エントリ）
        agent_link_map: ToolUseBlock.id → subagent_entries キー のマッピング

    Returns:
        タブパネル内部の HTML 文字列（<div class="card"> 群）
    """
    # メインセッションエントリ
    main_html = f"""<div class="card">
  <h2 id="tab-log">メインセッション ログ</h2>
  {_render_log_entries(parsed.main_entries, agent_link_map)}
</div>"""

    # サブエージェントセクション
    subagent_html = ""
    for agent_id, entries in parsed.subagent_entries.items():
        subagent_html += _render_subagent_section(agent_id, entries, agent_link_map)

    return main_html + subagent_html
