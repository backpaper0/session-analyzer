"""HTML レポーター"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from session_analyzer.exceptions import ReportGenerationError
from session_analyzer.log_renderer import render_log_detail_tab
from session_analyzer.models import ParsedSession, SessionReport


def _report_to_json(report: SessionReport) -> str:
    """SessionReport を JSON 文字列に変換する（JS 埋め込み用）"""
    raw: dict[str, Any] = asdict(report)
    return json.dumps(raw, ensure_ascii=False, default=str)


_CSS = """
:root {
    --color-bg: #f8f9fa;
    --color-surface: #ffffff;
    --color-primary: #6c8ebf;
    --color-primary-light: #dae8fc;
    --color-accent: #82b366;
    --color-accent-light: #d5e8d4;
    --color-warn: #d6b656;
    --color-warn-light: #fff2cc;
    --color-error: #ae4132;
    --color-error-light: #f8cecc;
    --color-success-bg: #d5e8d4;
    --color-failure-bg: #f8cecc;
    --color-border: #d0d7de;
    --color-text: #24292f;
    --color-text-muted: #57606a;
    --tab-active-bg: #ffffff;
    --tab-inactive-bg: #f0f3f6;
    --radius: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.08);
}

*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--color-bg);
    color: var(--color-text);
    line-height: 1.6;
    padding: 0 0 40px;
}

header {
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: var(--shadow);
}

header h1 {
    font-size: 1.2rem;
    font-weight: 600;
}

header .session-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

header .session-id {
    font-family: monospace;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    background: var(--color-bg);
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid var(--color-border);
}

header .session-cwd {
    font-family: monospace;
    font-size: 0.82rem;
    color: var(--color-text-muted);
}

header .session-time {
    font-size: 0.82rem;
    color: var(--color-text-muted);
}

.tab-bar {
    display: flex;
    gap: 2px;
    padding: 16px 24px 0;
    border-bottom: 2px solid var(--color-border);
    background: var(--color-bg);
    overflow-x: auto;
}

.tab-btn {
    padding: 8px 18px;
    border: 1px solid var(--color-border);
    border-bottom: none;
    border-radius: var(--radius) var(--radius) 0 0;
    background: var(--tab-inactive-bg);
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 0.9rem;
    font-family: inherit;
    white-space: nowrap;
    transition: background 0.15s, color 0.15s;
}

.tab-btn:hover {
    background: #e8ecf0;
    color: var(--color-text);
}

.tab-btn.active {
    background: var(--tab-active-bg);
    color: var(--color-text);
    font-weight: 600;
    border-bottom: 2px solid var(--tab-active-bg);
    margin-bottom: -2px;
}

.tab-panel {
    display: none;
    padding: 24px;
    max-width: 1100px;
    margin: 0 auto;
}

.tab-panel.active {
    display: block;
}

.card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
}

.card h2 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 14px;
    color: var(--color-primary);
    border-bottom: 1px solid var(--color-primary-light);
    padding-bottom: 8px;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
}

th, td {
    text-align: left;
    padding: 8px 12px;
    border-bottom: 1px solid var(--color-border);
}

th {
    background: var(--color-bg);
    font-weight: 600;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

tr:last-child td {
    border-bottom: none;
}

tr:hover td {
    background: var(--color-bg);
}

.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 0.78rem;
    font-weight: 600;
}

.badge-success {
    background: var(--color-success-bg);
    color: #2d6a35;
}

.badge-failure {
    background: var(--color-failure-bg);
    color: var(--color-error);
}

.bash-row.success td:first-child {
    border-left: 3px solid var(--color-accent);
}

.bash-row.failure td:first-child {
    border-left: 3px solid var(--color-error);
}

details {
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    margin-bottom: 10px;
    overflow: hidden;
}

details[open] {
    overflow: visible;
}

summary {
    padding: 10px 14px;
    cursor: pointer;
    background: var(--color-bg);
    font-weight: 500;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
}

summary::before {
    content: '▶';
    font-size: 0.7rem;
    transition: transform 0.15s;
    flex-shrink: 0;
}

details[open] > summary::before {
    transform: rotate(90deg);
}

summary:hover {
    background: #e8ecf0;
}

.thinking-content {
    padding: 14px 16px;
    font-size: 0.85rem;
    white-space: pre-wrap;
    word-break: break-word;
    border-top: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text);
    max-height: 400px;
    overflow-y: auto;
}

