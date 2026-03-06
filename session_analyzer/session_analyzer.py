"""SessionAnalyzer オーケストレーター"""
from __future__ import annotations

from pathlib import Path

from session_analyzer.analyzers.skill import SkillAnalyzer
from session_analyzer.analyzers.subagent import SubAgentAnalyzer
from session_analyzer.analyzers.thinking import ThinkingAnalyzer
from session_analyzer.analyzers.token import TokenAnalyzer
from session_analyzer.analyzers.tool import ToolAnalyzer
from session_analyzer.discovery import LogDiscovery
from session_analyzer.models import SessionReport
from session_analyzer.parser import LogParser
from session_analyzer.reporter import HtmlReporter


class SessionAnalyzer:
    """
    LogDiscovery → LogParser → 5 アナライザー → HtmlReporter の
    パイプラインを統括するオーケストレーター。
    """

    def run(self, session_id: str, claude_dir: Path, output_path: Path) -> Path:
        """
        セッションを解析して HTML レポートを生成する。

        Args:
            session_id: 解析対象のセッション ID
            claude_dir: Claude 設定ルートディレクトリ（projects/ の親）
            output_path: 出力 HTML ファイルパス

        Returns:
            生成された HTML ファイルの絶対パス

        Raises:
            SessionNotFoundError: セッションが見つからない
            AmbiguousSessionError: 複数のセッションがマッチした
            ReportGenerationError: HTML ファイルの書き込みに失敗した
        """
        # 1. ログファイルの探索
        files = LogDiscovery().discover(session_id, claude_dir)

        # 2. JSONL パース
        parsed = LogParser().parse(files)

        # 3. 5 アナライザーを並列的に実行
        token_report = TokenAnalyzer().analyze(parsed)
        skill_report = SkillAnalyzer().analyze(parsed)
        tool_report = ToolAnalyzer().analyze(parsed)
        subagent_report = SubAgentAnalyzer().analyze(parsed)
        thinking_report = ThinkingAnalyzer().analyze(parsed)

        # 4. SessionReport に集約
        report = SessionReport(
            session_id=parsed.session_id,
            token=token_report,
            skills=skill_report,
            tools=tool_report,
            sub_agents=subagent_report,
            thinking=thinking_report,
        )

        # 5. HTML 生成
        return HtmlReporter().generate(report, output_path)
