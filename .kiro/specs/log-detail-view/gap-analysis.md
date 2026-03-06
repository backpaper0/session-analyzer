# ギャップ分析レポート: log-detail-view

## 1. 現状調査

### 既存コンポーネントと再利用可能資産

| コンポーネント | ファイル | 関連度 |
|---|---|---|
| ドメインモデル | `session_analyzer/models.py` | ★★★ 全ログデータがすでに型付き |
| ログパーサー | `session_analyzer/parser.py` | ★★★ 変更不要・全エントリを解析済み |
| HTML レポーター | `session_analyzer/reporter.py` | ★★★ タブ構造を拡張すれば実現可能 |
| サブエージェント解析 | `session_analyzer/analyzers/subagent.py` | ★★ 起動箇所の検出ロジックを参照 |
| オーケストレーター | `session_analyzer/session_analyzer.py` | ★★ インターフェース変更が必要 |

### アーキテクチャパターンと規約

- **パイプライン**: `LogDiscovery → LogParser → Analyzers → HtmlReporter`
- **HTML 生成**: Python 側でサーバーサイドレンダリング（文字列結合）、`_TAB_DEFS` リストに追加するだけでタブ追加
- **データ埋め込み**: `const SESSION_DATA = {...}` として `SessionReport` を JSON インライン化
- **コンテンツブロック**: `TextBlock | ToolUseBlock | ThinkingBlock | ToolResultBlock` の Union 型

---

## 2. 要件フィージビリティ分析

### 要件 1 & 2: メイン／サブエージェント詳細ログビュー

**必要なもの**: 全ログエントリの HTML レンダリング

**既存資産**:
- `ParsedSession.main_entries: list[LogEntry]` ✅ すでに全エントリを保持
- `ParsedSession.subagent_entries: dict[str, list[LogEntry]]` ✅ エージェント別に保持
- `AssistantEntry`, `UserEntry` の全フィールド（uuid, timestamp, role, content）✅

**ギャップ**:
- `HtmlReporter.generate(report: SessionReport, ...)` は現在 `ParsedSession` を受け取らない → インターフェース変更が必要
- `ContentBlock` を HTML に変換する関数が存在しない → 新規実装が必要
- `ThinkingBlock` の折りたたみ表示（`<details>`）は既存パターン（thinking セクション）を流用可能

### 要件 3: サブエージェント起動箇所のリンク

**必要なもの**: メインログの `ToolUseBlock(name="Agent"|"Task")` からサブエージェント詳細セクションへのアンカーリンク

**既存資産**:
- `subagent.py` の `_SUBAGENT_TOOL_NAMES = {"Task", "Agent"}` 検出ロジック ✅
- `ToolUseBlock.id` でサブエージェント呼び出しを識別可能 ✅

**ギャップ・要調査**:
- ⚠️ **[要調査]** `ToolUseBlock.id`（例: `toolu_xxx`）と `subagent_entries` のキー（ファイル名由来、例: `agent-aaa111` → `aaa111`）の対応関係が不明。現在 `subagent.py` は順序マッチング（位置ベース）を使用しており、ID ベースの対応付けができていない。実際のログファイルを調査して命名規則を確認する必要がある。
- HTML アンカー（`id="subagent-{agent_id}"`）の設計が必要

### 要件 4: 単一 HTML・パフォーマンス

**既存資産**:
- 外部依存ゼロの設計 ✅
- `file://` 直接表示対応 ✅

**ギャップ**:
- 1,000 件超のエントリに対するパフォーマンス戦略が未定
  - Option A: 全 HTML を Python 側でレンダリング → ブラウザのレンダリング性能に依存（HTML サイズが大きくなる）
  - Option B: `SESSION_DATA` にログデータを追加して JS でレンダリング → `file://` 対応は維持できるが JS 実装量が増加
  - Option C: 最初は折りたたみ（`<details>`）で全件表示し、後でページネーション追加

---

## 3. 実装アプローチ選択肢

### Option A: reporter.py を直接拡張