.meta-label {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    font-family: monospace;
}

.empty-msg {
    color: var(--color-text-muted);
    font-style: italic;
    text-align: center;
    padding: 20px;
}

.cost {
    font-weight: 600;
    color: var(--color-accent);
}

.na {
    color: var(--color-text-muted);
    font-style: italic;
}

.total-row td {
    font-weight: 700;
    background: var(--color-accent-light);
}

.skill-llm {
    background: var(--color-warn-light);
    color: #6b5900;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
}

.skill-user {
    background: var(--color-primary-light);
    color: #1a3a6b;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
}

code {
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 0.85em;
    background: var(--color-bg);
    padding: 1px 4px;
    border-radius: 3px;
    word-break: break-all;
}

.prompt-cell {
    max-width: 400px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ログ詳細タブ */
.log-entries-container {
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
}

.log-entry {
    border-bottom: 1px solid var(--color-border);
    padding: 10px 14px;
    font-size: 0.88rem;
}

.log-entry:last-child {
    border-bottom: none;
}

.log-entry-hidden {
    display: none;
}

.log-entry-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

.log-role-badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 99px;
    font-size: 0.75rem;
    font-weight: 600;
}

.role-assistant .log-role-badge {
    background: var(--color-primary-light);
    color: #1a3a6b;
}

.role-user .log-role-badge {
    background: var(--color-accent-light);
    color: #2d6a35;
}

.log-timestamp {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    font-family: monospace;
}

.log-model {
    font-size: 0.75rem;
    color: var(--color-text-muted);
}

.log-entry-body {
    padding-left: 4px;
}

.log-text {
    margin: 4px 0;
    white-space: pre-wrap;
    word-break: break-word;
}

.log-tool-use {
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    margin: 4px 0;
}

.log-tool-use.agent-launch {
    border-left: 3px solid var(--color-primary);
    background: var(--color-primary-light);
}

.agent-launch > summary {
    background: var(--color-primary-light);
    font-weight: 600;
}

.subagent-link {
    font-size: 0.8rem;
    color: var(--color-primary);
    text-decoration: none;
    font-weight: 600;
    margin-left: 8px;
}

.subagent-link:hover {
    text-decoration: underline;
}

.log-thinking {
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    margin: 4px 0;
}

.tool-input {
    padding: 10px 14px;
    font-size: 0.82rem;
    white-space: pre-wrap;
    word-break: break-all;
    background: var(--color-bg);
    border-top: 1px solid var(--color-border);
    max-height: 300px;
    overflow-y: auto;
    margin: 0;
}

.log-tool-result {
    padding: 6px 10px;
    border-radius: var(--radius);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    margin: 4px 0;
    font-size: 0.85rem;
    word-break: break-word;
}

.tool-result-error {
    background: var(--color-error-light);
    border-color: var(--color-error);
}

.tool-result-content {
    white-space: pre-wrap;
}

.show-more-btn {
    display: block;
    width: 100%;
    padding: 10px;
    border: 1px dashed var(--color-border);
    border-radius: var(--radius);
    background: var(--color-bg);
    color: var(--color-primary);
    cursor: pointer;
    font-size: 0.88rem;
    font-family: inherit;
    margin-top: 8px;
    text-align: center;
}

.show-more-btn:hover {
    background: var(--color-primary-light);
}

.subagent-section {
    margin-top: 20px;
}

.back-link {
    font-size: 0.85rem;
    color: var(--color-primary);
    text-decoration: none;
}

.back-link:hover {
    text-decoration: underline;
}

.badge-meta {
    background: var(--color-warn-light);
    color: #6b5900;
}

.log-text-content {
    padding: 14px 16px;
    font-size: 0.85rem;
    white-space: pre-wrap;
    word-break: break-word;
    border-top: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text);
    max-height: 400px;
    overflow-y: auto;
}

.log-tool-result-content {
    padding: 14px 16px;
    font-size: 0.85rem;
    white-space: pre-wrap;
    word-break: break-word;
    border-top: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text);
    max-height: 400px;
    overflow-y: auto;
}

.log-tool-result-collapsible.tool-result-error > summary {
    color: var(--color-error);
}

.log-link {
    font-size: 0.8rem;
    color: var(--color-primary);
    text-decoration: none;
    font-weight: 500;
    cursor: pointer;
}

