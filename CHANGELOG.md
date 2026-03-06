# Changelog

このプロジェクトのすべての注目すべき変更点を記録します。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準拠し、
このプロジェクトは [Semantic Versioning](https://semver.org/lang/ja/) に従います。

## [0.1.0] - 2026-03-07

ファーストリリース。

Claude Code のセッションログを解析し、トークン使用量・コスト推計、スキル/ツール/サブエージェントサマリー、ログ詳細タブを含むインタラクティブな HTML レポートを生成する。

## [0.2.0] - 2026-03-07

### 追加

- ログ詳細タブ — 全会話ログをロール別に閲覧し、各サマリーセクションからワンクリックでジャンプ可能
- セッションヘッダーに作業ディレクトリ（cwd）と最終タイムスタンプを表示
- 各サマリー行に「→ ログ詳細」ナビゲーションリンクを追加
- 長いコンテンツブロック（5 行以上）を自動折りたたみ
- TextBlock コンテンツを Markdown レンダリング

### 修正

- 暗号化済み thinking ブロックにプレースホルダーを表示し、details 展開の不具合を修正
- `SESSION_DATA` に `</script>` が含まれる場合に script 要素が早期終了する問題を修正
- 推定コスト合計で N/A を無視し、既知モデル分のみ集計するよう修正

[0.1.0]: https://github.com/backpaper0/session-analyzer/releases/tag/v0.1.0
[0.2.0]: https://github.com/backpaper0/session-analyzer/compare/v0.1.0...v0.2.0
