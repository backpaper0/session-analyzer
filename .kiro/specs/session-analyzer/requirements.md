# 要件ドキュメント

## プロジェクト概要 (Input)
Claude Codeのセッションログを解析して可視化するPythonプログラム。

### 前提

セッションログはデフォルトだと`$HOME/.claude/projects/`配下にある。
ルート(`$HOME/.claude`)は環境変数で変更可能。

このPythonプログラムはClaude Codeのエージェントスキルから呼び出されることを想定している。

### 要件

セッションIDを引数に取り、そのセッションのログファイルと関連するサブエージェントのログファイルを特定し、解析する。

主な欲しい機能:
- 入力トークン数と出力トークン数を表示。あとできれば金額を表示
- 使用されたスキルと起動方法のサマリー。起動方法はLLMによって自動的に起動される場合とスラッシュコマンドでユーザーが明示的に起動する場合がある
- 使用されたツールのサマリー。Bashツールで実行したコマンドがエラーになった場合はエラーの内容(エラーメッセージ)を確認したい
- 使用されたサブエージェントのサマリー
- LLMの思考ログを確認できるビュー

可視化のアウトプットは1つのHTMLファイルとしたい。
また可能であればHTTPサーバーを必要とせず、HTMLファイルをWebブラウザで開くだけで内容を確認できるようにしたい。

可視化の技術スタック、つまりHTML側のスタックにこだわりはないためReactのようなSPAライブラリを使用してもよいしバニラJSで実現してもどちらでも良い。

見栄えはモダンかつかわいく仕上げてほしい。
色合いはパステルカラーが好ましい。

### その他、参考情報

セッションログのサンプルは`projects/`配下に置いたので参考にすること。

---

## Requirements

### イントロダクション

本ドキュメントは、Claude Code のセッションログを解析・可視化する Python プログラム「Session Analyzer」の要件を定義する。本プログラムは Claude Code のエージェントスキルから呼び出され、指定されたセッションの活動状況をインタラクティブな HTML レポートとして出力する。

---

### 要件 1: ログファイルの探索と特定

**目的:** 開発者として、セッション ID を指定するだけで対象のログファイルが自動的に特定されることで、手動でファイルパスを調べる手間なくセッション解析を開始できる。

#### 受け入れ基準

1. The Session Analyzer shall accept a session ID as a command-line argument.
2. When a session ID is provided, the Session Analyzer shall search for the corresponding JSONL file under `$HOME/.claude/projects/` by recursively scanning all subdirectories.
3. Where the environment variable `CLAUDE_CONFIG_DIR` is set, the Session Analyzer shall use that value as the root directory instead of `$HOME/.claude`.
4. When a main session file is found, the Session Analyzer shall also discover all associated sub-agent JSONL files located under `{session_id}/subagents/` relative to the session file.
5. If the specified session ID does not match any JSONL file, the Session Analyzer shall output a clear error message and exit with a non-zero status code.
6. The Session Analyzer shall support partial session ID matching (prefix match) to allow convenient short-form input.

---

### 要件 2: トークン使用量と推定コストの集計

**目的:** 開発者として、セッション全体のトークン使用量と推定コストを確認することで、API 利用費用の把握とコスト最適化の判断ができる。

#### 受け入れ基準

1. The Session Analyzer shall aggregate input token counts and output token counts from all `assistant` type messages in the session log (including sub-agent logs).
2. The Session Analyzer shall separately count cache-related tokens: `cache_creation_input_tokens` and `cache_read_input_tokens`.
3. Where pricing data is available for the model name recorded in the log, the Session Analyzer shall calculate and display the estimated cost in USD.
4. The Session Analyzer shall display token usage broken down by model (e.g., claude-opus-4-6, claude-haiku-4-5) when multiple models are used within a session.
5. The Session Analyzer shall display aggregated totals across all models as a summary.
6. If cost estimation is not available for a given model, the Session Analyzer shall display token counts only and indicate that cost data is unavailable.

---

### 要件 3: スキル使用サマリー

**目的:** 開発者として、セッション中にどのスキルが何回・どのような経緯で起動されたかを確認することで、エージェントの動作パターンを理解できる。

#### 受け入れ基準

1. The Session Analyzer shall identify skill invocations from `user` type messages where the content contains `<command-name>` tags.
2. When a skill is invoked via a slash command in the user message (type `user`, not `isMeta: true` system-generated), the Session Analyzer shall classify it as "ユーザー起動（スラッシュコマンド）".
3. When a skill is invoked via a system-generated message (type `user`, `isMeta: true`), the Session Analyzer shall classify it as "LLM自動起動".
4. The Session Analyzer shall display a summary listing each skill name, the number of invocations, and the invocation method for each occurrence.
5. The Session Analyzer shall display skill invocations in chronological order within the summary.

---

### 要件 4: ツール使用サマリーとエラー確認

