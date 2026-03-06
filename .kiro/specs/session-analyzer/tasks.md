# 実装計画: Session Analyzer

## タスク一覧

- [ ] 1. プロジェクト基盤とドメインモデルの整備
- [x] 1.1 パッケージ構造とエントリポイントのセットアップ
  - `session_analyzer` パッケージとして `python -m session_analyzer` で起動できるようにする
  - パッケージ初期化ファイルと `__main__.py` を用意する
  - `mise.toml` にツール設定（Python バージョン等）を追加する
  - _Requirements: 8.1_

- [x] 1.2 ドメインモデルの定義
  - ログエントリを表すデータクラス群（`UsageData`, `TextBlock`, `ToolUseBlock`, `ThinkingBlock`, `ToolResultBlock`, `AssistantEntry`, `UserEntry`）を定義する
  - セッション全体を保持する `ParsedSession` および `SessionFiles` データクラスを定義する
  - 各アナライザーの出力型（`TokenReport`, `SkillReport`, `ToolReport`, `SubAgentReport`, `ThinkingReport`, `SessionReport`）を定義する
  - カスタム例外（`SessionNotFoundError`, `AmbiguousSessionError`, `ReportGenerationError`）を定義する
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

- [ ] 2. ログファイル探索機能の実装
- [x] 2.1 JSONL ファイルの再帰探索と環境変数対応
  - `$HOME/.claude/projects/` 配下を再帰的にスキャンして `*.jsonl` ファイルを列挙する
  - 環境変数 `CLAUDE_CONFIG_DIR` が設定されていればそちらをルートディレクトリとして使用する
  - ファイルが見つからない場合は `SessionNotFoundError` を raise する
  - _Requirements: 1.2, 1.3, 1.5_

- [x] 2.2 セッション ID のマッチングとサブエージェントファイルの探索
  - 完全一致を優先し、次いで prefix マッチでセッション JSONL を特定する
  - 複数ファイルがマッチした場合は `AmbiguousSessionError` を raise する
  - メインファイル特定後、`{session_dir}/{session_id}/subagents/agent-*.jsonl` パターンでサブエージェントファイルを探索する
  - 探索結果を `SessionFiles` として返す
  - _Requirements: 1.4, 1.6_

- [ ] 3. ログパーサーの実装
- [x] 3.1 JSONL 行単位ストリーミング解析
  - ファイルを行単位で読み込み、各行を JSON としてパースする
  - `type` フィールドで `assistant` / `user` / その他を振り分け、各型のデータクラスに変換する
  - `content` フィールドが配列の場合に各ブロック（`text`, `tool_use`, `thinking`, `tool_result`）を識別してパースする
  - 不正 JSON や未知フィールドは警告を stderr に出力してスキップする（処理継続）
  - _Requirements: 1.4_

- [x] 3.2 メインセッションとサブエージェントの統合
  - メイン JSONL とサブエージェント JSONL 群をそれぞれ解析し、`ParsedSession` にまとめる
  - サブエージェントログは `agentId` をキーとして `subagent_entries` に格納する
  - _Requirements: 1.4, 5.4_

- [ ] 4. アナライザー群の実装
- [x] 4.1 (P) トークン使用量とコスト推定の集計
  - `assistant` メッセージの `usage` フィールドからトークン数（入力・出力・キャッシュ作成・キャッシュ読み込み）を集計する
  - メイン + 全サブエージェントログを対象とし、モデル別に集計する
  - 既知モデルの料金テーブル（`claude-opus-4-6` / `claude-sonnet-4-6` / `claude-haiku-4-5-20251001`）を定数として保持し、USD コストを計算する
  - 未知モデルはトークン数のみ表示し、コストは `None` として扱う
  - 全モデルの合計トークン数・推定コストを `TokenReport.total` として集計する
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4.2 (P) スキル使用サマリーの解析
  - `user` メッセージのコンテンツ文字列から `<command-name>` タグを正規表現で抽出する
  - `isMeta: true` のメッセージを「LLM自動起動」、それ以外を「ユーザー起動（スラッシュコマンド）」として分類する
  - スキル名・起動方法・タイムスタンプ・UUID を `SkillInvocation` として記録する
  - 時系列順に並べたリストとスキル名別の集計カウントを `SkillReport` として返す
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4.3 (P) ツール使用サマリーと Bash コマンド集計
  - `assistant` メッセージの `tool_use` ブロックをツール名別にカウントする（メイン + サブエージェント含む）
  - `Bash` ツールの全実行を時系列一覧として保持し、対応する `tool_result` と紐づけて成功/エラーを判定する
  - `shlex.split` でコマンドをトークン分割し、先頭トークン（ベースコマンド）を抽出して使用回数降順の集計を作成する
  - `git`, `docker`, `mvn`, `npm`, `uv` については2番目のトークン（サブコマンド）でさらに詳細集計する
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