.log-link:hover {
    text-decoration: underline;
}
"""

_JS = """
function showTab(id) {
    document.querySelectorAll('.tab-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.tab === id);
    });
    document.querySelectorAll('.tab-panel').forEach(function(panel) {
        panel.classList.toggle('active', panel.id === id);
    });
}

function goToLogEntry(anchorId) {
    showTab('tab-log');
    var el = document.getElementById(anchorId);
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        el.style.outline = '2px solid var(--color-primary)';
        setTimeout(function() { el.style.outline = ''; }, 1500);
    }
}

function showAllLogEntries(btn) {
    var container = btn.parentElement;
    container.querySelectorAll('.log-entry-hidden').forEach(function(el) {
        el.classList.remove('log-entry-hidden');
    });
    btn.remove();
}

document.addEventListener('DOMContentLoaded', function() {
    var btns = document.querySelectorAll('.tab-btn');
    btns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            showTab(btn.dataset.tab);
        });
    });
    if (btns.length > 0) {
        showTab(btns[0].dataset.tab);
    }
});
"""


def _fmt_timestamp(ts: str) -> str:
    """ISO 8601 文字列をローカル表示形式（YYYY-MM-DD HH:MM:SS）に変換する。"""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError, AttributeError:
        return ts


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt_cost(cost: float | None) -> str:
    if cost is None:
        return '<span class="na">N/A</span>'
    return f'<span class="cost">${cost:.4f}</span>'


def _render_token_section(report: SessionReport) -> str:
    token = report.token
    rows = ""
    for s in token.by_model:
        rows += f"""
        <tr>
            <td><code>{_esc(s.model)}</code></td>
            <td>{s.input_tokens:,}</td>
            <td>{s.output_tokens:,}</td>
            <td>{s.cache_creation_tokens:,}</td>
            <td>{s.cache_read_tokens:,}</td>
            <td>{_fmt_cost(s.estimated_cost_usd)}</td>
        </tr>"""

    t = token.total
    total_row = f"""
        <tr class="total-row">
            <td>合計</td>
            <td>{t.input_tokens:,}</td>
            <td>{t.output_tokens:,}</td>
            <td>{t.cache_creation_tokens:,}</td>
            <td>{t.cache_read_tokens:,}</td>
            <td>{_fmt_cost(t.estimated_cost_usd)}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="6" class="empty-msg">トークンデータなし</td></tr>'

    return f"""
    <div class="card">
        <h2>モデル別トークン使用量</h2>
        <table>
            <thead><tr>
                <th>モデル</th><th>入力</th><th>出力</th>
                <th>キャッシュ作成</th><th>キャッシュ読込</th><th>推定コスト (USD)</th>
            </tr></thead>
            <tbody>{rows}{total_row}</tbody>
        </table>
    </div>"""