**変更対象**:
- `reporter.py`: `_render_main_log_section(parsed: ParsedSession)` 等を追加、`_TAB_DEFS` を拡張
- `session_analyzer.py`: `HtmlReporter().generate(report, parsed, output_path)` にシグネチャ変更
- `reporter.py`: `_build_html(report, parsed)` を拡張

**評価**:
- ✅ 新規ファイルなし、既存パターンと一致
- ✅ Python サーバーサイドレンダリングで `file://` 完全対応
- ❌ `reporter.py` が肥大化（現在 ~600 行 → +200〜400 行見込み）
- ❌ テストしにくい

### Option B: log_renderer.py を新規作成（推奨）

**変更対象**:
- `session_analyzer/log_renderer.py` (新規): ログエントリ HTML レンダリング関数群
- `reporter.py`: `log_renderer` をインポートして新タブを追加、`_build_html` シグネチャ変更
- `session_analyzer.py`: `generate()` に `parsed` を渡す

**評価**:
- ✅ 単一責務原則を維持（ログレンダリングを分離）
- ✅ `log_renderer.py` を独立してテスト可能
- ✅ `reporter.py` を適切なサイズに保てる
- ❌ ファイル数が 1 つ増加

### Option C: ハイブリッド（段階的実装）

**Phase 1**: Python サーバーサイドレンダリングで基本ビューを実装（Option B ベース）
**Phase 2**: 必要に応じて JS ページネーションを追加

**評価**:
- ✅ リスクを分散できる
- ✅ まず動作するものを早期に提供できる
- ❌ 設計整合性の維持が必要

---

## 4. 要件 → 資産マップ

| 要件 | 既存資産 | ギャップ | タグ |
|---|---|---|---|
| メインログ全表示 | `ParsedSession.main_entries` | `generate()` へ `ParsedSession` 渡し | Missing |
| タイムスタンプ・ロール表示 | `LogEntry` の全フィールド | HTML レンダリング関数 | Missing |
| ToolUseBlock 表示 | `ToolUseBlock` モデル | レンダリング実装 | Missing |
| Thinking 折りたたみ | `<details>` パターン（既存） | 流用可能 | 再利用 |
| サブエージェント個別ビュー | `subagent_entries` dict | レンダリング + アンカー設計 | Missing |
| agent_id ヘッダー表示 | `agent_id` フィールド | HTML レンダリング | Missing |
| 起動箇所リンク | `ToolUseBlock.id` 検出 | **ID 対応マッピングが不明** | Unknown |
| 単一 HTML | 既存アーキテクチャ | `generate()` インターフェース変更 | Missing |
| `file://` 動作 | 外部依存ゼロ設計 | 維持するだけ | 再利用 |
| 1000 件パフォーマンス | なし | 戦略を決定する必要あり | Unknown |

---

## 5. 実装複雑度・リスク評価

- **工数**: **M（3〜7 日）**
  - パーサー変更不要、モデル変更不要、HTML タブ拡張パターンは確立済み
  - ただし `ContentBlock` のレンダリング（4 variant）と ID マッピング調査が必要
- **リスク**: **Medium**
  - `ToolUseBlock.id` ↔ サブエージェントファイル名の対応が不明（要調査）
  - 大量ログ時のパフォーマンスは実測まで不明

---

## 6. デザインフェーズへの推奨事項

### 推奨アプローチ
**Option B（log_renderer.py 新規作成）** を推奨。

### デザインフェーズで解決すべき研究項目

1. **[要調査] サブエージェント ID マッピング**: 実際のログファイル（`projects/` 配下）を調査し、`ToolUseBlock.id`（`toolu_xxx`）と サブエージェントファイル名（`agent-{uuid}.jsonl`）の命名規則・対応関係を確認する。現在の位置ベースマッチングで十分か、ID ベースマッチングが必要かを判断する。

2. **[要調査] 大量エントリのパフォーマンス戦略**: `<details>` による折りたたみか、JS ページネーションかを決定する。`file://` 対応の維持を前提に。

3. **[設計] `HtmlReporter.generate()` インターフェース変更**: `ParsedSession` を追加引数として渡すか、新しい `LogDetailData` 中間モデルを導入するかを決定する。
