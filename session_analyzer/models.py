"""ドメインモデル定義"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# コンテンツブロック
# ---------------------------------------------------------------------------


@dataclass
class UsageData:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class TextBlock:
    type: Literal["text"]
    text: str


@dataclass
class ToolUseBlock:
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, object]


@dataclass
class ThinkingBlock:
    type: Literal["thinking"]
    thinking: str
    signature: str


@dataclass
class ToolResultBlock:
    type: Literal["tool_result"]
    tool_use_id: str
    content: str
    is_error: bool


ContentBlock = TextBlock | ToolUseBlock | ThinkingBlock | ToolResultBlock


# ---------------------------------------------------------------------------
# ログエントリ
# ---------------------------------------------------------------------------


@dataclass
class AssistantEntry:
    uuid: str
    parent_uuid: str | None
    timestamp: str
    model: str
    content: list[ContentBlock]
    usage: UsageData
    agent_id: str | None  # サブエージェントログの場合のみ


@dataclass
class UserEntry:
    uuid: str
    parent_uuid: str | None
    timestamp: str
    is_meta: bool
    content: str | list[ContentBlock]
    agent_id: str | None


LogEntry = AssistantEntry | UserEntry


# ---------------------------------------------------------------------------
# セッション集約モデル
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionFiles:
    main: Path
    subagents: list[Path]


@dataclass
class ParsedSession:
    session_id: str
    main_entries: list[LogEntry]
    subagent_entries: dict[str, list[LogEntry]]  # agentId -> entries
    cwd: str | None = None  # セッション実行時のワークディレクトリ
    last_timestamp: str | None = None  # 最後のエントリのタイムスタンプ


# ---------------------------------------------------------------------------
# アナライザー出力型
# ---------------------------------------------------------------------------


@dataclass
class TokenUsageStats:
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    estimated_cost_usd: float | None  # 未知モデルは None


@dataclass
class TokenReport:
    by_model: list[TokenUsageStats]
    total: TokenUsageStats  # 全モデル合計


class InvocationMethod(StrEnum):
    USER_SLASH_COMMAND = "ユーザー起動（スラッシュコマンド）"
    LLM_AUTO = "LLM自動起動"


@dataclass
class SkillInvocation:
    skill_name: str
    method: InvocationMethod
    timestamp: str
    uuid: str


@dataclass
class SkillReport:
    invocations: list[SkillInvocation]  # 時系列順
    summary: dict[str, int]  # skill_name -> count


@dataclass
class BashInvocation:
    command: str  # 実行されたコマンド文字列
    is_error: bool
    error_message: str | None
    timestamp: str
    source: str  # "main" or agent_id
    entry_uuid: str  # Bash ToolUseBlock を含む AssistantEntry.uuid


@dataclass
class CommandAggregation:
    base_command: str
    count: int
    sub_commands: dict[str, int]  # サブコマンド展開対象のみ populated


@dataclass
class ToolReport:
    tool_counts: dict[str, int]  # tool_name -> count
    bash_invocations: list[BashInvocation]  # 全 Bash 実行一覧（時系列）
    bash_aggregation: list[CommandAggregation]  # ベースコマンド別集計（降順）


@dataclass
class SubAgentInfo:
    agent_id: str
    tool_name: str  # "Task" or "Agent"
    subagent_type: str | None  # e.g. "Explore"
    prompt: str  # description または prompt フィールド
    launched_at: str  # timestamp
    token_usage: TokenUsageStats | None  # サブエージェントログがある場合


@dataclass
class SubAgentReport:
    agents: list[SubAgentInfo]  # 起動順


@dataclass
class ThinkingEntry:
    content: str  # thinking テキスト
    message_uuid: str  # 紐づく assistant メッセージの UUID
    timestamp: str
    source: str  # "main" or agent_id


@dataclass
class ThinkingReport:
    entries: list[ThinkingEntry]  # 時系列順
    has_thinking: bool


@dataclass
class SessionReport:
    session_id: str
    token: TokenReport
    skills: SkillReport
    tools: ToolReport
    sub_agents: SubAgentReport
    thinking: ThinkingReport
    cwd: str | None = None
    last_timestamp: str | None = None
