# Technology Stack

## Architecture

パイプライン型: `LogDiscovery → LogParser → 5 Analyzers → HtmlReporter`
`SessionAnalyzer` がオーケストレーターとして各ステップを順次呼び出す。

## Core Technologies

- **Language**: Python 3.14
- **Runtime**: uv 0.9 / mise で管理
- **HTML Output**: バニラ JS + インライン CSS（外部依存なし）

## Key Libraries

標準ライブラリのみ（`json`, `pathlib`, `dataclasses`, `argparse`, `enum`）。
サードパーティ依存なし。dev ツールは `pytest`（テスト）、`ruff`（lint/format）、`ty`（型チェック）。

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
```

## Key Technical Decisions

- **外部依存ゼロ**: インストール不要でどの環境でも動作させるため標準ライブラリのみ使用
- **HTML にデータを埋め込む**: `SESSION_DATA = {...};` として JS オブジェクトをインライン定義し、file:// でも動作
- **サブエージェントログ**: メインセッションと同じパーサーを再利用し `agent_id` を付与して区別
