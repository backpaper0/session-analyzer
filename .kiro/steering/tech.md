# Technology Stack

## Architecture

パイプライン型: `LogDiscovery → LogParser → 5 Analyzers → HtmlReporter`
`SessionAnalyzer` がオーケストレーターとして各ステップを順次呼び出す。

## Core Technologies

- **Language**: Python 3.14
- **Runtime**: uv 0.9 / mise で管理
- **HTML Output**: バニラ JS + インライン CSS（外部依存なし）

## Key Libraries

- **Runtime 依存**: `markdown>=3.7`（TextBlock コンテンツの HTML レンダリング用）
- **標準ライブラリ**: `json`, `pathlib`, `dataclasses`, `argparse`, `enum`
- **Dev ツール**: `pytest`（テスト）、`ruff`（lint/format）、`ty`（型チェック）

## Development Standards

### Type Safety
- 全モジュールで `from __future__ import annotations` を使用
- `dataclass` / `StrEnum` によるドメインモデル定義
- Union 型は `X | Y` 記法（Python 3.10+）

### Code Quality
- コメント・docstring は日本語

### Testing
- `pytest` + `tmp_path` フィクスチャ
- E2E テストは `projects/` 配下のサンプルログを使用（存在しない場合は skip）
- アナライザー単体テストは `ParsedSession` を直接構築してテスト

## Development Environment

### Required Tools
- Python 3.14、uv 0.9（mise で管理）

### Common Commands
```bash
# 実行: uv run python -m session_analyzer <session_id>
# テスト: uv run pytest
# テスト（詳細）: uv run pytest -v
# 品質チェック（format/lint/型）: mise run check
# 自動修正: mise run fix
```

## Key Technical Decisions

- **最小外部依存**: Runtime 依存は `markdown` のみ。標準ライブラリで賄える機能はサードパーティを追加しない
- **HTML にデータを埋め込む**: `SESSION_DATA = {...};` として JS オブジェクトをインライン定義し、file:// でも動作
- **Script 早期終了の防止**: `reporter.py` で JSON 文字列内の `</` を `<\/` にエスケープし、`<script>` 要素が誤って閉じられないよう対策
- **Markdown レンダリングの XSS 防止**: `log_renderer.py` の `_render_markdown()` は `<` と `&` をエスケープしてから `markdown` ライブラリに渡す（`>` はエスケープしない：blockquote 構文を保持するため）
- **サブエージェントログ**: メインセッションと同じパーサーを再利用し `agent_id` を付与して区別
