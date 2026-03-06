# Research & Design Decisions: log-detail-view

---
**Purpose**: ディスカバリーフェーズの調査結果と設計判断の根拠を記録する。

---

## Summary
- **Feature**: `log-detail-view`
- **Discovery Scope**: Extension（既存システムへの機能追加）
- **Key Findings**:
  - `ParsedSession` はすでに全ログエントリ（main + subagent）を保持しており、パーサー変更は不要
  - `reporter.py` のタブ構造（`_TAB_DEFS` + `_build_html`）は新タブ追加のための拡張ポイントとして機能する
  - サブエージェントの ToolUseBlock.id（`toolu_xxx`）とサブエージェントファイル由来のキー（`abc123`）は異なる ID 体系であり、現在は位置ベースマッチングで対応している

## Research Log

### サブエージェント ID マッピング調査

- **Context**: 要件 3（起動箇所リンク）の実現にあたり、メインログの Agent/Task ToolUseBlock と、どのサブエージェントログが対応するかを特定する必要があった
- **Sources Consulted**: `session_analyzer/analyzers/subagent.py`, `session_analyzer/discovery.py`, `session_analyzer/models.py`
- **Findings**:
  - `ToolUseBlock.id` は Claude API が割り振るツール使用 ID（例: `toolu_01XYZ`）
  - サブエージェントファイル名は `agent-{subagent_session_id}.jsonl` 形式で、セッション ID は別体系
  - `discovery.py` では `sorted(subagents_dir.glob("agent-*.jsonl"))` でアルファベット順にファイルを収集
  - `subagent.py` の既存マッチングは `enumerate(task_calls)` と `sub_token_usages[i]` による位置ベース
- **Implications**:
  - 「N 番目の Agent/Task 呼び出し → N 番目のサブエージェントファイル（ソート順）」という位置ベースマッチングを採用
  - 完全な ID ベースマッチングは実ログのファイル命名規則の詳細調査が必要（将来の改善点）

### 既存 HTML レンダリングパターン調査

- **Context**: 新規ログレンダリングコンポーネントが既存のコーディングパターンと整合するかを確認
- **Sources Consulted**: `session_analyzer/reporter.py`
- **Findings**:
  - HTML は Python 側のサーバーサイドレンダリング（文字列結合）で生成している
  - `_esc(text)` によるエスケープ関数が定義済み
  - `<details>/<summary>` パターンが ThinkingBlock の折りたたみ表示に既存利用されている
  - `SESSION_DATA = {...}` として `SessionReport` を JSON インライン化する形式
  - 外部 CSS/JS ライブラリへの依存はゼロ（バニラ JS + インライン CSS のみ）
- **Implications**:
  - ログレンダリングも同一パターン（Python 文字列生成 + `_esc`）に従う
  - ThinkingBlock の `<details>` パターンを ToolUseBlock 入力表示にも流用可能
  - `SESSION_DATA` には生ログを追加しない（HTML サイズ抑制）

### 大量エントリ時のパフォーマンス調査

- **Context**: 要件 4.5「1,000 件超のエントリに対するパフォーマンス維持」の設計
- **Sources Consulted**: 既存 HTML 生成コード、Web 標準
- **Findings**:
  - 仮想スクロールは vanilla JS での実装が複雑
  - ページネーションは JS で実装可能だが UX に難あり
  - 最もシンプルな実装: 全 HTML を Python で生成し、スクロール可能なコンテナに収める
  - CSS `max-height` + `overflow-y: auto` でファーストビューのレンダリングコストを下げる
  - JS の「最初の N 件を表示、残りを遅延表示」パターンは `display:none` → `display:block` 切り替えで実現可能（DOM は事前生成、表示制御のみ JS）
- **Implications**:
  - 全エントリを Python 側で HTML として生成（DOM 事前構築）
  - 1,000 件超の場合のみ、JS による「最初の 200 件表示 + 残り表示ボタン」を適用
  - コンテナには `max-height: 600px; overflow-y: auto` を設定しスクロール可能に