def _render_skills_section(report: SessionReport) -> str:
    rows = ""
    for inv in report.skills.invocations:
        method_cls = "skill-llm" if "LLM" in inv.method else "skill-user"
        log_link = f'<a class="log-link" href="javascript:void(0)" onclick="goToLogEntry(\'entry-{_esc(inv.uuid)}\')">→ ログ詳細</a>'
        rows += f"""
        <tr>
            <td><code>{_esc(inv.skill_name)}</code></td>
            <td><span class="{method_cls}">{_esc(inv.method)}</span></td>
            <td class="meta-label">{_esc(inv.timestamp)}</td>
            <td>{log_link}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="4" class="empty-msg">スキル利用なし</td></tr>'

    summary_rows = ""
    for name, count in sorted(report.skills.summary.items(), key=lambda x: -x[1]):
        summary_rows += f"<tr><td><code>{_esc(name)}</code></td><td>{count}</td></tr>"

    summary_html = ""
    if summary_rows:
        summary_html = f"""
    <div class="card">
        <h2>スキル別集計</h2>
        <table>
            <thead><tr><th>スキル名</th><th>回数</th></tr></thead>
            <tbody>{summary_rows}</tbody>
        </table>
    </div>"""

    return f"""
    <div class="card">
        <h2>スキル利用一覧（時系列）</h2>
        <table>
            <thead><tr><th>スキル名</th><th>起動方法</th><th>タイムスタンプ</th><th>ログ詳細</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>{summary_html}"""


def _render_tools_section(report: SessionReport) -> str:
    tool_rows = ""
    for name, count in sorted(report.tools.tool_counts.items(), key=lambda x: -x[1]):
        tool_rows += f"<tr><td><code>{_esc(name)}</code></td><td>{count}</td></tr>"
    if not tool_rows:
        tool_rows = '<tr><td colspan="2" class="empty-msg">ツール使用なし</td></tr>'

    agg_rows = ""
    for agg in report.tools.bash_aggregation:
        sub_html = ""
        if agg.sub_commands:
            sub_items = ", ".join(
                f"{k}({v})"
                for k, v in sorted(agg.sub_commands.items(), key=lambda x: -x[1])
            )
            sub_html = f'<br><span class="meta-label">{_esc(sub_items)}</span>'
        agg_rows += f"""
        <tr>
            <td><code>{_esc(agg.base_command)}</code>{sub_html}</td>
            <td>{agg.count}</td>
        </tr>"""
    if not agg_rows:
        agg_rows = '<tr><td colspan="2" class="empty-msg">Bash 実行なし</td></tr>'

    bash_rows = ""
    for inv in report.tools.bash_invocations:
        status_cls = "failure" if inv.is_error else "success"
        badge_cls = "badge-failure" if inv.is_error else "badge-success"
        badge_label = "失敗" if inv.is_error else "成功"
        err_html = ""
        if inv.error_message:
            err_html = (
                f'<br><span class="meta-label">{_esc(inv.error_message[:120])}</span>'
            )
        log_link = f'<a class="log-link" href="javascript:void(0)" onclick="goToLogEntry(\'entry-{_esc(inv.entry_uuid)}\')">→ ログ詳細</a>'
        bash_rows += f"""
        <tr class="bash-row {status_cls}">
            <td><code>{_esc(inv.command[:200])}</code>{err_html}</td>
            <td><span class="badge {badge_cls}">{badge_label}</span></td>
            <td class="meta-label">{_esc(inv.source)}</td>
            <td class="meta-label">{_esc(inv.timestamp)}</td>
            <td>{log_link}</td>
        </tr>"""
    if not bash_rows:
        bash_rows = '<tr><td colspan="5" class="empty-msg">Bash 実行なし</td></tr>'

    return f"""
    <div class="card">
        <h2>ツール使用カウント</h2>
        <table>
            <thead><tr><th>ツール名</th><th>回数</th></tr></thead>
            <tbody>{tool_rows}</tbody>
        </table>
    </div>
    <div class="card">
        <h2>Bash コマンド集計</h2>
        <table>
            <thead><tr><th>ベースコマンド</th><th>回数</th></tr></thead>
            <tbody>{agg_rows}</tbody>
        </table>
    </div>
    <div class="card">
        <h2>Bash 実行一覧（時系列）</h2>
        <table>
            <thead><tr><th>コマンド</th><th>結果</th><th>出所</th><th>タイムスタンプ</th><th>ログ詳細</th></tr></thead>
            <tbody>{bash_rows}</tbody>
        </table>
    </div>"""


def _render_subagents_section(report: SessionReport) -> str:
    rows = ""
    for agent in report.sub_agents.agents:
        token_html = "―"
        if agent.token_usage:
            t = agent.token_usage
            cost_str = (
                f"${t.estimated_cost_usd:.4f}"
                if t.estimated_cost_usd is not None
                else "N/A"
            )
            token_html = f"入力:{t.input_tokens:,} / 出力:{t.output_tokens:,} / コスト:{cost_str}"
        subtype = _esc(agent.subagent_type or "―")
        log_link = f'<a class="log-link" href="javascript:void(0)" onclick="goToLogEntry(\'subagent-{_esc(agent.agent_id)}\')">→ ログ詳細</a>'
        rows += f"""
        <tr>
            <td class="meta-label">{_esc(agent.agent_id[:12])}…</td>
            <td><code>{_esc(agent.tool_name)}</code></td>
            <td>{subtype}</td>
            <td class="prompt-cell" title="{_esc(agent.prompt)}">{_esc(agent.prompt[:80])}</td>
            <td class="meta-label">{_esc(agent.launched_at)}</td>
            <td class="meta-label">{token_html}</td>
            <td>{log_link}</td>
        </tr>"""

    if not rows:
        rows = (
            '<tr><td colspan="7" class="empty-msg">サブエージェント起動なし</td></tr>'
        )

    return f"""
    <div class="card">
        <h2>サブエージェント一覧</h2>
        <table>
            <thead><tr>
                <th>エージェント ID</th><th>ツール</th><th>タイプ</th>
                <th>プロンプト</th><th>起動時刻</th><th>トークン使用量</th><th>ログ詳細</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""


