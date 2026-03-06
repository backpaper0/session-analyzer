"""カスタム例外定義"""


class SessionNotFoundError(Exception):
    """セッション ID に対応するファイルが見つからない場合"""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


class AmbiguousSessionError(Exception):
    """複数のファイルがセッション ID にマッチした場合"""

    def __init__(self, session_id: str, candidates: list[str]) -> None:
        candidates_str = ", ".join(candidates)
        super().__init__(f"Multiple sessions match '{session_id}': {candidates_str}")
        self.session_id = session_id
        self.candidates = candidates


class ReportGenerationError(Exception):
    """HTML レポート生成に失敗した場合"""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Failed to write report: {reason}")
        self.reason = reason