- [x] 4.4 (P) サブエージェント情報の集計
  - `assistant` メッセージで `name` が `Task` または `Agent` の `tool_use` ブロックを検出する
  - エージェント ID・ツール名・`subagent_type`・プロンプト・タイムスタンプを `SubAgentInfo` として記録する
  - 対応するサブエージェントログが存在する場合は、そのトークン使用量も `TokenAnalyzer` の部分集計として保持する
  - 起動順に並べた一覧を `SubAgentReport` として返す
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 4.5 (P) 思考ログの抽出と整理
  - `assistant` メッセージの `content` 配列から `type: "thinking"` ブロックを全て抽出する（メイン + サブエージェント含む）
  - 各エントリに紐づく `message_uuid`・タイムスタンプ・出所（メインまたはエージェント ID）を記録する
  - 時系列順に並べた `ThinkingReport` を返す
  - `thinking` ブロックが0件の場合は `has_thinking: false` として返す
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [ ] 5. HTML レポーターの実装
- [x] 5.1 HTML テンプレートとデザイン基盤の構築
  - タブナビゲーション（トークン / スキル / ツール / サブエージェント / 思考ログ）を持つ HTML 骨格を作成する
  - パステルカラーパレットを CSS カスタムプロパティで定義し、モダンなレイアウト（Flexbox/Grid）を適用する
  - CSS と JavaScript を `<style>` / `<script>` タグにすべてインライン埋め込みし、外部リソース参照をゼロにする
  - `file://` プロトコルでタブ切り替えが動作することを確認できる最小限の JS を実装する
  - _Requirements: 7.1, 7.2, 7.3, 7.6_

- [x] 5.2 各セクションのデータ描画実装
  - `SessionReport` を JSON 直列化してスクリプトタグに埋め込み、JS がそれを読み取ってページを描画する構成にする
  - トークンセクション：モデル別テーブルと合計、コスト（または N/A）を表示する
  - スキルセクション：スキル名・起動方法・時系列一覧を表示する
  - ツールセクション：ツール使用カウント一覧・Bash コマンド集計（サブコマンド展開含む）・全 Bash 実行一覧（成功はパステルグリーン、失敗はパステルレッドで色分け）を表示する
  - サブエージェントセクション：エージェント一覧（プロンプト・タイプ・トークン量）を表示する
  - 思考ログセクション：`<details>/<summary>` 要素を使って各エントリを折りたたみ表示する
  - _Requirements: 7.4, 7.5, 7.7, 4.5, 5.2, 5.3, 6.2, 6.3, 6.4_

- [ ] 6. CLI インターフェースとパイプライン統合
- [x] 6.1 argparse による CLI 実装
  - セッション ID を位置引数として受け取る `argparse` の設定を実装する
  - `--output` / `-o`（出力ファイルパス）、`--claude-dir`（ルートディレクトリ上書き）オプションを追加する
  - `--output` 省略時のデフォルトファイル名を `session-{session_id}.html` とする
  - `--help` で使い方を表示し、正常終了時は HTML パスを stdout に出力して exit code 0 で終了する
  - エラー時は説明メッセージを stderr に出力して exit code 1 で終了する
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 6.2 SessionAnalyzer オーケストレーターによるパイプライン統合
  - `LogDiscovery` → `LogParser` → 5 アナライザー → `HtmlReporter` の順で呼び出す `SessionAnalyzer` を実装する
  - 各カスタム例外を CLI レイヤーで捕捉し、適切なエラーメッセージに変換して stderr に出力する
  - 全コンポーネントを接続し、サンプルログを対象にパイプライン全体がエラーなく動作することを確認する
  - _Requirements: 1.1, 1.5, 8.5, 8.6_

- [ ] 7. 統合テストと動作確認
- [x] 7.1 サンプルログを使ったエンドツーエンドの動作確認
  - `projects/` 配下のサンプルログを対象に `python -m session_analyzer {session_id}` を実行し、HTML ファイルが生成されることを確認する
  - サブエージェントあり・なし両方のセッションで正しく解析されることを確認する
  - 生成された HTML をブラウザで開き、全タブの表示・折りたたみ操作が `file://` プロトコルで正常に動作することを確認する
  - `--output` オプションで指定パスへの出力が機能することを確認する
  - _Requirements: 1.1, 1.2, 1.4, 7.1, 7.2, 7.3, 8.1, 8.5_

- [x] 7.2 アナライザー単体テスト
  - `LogDiscovery`: 完全一致・prefix マッチ・未発見・複数マッチのケースをテストする
  - `TokenAnalyzer`: 既知モデル・未知モデル・複数モデル混在のコスト計算をテストする
  - `ToolAnalyzer`: Bash コマンド集計（成功・失敗・サブコマンド展開対象コマンド）をテストする
  - `SkillAnalyzer`: `isMeta` の有無によるスキル分類をテストする
  - _Requirements: 1.5, 1.6, 2.3, 2.6, 3.2, 3.3, 4.4, 4.7_