def _render_thinking_section(report: SessionReport) -> str:
    if not report.thinking.has_thinking:
        return '<div class="card"><p class="empty-msg">thinking ブロックなし</p></div>'

    items = ""
    for entry in report.thinking.entries:
        if entry.content:
            summary_text = _esc(entry.content[:100].replace("\n", " ")) + "…"
            content_html = _esc(entry.content)
        else:
            summary_text = "（暗号化済み）"
            content_html = '<em style="color:var(--color-text-muted)">この思考ブロックは暗号化されています。</em>'
        log_link = f'<a class="log-link" href="javascript:void(0)" onclick="goToLogEntry(\'entry-{_esc(entry.message_uuid)}\')">→ ログ詳細</a>'
        items += f"""
    <details>
        <summary>
            <span>{summary_text}</span>
            <span class="meta-label">{_esc(entry.source)} / {_esc(entry.timestamp)}</span>
            {log_link}
        </summary>
        <div class="thinking-content">{content_html}</div>
    </details>"""

    return f'<div class="card"><h2>思考ログ一覧</h2>{items}</div>'


_TAB_DEFS = [
    ("tab-token", "トークン"),
    ("tab-skills", "スキル"),
    ("tab-tools", "ツール"),
    ("tab-subagents", "サブエージェント"),
    ("tab-thinking", "思考ログ"),
    ("tab-log", "ログ詳細"),
]


def _build_html(report: SessionReport, log_tab_html: str = "") -> str:
    tab_btns = "".join(
        f'<button class="tab-btn" data-tab="{tid}">{label}</button>'
        for tid, label in _TAB_DEFS
    )

    panels = {
        "tab-token": _render_token_section(report),
        "tab-skills": _render_skills_section(report),
        "tab-tools": _render_tools_section(report),
        "tab-subagents": _render_subagents_section(report),
        "tab-thinking": _render_thinking_section(report),
        "tab-log": log_tab_html,
    }
    tab_panels = "".join(
        f'<div id="{tid}" class="tab-panel">{panels[tid]}</div>' for tid, _ in _TAB_DEFS
    )

    session_json = _report_to_json(report)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Session Report: {_esc(report.session_id)}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
    <h1>Session Report</h1>
    <div class="session-meta">
        <span class="session-id">{_esc(report.session_id)}</span>
        {f'<span class="session-cwd">{_esc(report.cwd)}</span>' if report.cwd else ""}
        {f'<span class="session-time">{_esc(_fmt_timestamp(report.last_timestamp))}</span>' if report.last_timestamp else ""}
    </div>
</header>
<nav class="tab-bar">{tab_btns}</nav>
{tab_panels}
<script>
const SESSION_DATA = {session_json};
{_JS}</script>
</body>
</html>"""


class HtmlReporter:
    def generate(
        self,
        report: SessionReport,
        parsed: ParsedSession | None = None,
        agent_link_map: dict[str, str] | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """
        HTML ファイルを生成して output_path に書き込む。

        Args:
            report: セッションレポート（アナライザー出力集約）
            parsed: パース済みセッション（ログ詳細タブの生成に使用）
            agent_link_map: ToolUseBlock.id → サブエージェントキー のマッピング
            output_path: 出力先ファイルパス

        Returns: 書き込んだファイルの絶対パス
        Raises: ReportGenerationError (PermissionError 等のラッパー)
        """
        # 後方互換: 旧シグネチャ generate(report, output_path) を受け付ける
        if isinstance(parsed, Path):
            output_path = parsed
            parsed = None
            agent_link_map = None

        if output_path is None:
            raise ValueError("output_path は必須です")

        log_tab_html = ""
        if parsed is not None:
            log_tab_html = render_log_detail_tab(parsed, agent_link_map or {})

        html = _build_html(report, log_tab_html)
        try:
            output_path.write_text(html, encoding="utf-8")
        except OSError as exc:
            raise ReportGenerationError(f"Failed to write report: {exc}") from exc
        return output_path.resolve()
