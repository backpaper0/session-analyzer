# Research & Design Decisions

---
**Purpose**: Capture discovery findings, architectural investigations, and rationale that inform the technical design.

---

## Summary

- **Feature**: `session-analyzer`
- **Discovery Scope**: New Feature (greenfield)
- **Key Findings**:
  - JSONL ファイルは1行1 JSON オブジェクト。`type` フィールドで `user` / `assistant` / `progress` / `file-history-snapshot` を区別する。
  - サブエージェントログは別ファイル（`{session_id}/subagents/agent-{agentId}.jsonl`）に格納され、`isSidechain: true` かつ `agentId` フィールドを持つ。
  - HTML を `file://` プロトコルで動作させるには外部リソース参照（CDN）を使用できないため、Vanilla JS + インライン埋め込みが最適解。
  - Python 標準ライブラリのみで実装可能（`json`, `pathlib`, `argparse`, `dataclasses`）。外部依存ゼロで配布が容易。

---

## Research Log

### JSONL ログ形式の調査

- **Context**: 解析対象のデータ構造を正確に把握するため、サンプルログを直接読み込んだ。
- **Findings**:
  - トップレベルフィールド: `type`, `uuid`, `parentUuid`, `sessionId`, `timestamp`, `message`, `isMeta`, `agentId`, `isSidechain`
  - `assistant` type の `message.usage`: `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `cache_creation.ephemeral_*`
  - `message.content` は文字列または配列（`text` / `tool_use` / `thinking` / `tool_result` ブロック）
  - スキル検出: `user` type メッセージの `content` 文字列中の `<command-name>` タグ。`isMeta: true` は LLM 自動起動、それ以外はユーザー起動。
  - `progress` type はサブエージェントの進捗を含むが、実際のサブエージェントメッセージは別 JSONL ファイルに存在する。
- **Implications**: パーサーは `type` による分岐処理が必要。`progress` type は集計から除外し、サブエージェントログを別途解析する。

### ファイル探索パターンの調査

- **Context**: セッション ID からファイルパスを特定する方法を確認。
- **Findings**:
  - 主ログ: `$HOME/.claude/projects/{encoded_path}/{session_id}.jsonl`
  - サブエージェントログ: `$HOME/.claude/projects/{encoded_path}/{session_id}/subagents/agent-{agentId}.jsonl`
  - `{encoded_path}` はプロジェクトディレクトリパスをハイフン区切りにエンコードしたもの（例: `-Users-urgm-src-claude-plugins`）
  - 環境変数 `CLAUDE_CONFIG_DIR` でルートを変更可能
- **Implications**: セッション ID の完全/部分マッチで `*.jsonl` ファイルを再帰探索する実装が必要。

### HTML `file://` 対応の制約調査

- **Context**: HTTPサーバー不要でブラウザ表示する制約の技術的実現方法を検討。
- **Findings**:
  - `file://` プロトコルでは CORS 制限により外部 JS/CSS ファイルの fetch が不可
  - CDN 経由の React/Vue はネットワーク不要だが、オフライン環境では動作しない
  - Vanilla JS をインラインで埋め込めば制約なし
  - データを `<script>` タグ内の JSON 変数として埋め込む手法が標準的
- **Implications**: HTML テンプレートに CSS・JS・データをすべてインライン埋め込みするアーキテクチャを採用。

### モデル料金データ

- **Context**: トークンコスト推定に必要なモデル別単価を把握。
- **Findings**（2026年3月時点の公開情報に基づく概算）:

  | モデル | Input ($/MTok) | Output ($/MTok) | Cache Write ($/MTok) | Cache Read ($/MTok) |
  |--------|---------------|-----------------|---------------------|---------------------|
  | claude-opus-4-6 | 15.00 | 75.00 | 18.75 | 1.50 |
  | claude-sonnet-4-6 | 3.00 | 15.00 | 3.75 | 0.30 |
  | claude-haiku-4-5-20251001 | 0.80 | 4.00 | 1.00 | 0.08 |

- **Implications**: 料金テーブルをコード内に定数として保持し、未知モデルは N/A と表示。

---

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Pipeline / ETL | 探索 → 解析 → 変換 → 出力の直列パイプライン | シンプル、テスト容易、段階ごとに独立したテスト可能 | 並列処理なし（今回は不要） | データ量が少ないため十分 |
| イベント駆動 | ログエントリをイベントとしてアナライザーに通知 | 拡張性が高い | 複雑すぎる | 過剰設計 |
| プラグインアーキテクチャ | アナライザーをプラグインとして動的ロード | 柔軟性が高い | 実装コスト大 | スコープ外 |

**選択**: Pipeline / ETL パターン

---

## Design Decisions

### Decision: HTML 出力に Vanilla JS を採用

- **Context**: `file://` プロトコルでの動作要件と、外部ライブラリへの依存ゼロ要件
- **Alternatives Considered**:
  1. React (バンドル済みインライン埋め込み) — ビルドステップ不要にできるが複雑
  2. Vue CDN — ネットワーク接続が必要になりオフライン非対応
  3. Vanilla JS — ビルド不要、制約なし、完全自己完結
- **Selected Approach**: Vanilla JS + インライン CSS + JSON データ埋め込み
- **Rationale**: 追加依存ゼロ、`file://` 完全対応、Python のみで HTML を生成できる
- **Trade-offs**: React より UI の記述量は増えるが、今回の規模では問題なし

### Decision: Python 標準ライブラリのみ使用

- **Context**: エージェントスキルから呼び出されるツールとして、インストール手順の簡素化が重要
- **Alternatives Considered**:
  1. `rich` ライブラリ — ターミナル出力向け、HTML 生成には不要
  2. `jinja2` — テンプレートエンジン、外部依存になる
  3. 標準ライブラリのみ — `json`, `pathlib`, `argparse`, `dataclasses`
- **Selected Approach**: 標準ライブラリのみ。HTML テンプレートは Python 文字列で管理。
- **Rationale**: `uv run` や `python` 直接実行で動作する。依存関係管理不要。
- **Trade-offs**: テンプレート管理が煩雑になる可能性があるが、HTML 生成は一度きりなので許容範囲

### Decision: Bash コマンド集計のサブコマンド展開対象を設定ファイルではなく定数で管理

- **Context**: `git`, `docker`, `mvn`, `npm`, `uv` のサブコマンド展開が要件
- **Selected Approach**: ソースコード内の `frozenset` 定数として管理
- **Rationale**: 要件が固定されており、設定ファイルによる拡張は過剰設計

---

## Risks & Mitigations

- JSONL フォーマットの非互換変更 — Claude Code のバージョン更新で構造が変わる可能性。ログパーサーを防御的に実装し、未知フィールドを無視する設計とする。
- 大規模セッションでのメモリ使用量 — 巨大な JSONL ファイルをすべてメモリに展開すると問題になりうる。行単位ストリーミング読み込みで対処する。
- `thinking` ブロックの `signature` フィールド — 暗号化済みシグネチャのため内容解析は不要。表示用にそのまま保持する。

---

## References

- Claude Code ドキュメント（ログ形式は公式ドキュメント外のため、サンプルログを正とする）
- Anthropic 料金ページ（モデル単価の参照元）