---

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| A: reporter.py を直接拡張 | `reporter.py` にログレンダリング関数を追加 | 新規ファイルなし | reporter.py が 800 行超に膨張、テストが難化 | 採用しない |
| B: log_renderer.py を新規作成（推奨） | `session_analyzer/log_renderer.py` でログレンダリングを分離 | 単一責務、独立テスト可能、reporter.py の肥大化回避 | ファイル数が 1 増加 | **採用** |
| C: SESSION_DATA へのログデータ追加 + JS レンダリング | Python でデータを JSON 化し、JS でレンダリング | 動的フィルタリングが容易 | HTML ファイルが大幅に大きくなる、JS 実装が複雑 | 採用しない |

---

## Design Decisions

### Decision: `HtmlReporter.generate()` シグネチャ変更方法

- **Context**: `HtmlReporter` は現在 `SessionReport` のみを受け取るが、ログ詳細ビューには `ParsedSession` のデータが必要
- **Alternatives Considered**:
  1. `generate(report, parsed, output_path)` — `ParsedSession` を追加引数として渡す
  2. `SessionReport` に `parsed: ParsedSession` フィールドを追加
  3. 新たな `FullReport(report, parsed)` ラッパーを定義
- **Selected Approach**: オプション 1（`parsed: ParsedSession` を追加引数として渡す）
- **Rationale**: `SessionReport` はアナライザーの出力集約モデルであり、生ログデータを混入させるべきではない。ラッパーは過剰設計。追加引数が最もシンプル。
- **Trade-offs**: 呼び出し側（`session_analyzer.py`）の変更が必要だが影響範囲は最小
- **Follow-up**: テスト側でも `generate()` 呼び出しを更新する必要がある

### Decision: サブエージェントリンクのマッピング戦略

- **Context**: メインログの Agent/Task 呼び出し箇所からサブエージェント詳細ビューへリンクする際の対応付け
- **Alternatives Considered**:
  1. 位置ベースマッチング（N 番目の Agent 呼び出し → N 番目のサブエージェントファイル）
  2. タイムスタンプベースマッチング（起動時刻に最も近い初回エントリを持つサブエージェント）
  3. ID ベースマッチング（ToolUseBlock.id とファイル名の直接対応）
- **Selected Approach**: オプション 1（位置ベースマッチング）、`session_analyzer.py` で `agent_link_map: dict[str, str]` を構築
- **Rationale**: 既存の `SubAgentAnalyzer` が同一のアプローチを使用しており、一貫性がある。ID ベースには実ログの命名規則調査が必要で現時点では不確実。
- **Trade-offs**: サブエージェントが途中でキャンセルされた場合など、順序がずれるケースでリンクが誤る可能性あり
- **Follow-up**: 実際のログを確認し、ID ベースマッチングへの移行が可能か評価する

### Decision: ログレンダリングモジュールの責務範囲

- **Context**: `log_renderer.py` が担う責務の範囲
- **Alternatives Considered**:
  1. `render_log_detail_tab(parsed, agent_link_map) -> str` の 1 関数のみ公開
  2. 複数の公開関数（main/subagent それぞれ）
- **Selected Approach**: オプション 1（1 つの公開インターフェース）、内部は private 関数で分割
- **Rationale**: `reporter.py` からは 1 関数呼び出しで完結させることで結合度を最小化
- **Trade-offs**: 内部テストには private 関数を直接テストする工夫が必要

---

## Risks & Mitigations

- 位置ベース ID マッピングの誤対応 — ドキュメントに既知の制限として記載、将来的に ID ベース移行を検討
- 大量エントリ時の HTML ファイルサイズ増大 — 1,000 件を超える場合の JS 遅延表示で初期ロードを軽減
- `reporter.py` の `_build_html` シグネチャ変更による既存テストへの影響 — `session_analyzer.py` と `reporter.py` のテストを同時に更新する

## References

- 既存実装: `session_analyzer/reporter.py` — タブ構造・CSS・JS パターンの参照元
- 既存実装: `session_analyzer/analyzers/subagent.py` — 位置ベースマッチングの参照元
- 既存実装: `session_analyzer/discovery.py` — サブエージェントファイルのソート順の確認元
