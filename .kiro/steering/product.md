# Product Overview

Session Analyzer は、Claude Code のセッションログを解析・可視化する Python ツール。
セッション ID を引数に受け取り、単一の自己完結型 HTML レポートを生成する。

## Core Capabilities

- **ログ探索**: `$HOME/.claude/projects/` 配下からセッション ID（完全一致・前方一致）でメインログとサブエージェントログを自動検出
- **多次元解析**: トークン消費量・コスト推計、スキル使用履歴、ツール呼び出し集計、サブエージェント起動状況、Thinking ブロック抽出の 5 軸分析
- **HTML レポート生成**: 外部サーバー不要で `file://` 直接表示できる、インライン CSS/JS 埋め込みの単一 HTML ファイルとして出力

## Target Use Cases

- Claude Code エージェントスキルからの自動呼び出し（`python -m session_analyzer <session_id>`）
- 開発者がセッション後に手動実行し、API コストや作業内容を振り返る

## Value Proposition

セッション ID だけで即座に解析を開始でき、生成された HTML をブラウザで開くだけで
トークン消費・ツール使用・思考プロセスをインタラクティブに確認できる。
