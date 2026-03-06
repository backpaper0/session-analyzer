# Project Structure

## Organization Philosophy

責務分離レイヤー型: Discovery → Parse → Analyze → Report の一方向パイプライン。
各レイヤーは独立したモジュールで、`SessionAnalyzer` がオーケストレートする。

## Directory Patterns

### Main Package (`session_analyzer/`)
**Purpose**: 解析パイプラインの全コンポーネント
**Pattern**: モジュール = 1 責務（discovery, parser, reporter, models, exceptions）

### Analyzers (`session_analyzer/analyzers/`)
**Purpose**: 5 軸の独立した分析ロジック（token, skill, tool, subagent, thinking）
**Pattern**: 各ファイルに `XxxAnalyzer` クラスを 1 つ定義し、`analyze(ParsedSession) -> XxxReport` を実装

### Tests (`tests/`)
**Purpose**: 各モジュールに対応する単体テスト + E2E テスト
**Pattern**: `test_{module_name}.py`、アナライザーは `ParsedSession` を直接構築してテスト

### Sample Logs (`projects/`)
**Purpose**: E2E テスト用のサンプルセッションログ（JSONL）
**Pattern**: `projects/{project_name}/{session_id}.jsonl` + `{session_id}/subagents/agent-*.jsonl`

## Naming Conventions

- **Files**: snake_case（例: `skill_analyzer.py`）
- **Classes**: PascalCase（例: `SkillAnalyzer`, `SkillReport`）
- **Dataclasses**: モデルは `models.py` に集約、`XxxReport` が各アナライザーの出力型

## Code Organization Principles

- **データフロー**: `SessionFiles → ParsedSession → [XxxReport] → SessionReport → HTML`
- **モデル集約**: 全ドメインオブジェクトは `models.py` に定義
- **例外集約**: カスタム例外は `exceptions.py` のみに定義
- **インポート**: パッケージ内は `from session_analyzer.xxx import Yyy` の絶対インポート
- アナライザー追加時は `session_analyzer/analyzers/` にファイルを追加し、`SessionAnalyzer.run()` から呼び出す
