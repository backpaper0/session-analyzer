# 要件定義書

## はじめに

Session Analyzer が生成する HTML レポートに、メインセッションおよびサブエージェントの全ログエントリを閲覧できる詳細ビューを追加する。メインセッションログ内のサブエージェント起動箇所から対応するサブエージェント詳細ビューへリンクを張り、すべてを単一の自己完結型 HTML ファイルで提供する。

## Requirements

### Requirement 1: メインセッション詳細ログビュー

**Objective:** 開発者として、メインセッションの全ログエントリを時系列で閲覧したい。そうすることで、セッション中に何が起きたかを詳細に把握できる。

#### Acceptance Criteria

1. The Log Detail View shall メインセッションの全ログエントリ（各 JSONL 行）を時系列順に表示する。
2. The Log Detail View shall 各ログエントリのロール（user / assistant）、タイムスタンプ、およびコンテンツを表示する。
3. The Log Detail View shall assistant ロールのエントリに含まれるツール呼び出し（tool_use）をエントリ内で識別できる形式で表示する。
4. The Log Detail View shall assistant ロールのエントリに含まれる Thinking ブロックを折りたたみ可能な形式で表示する。
5. If ログエントリが存在しない場合、The Log Detail View shall 「ログエントリが見つかりません」のメッセージを表示する。

### Requirement 2: サブエージェント詳細ログビュー

**Objective:** 開発者として、各サブエージェントの全ログエントリを個別に閲覧したい。そうすることで、サブエージェントの動作を詳細に追跡できる。

#### Acceptance Criteria

1. The Log Detail View shall 検出された各サブエージェントについて、個別の詳細ログビューを提供する。
2. The Log Detail View shall サブエージェントの詳細ビューに、そのサブエージェントの全ログエントリを時系列順に表示する。
3. The Log Detail View shall サブエージェント詳細ビューのヘッダーに agent_id を表示する。
4. The Log Detail View shall サブエージェント詳細ビューに、メインセッション詳細ビューへ戻るナビゲーションリンクを提供する。
5. If サブエージェントログが存在しない場合、The Log Detail View shall サブエージェントセクションを非表示にする。

### Requirement 3: サブエージェント起動箇所のリンク

**Objective:** 開発者として、メインセッションログ内でサブエージェントが起動された箇所からそのサブエージェントのログへジャンプしたい。そうすることで、メインとサブの実行フローを対応づけて読める。

#### Acceptance Criteria

1. When メインセッションのログエントリがサブエージェント起動（Agent ツール呼び出し）を含む場合、The Log Detail View shall そのエントリに対応するサブエージェント詳細ビューへのリンクを表示する。
2. When リンクがクリックされた場合、The Log Detail View shall 同一 HTML ファイル内の対応するサブエージェント詳細ビューのセクションへスクロールする。
3. The Log Detail View shall サブエージェント起動エントリを視覚的に強調表示（ハイライト）する。
4. If 対応するサブエージェントログが見つからない場合、The Log Detail View shall リンクを表示せずエントリのみを表示する。

### Requirement 4: 単一 HTML ファイルでの実現

**Objective:** 開発者として、詳細ビューを含む全コンテンツを単一の自己完結型 HTML ファイルで受け取りたい。そうすることで、サーバーなしに `file://` でそのまま閲覧できる。

#### Acceptance Criteria

1. The Log Detail View shall メインセッション詳細ビューおよび全サブエージェント詳細ビューを、既存の Session Analyzer HTML レポートと同一の単一 HTML ファイル内に含める。
2. The Log Detail View shall 外部 CSS・JS・フォント・画像などの外部リソースへの依存を持たず、`file://` プロトコルで完全動作する。
3. The Log Detail View shall ログデータをインライン JS オブジェクト（`SESSION_DATA`）として HTML に埋め込む形式を使用する。
4. The Log Detail View shall 既存の HTML レポート内のナビゲーション（サマリー・トークン分析等）から詳細ビューセクションへのリンクを提供する。
5. While 大量のログエントリ（1,000 件超）が存在する場合、The Log Detail View shall ページネーションまたは仮想スクロールにより表示パフォーマンスを維持する。