**目的:** 開発者として、セッション中に使われたツールの種類と回数を確認し、Bash ツールで実行されたすべてのコマンドと特にエラーの内容を把握することで、エージェントの作業内容とトラブルを振り返ることができる。

#### 受け入れ基準

1. The Session Analyzer shall identify all tool use blocks (type `tool_use`) from `assistant` messages and aggregate them by tool name.
2. The Session Analyzer shall display a summary showing each tool name and its invocation count.
3. The Session Analyzer shall display a list of all `Bash` tool invocations, showing the executed command and its exit status (success or error), regardless of whether the command succeeded or failed.
4. When a `Bash` tool invocation is followed by a `tool_result` with `is_error: true`, the Session Analyzer shall additionally display the error message content alongside the command.
5. The Session Analyzer shall visually distinguish successful Bash commands from failed ones (e.g., using different colors or icons) in the HTML report.
6. The Session Analyzer shall aggregate Bash commands by their base command name (the first token of the command string) and display a ranked summary of how many times each command was used (e.g., `ls: 5回`, `git: 8回`).
7. When any of the following commands appears in the aggregated results — `git`, `docker`, `mvn`, `npm`, `uv` — the Session Analyzer shall further break down their usage by sub-command (e.g., `git commit: 3回`, `docker run: 2回`, `npm install: 1回`).
8. The Session Analyzer shall display the tool usage summary including sub-agent tool usage.

---

### 要件 5: サブエージェントサマリー

**目的:** 開発者として、セッション中に起動されたサブエージェントの概要を確認することで、エージェントの並列処理やタスク委譲の状況を把握できる。

#### 受け入れ基準

1. The Session Analyzer shall identify sub-agent invocations from `assistant` messages where a tool use block has `name: "Task"` or `name: "Agent"`.
2. The Session Analyzer shall display a list of sub-agents, showing the agent ID, the tool type used to launch it, and the prompt or description provided.
3. The Session Analyzer shall display sub-agent type (e.g., `subagent_type` value such as "Explore") when available.
4. The Session Analyzer shall show per-sub-agent token usage when the corresponding sub-agent log file is available.
5. The Session Analyzer shall display sub-agents in the order they were launched within the session.

---

### 要件 6: 思考ログビュー

**目的:** 開発者として、LLM の思考プロセス（thinking ブロック）をセッション時系列に沿って確認することで、エージェントの意思決定過程を深く理解できる。

#### 受け入れ基準

1. The Session Analyzer shall extract all `thinking` type content blocks from `assistant` messages in both the main session and sub-agent logs.
2. The Session Analyzer shall display thinking blocks in a dedicated collapsible view, organized chronologically.
3. When a thinking block is displayed, the Session Analyzer shall show the associated message UUID and timestamp for traceability.
4. The Session Analyzer shall allow users to expand or collapse individual thinking entries in the HTML output (without requiring a server).
5. If no thinking blocks are found in the session, the Session Analyzer shall display a message indicating that extended thinking was not used.

---

### 要件 7: HTML レポート出力

**目的:** 開発者として、解析結果が単一の HTML ファイルとして出力されることで、サーバーなしにブラウザで即座に確認でき、ファイルを共有しやすい。

#### 受け入れ基準

1. The Session Analyzer shall generate a single self-contained HTML file as its output.
2. The Session Analyzer shall embed all required CSS and JavaScript inline within the HTML file so that no external network requests are needed to render the page.
3. When the output HTML file is opened directly in a web browser via the `file://` protocol, the Session Analyzer shall ensure all interactive features (collapsible sections, tabs, etc.) work correctly without a web server.
4. The Session Analyzer shall default the output file name to `session-{session_id}.html` and write it to the current working directory.
5. Where a `--output` option is provided on the command line, the Session Analyzer shall write the HTML file to the specified path instead.
6. The Session Analyzer shall apply a modern and visually appealing design using pastel colors as the primary color palette.
7. The Session Analyzer shall structure the HTML report with clearly separated sections for: token usage, skill summary, tool summary, sub-agent summary, and thinking log.

---

### 要件 8: コマンドラインインターフェース

**目的:** 開発者として、シンプルな CLI を通じてプログラムを呼び出すことで、エージェントスキルや手動実行の両方から容易に利用できる。

#### 受け入れ基準

1. The Session Analyzer shall provide a CLI entry point that accepts a positional argument for the session ID.
2. The Session Analyzer shall support a `--output` option to specify the output file path.
3. The Session Analyzer shall support a `--claude-dir` option to override the root Claude data directory (equivalent to `CLAUDE_CONFIG_DIR`).
4. When invoked with `--help`, the Session Analyzer shall display usage instructions including all available options.
5. If the Session Analyzer completes successfully, it shall print the path of the generated HTML file to stdout and exit with status code 0.
6. If the Session Analyzer encounters a fatal error (e.g., session not found, file permission error), it shall print a descriptive error message to stderr and exit with a non-zero status code.
