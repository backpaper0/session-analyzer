# Session Analyzer

Claude Code のセッションログを解析して、インタラクティブな HTML レポートを生成する Python ツール。

## 概要

セッション ID を指定するだけで、対象セッションのログファイルとサブエージェントのログを自動検出し、以下の情報を単一の HTML ファイルとして出力します。

- **トークン使用量・コスト推計** — モデル別の入出力トークン数と推定 USD コスト
- **スキル使用サマリー** — 使用されたスキルと起動方法（ユーザー起動 / LLM 自動起動）
- **ツール使用サマリー** — ツール呼び出し回数、Bash コマンド一覧とエラー内容
- **サブエージェントサマリー** — 起動されたサブエージェントとそのトークン使用量
- **思考ログビュー** — LLM の Thinking ブロックを時系列で確認（暗号化済みブロックも表示）
- **ログ詳細タブ** — 全会話ログをロール別に閲覧、各セクションからワンクリックでジャンプ可能

各サマリーセクションの行には「→ ログ詳細」リンクが付き、対応するログエントリへ直接ナビゲートできます。
1,000 件を超えるログは初期 200 件を表示し、残りは「さらに表示」ボタンで展開します。
長いコンテンツブロック（5 行以上）は自動的に折りたたまれます。

生成された HTML はブラウザで直接開くだけで動作します（HTTP サーバー不要）。

## インストール

```bash
# リポジトリをクローン後、uv で依存関係をセットアップ
git clone https://github.com/your-org/session-analyzer.git
cd session-analyzer
uv sync
```

## 使い方

```bash
# 基本: セッション ID を指定して実行
uv run python -m session_analyzer <session_id>

# 出力ファイルを指定
uv run python -m session_analyzer <session_id> -o report.html

# Claude 設定ディレクトリを明示的に指定
uv run python -m session_analyzer <session_id> --claude-dir /path/to/.claude
```

セッション ID は前方一致で検索されるため、先頭数文字の短縮形でも動作します。

### オプション

| オプション | 短縮形 | 説明 |
|---|---|---|
| `--output` | `-o` | 出力 HTML ファイルのパス（省略時: `session-{id}.html`）|
| `--claude-dir` | | Claude 設定ルートディレクトリ（省略時: `$CLAUDE_CONFIG_DIR` または `$HOME/.claude`）|
| `--help` | `-h` | ヘルプを表示 |

### 環境変数

| 変数名 | 説明 |
|---|---|
| `CLAUDE_CONFIG_DIR` | Claude 設定ルートディレクトリ（`--claude-dir` と同等）|

## ログファイルの場所

デフォルトでは `$HOME/.claude/projects/` 配下を再帰的に検索します。
サブエージェントのログは `{session_id}/subagents/agent-*.jsonl` から自動検出されます。

## 開発

```bash
# テスト実行
uv run pytest

# 詳細表示
uv run pytest -v
```

E2E テストはプロジェクトルートの `projects/` 配下にサンプルログが必要です。
存在しない場合は自動的にスキップされます。

## 動作環境

- Python 3.14+
- 外部ライブラリ依存なし（標準ライブラリのみ）
