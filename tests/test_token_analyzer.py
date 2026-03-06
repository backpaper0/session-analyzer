"""タスク4.1: トークン使用量とコスト推定の集計テスト"""

import pytest

from session_analyzer.analyzers.token import TokenAnalyzer
from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    TokenReport,
    UsageData,
    UserEntry,
)


def _make_session(main_entries=None, subagent_entries=None) -> ParsedSession:
    return ParsedSession(
        session_id="test-session",
        main_entries=main_entries or [],
        subagent_entries=subagent_entries or {},
    )


def _make_assistant(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation: int = 0,
    cache_read: int = 0,
    agent_id: str | None = None,
) -> AssistantEntry:
    return AssistantEntry(
        uuid="uid",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        model=model,
        content=[],
        usage=UsageData(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation,
            cache_read_input_tokens=cache_read,
        ),
        agent_id=agent_id,
    )


def _make_user() -> UserEntry:
    return UserEntry(
        uuid="u",
        parent_uuid=None,
        timestamp="2024-01-01T00:00:00Z",
        is_meta=False,
        content="hi",
        agent_id=None,
    )


# --- 戻り値の型 ---


def test_analyze_returns_token_report():
    """analyze()がTokenReportを返すこと"""
    session = _make_session()
    result = TokenAnalyzer().analyze(session)
    assert isinstance(result, TokenReport)


def test_analyze_empty_session():
    """エントリがない場合はbyModelが空でtotalがゼロであること"""
    session = _make_session()
    result = TokenAnalyzer().analyze(session)
    assert result.by_model == []
    assert result.total.input_tokens == 0
    assert result.total.output_tokens == 0


# --- モデル別集計 ---


def test_analyze_single_model(tmp_path):
    """単一モデルのトークンが正しく集計されること"""
    session = _make_session(
        main_entries=[
            _make_assistant("claude-sonnet-4-6", 100, 50),
            _make_assistant("claude-sonnet-4-6", 200, 80),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    assert len(result.by_model) == 1
    stats = result.by_model[0]
    assert stats.model == "claude-sonnet-4-6"
    assert stats.input_tokens == 300
    assert stats.output_tokens == 130


def test_analyze_multiple_models():
    """複数モデルがそれぞれ別集計されること"""
    session = _make_session(
        main_entries=[
            _make_assistant("claude-sonnet-4-6", 100, 50),
            _make_assistant("claude-opus-4-6", 200, 80),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    models = {s.model for s in result.by_model}
    assert "claude-sonnet-4-6" in models
    assert "claude-opus-4-6" in models
    assert len(result.by_model) == 2


def test_analyze_cache_tokens_aggregated():
    """キャッシュトークンが正しく集計されること"""
    session = _make_session(
        main_entries=[
            _make_assistant(
                "claude-sonnet-4-6", 100, 50, cache_creation=20, cache_read=10
            ),
            _make_assistant(
                "claude-sonnet-4-6", 50, 25, cache_creation=5, cache_read=15
            ),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.cache_creation_tokens == 25
    assert stats.cache_read_tokens == 25


# --- コスト計算 ---


def test_analyze_known_model_cost_sonnet():
    """claude-sonnet-4-6の料金が正しく計算されること（MTokあたり）"""
    # sonnet: input=3.0, output=15.0, cache_write=3.75, cache_read=0.30 USD/MTok
    session = _make_session(
        main_entries=[
            _make_assistant("claude-sonnet-4-6", 1_000_000, 1_000_000),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.estimated_cost_usd == pytest.approx(3.0 + 15.0)


def test_analyze_known_model_cost_opus():
    """claude-opus-4-6の料金が正しく計算されること"""
    # opus: input=15.0, output=75.0 USD/MTok
    session = _make_session(
        main_entries=[
            _make_assistant("claude-opus-4-6", 1_000_000, 1_000_000),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.estimated_cost_usd == pytest.approx(15.0 + 75.0)


def test_analyze_known_model_cost_haiku():
    """claude-haiku-4-5-20251001の料金が正しく計算されること"""
    # haiku: input=0.80, output=4.0 USD/MTok
    session = _make_session(
        main_entries=[
            _make_assistant("claude-haiku-4-5-20251001", 1_000_000, 1_000_000),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.estimated_cost_usd == pytest.approx(0.80 + 4.0)


def test_analyze_cache_cost_included():
    """キャッシュ料金がコストに含まれること（sonnet: cache_write=3.75, cache_read=0.30）"""
    session = _make_session(
        main_entries=[
            _make_assistant(
                "claude-sonnet-4-6",
                0,
                0,
                cache_creation=1_000_000,
                cache_read=1_000_000,
            ),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.estimated_cost_usd == pytest.approx(3.75 + 0.30)


def test_analyze_unknown_model_cost_is_none():
    """未知モデルのestimated_cost_usdがNoneであること"""
    session = _make_session(
        main_entries=[
            _make_assistant("claude-unknown-model", 100, 50),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.estimated_cost_usd is None


def test_analyze_unknown_model_tokens_present():
    """未知モデルのトークン数は集計されること"""
    session = _make_session(
        main_entries=[
            _make_assistant("claude-unknown-model", 300, 150),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.input_tokens == 300
    assert stats.output_tokens == 150


# --- total 集計 ---


def test_analyze_total_tokens():
    """totalが全モデル合計トークン数を持つこと"""
    session = _make_session(
        main_entries=[
            _make_assistant("claude-sonnet-4-6", 100, 50),
            _make_assistant("claude-opus-4-6", 200, 80),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    assert result.total.input_tokens == 300
    assert result.total.output_tokens == 130


def test_analyze_total_cost_is_sum():
    """totalのestimated_cost_usdが全モデルのコスト合計であること"""
    session = _make_session(
        main_entries=[
            _make_assistant("claude-sonnet-4-6", 1_000_000, 0),
            _make_assistant("claude-opus-4-6", 1_000_000, 0),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    # sonnet input: 3.0, opus input: 15.0
    assert result.total.estimated_cost_usd == pytest.approx(3.0 + 15.0)


def test_analyze_total_cost_none_if_any_unknown():
    """未知モデルが含まれる場合、totalのcostはNone（コスト不明）になること"""
    session = _make_session(
        main_entries=[
            _make_assistant("claude-sonnet-4-6", 100, 50),
            _make_assistant("claude-unknown", 100, 50),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    # 未知モデルを含む場合はtotalコストはNone
    assert result.total.estimated_cost_usd is None


def test_analyze_total_model_name():
    """totalのmodelフィールドが"total"であること"""
    session = _make_session(
        main_entries=[
            _make_assistant("claude-sonnet-4-6", 100, 50),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    assert result.total.model == "total"


# --- サブエージェントを含む集計 ---


def test_analyze_includes_subagent_tokens():
    """サブエージェントのトークンも集計対象になること"""
    main_entry = _make_assistant("claude-sonnet-4-6", 100, 50)
    sub_entry = _make_assistant("claude-sonnet-4-6", 200, 80, agent_id="agent-aaa")

    session = _make_session(
        main_entries=[main_entry],
        subagent_entries={"aaa": [sub_entry]},
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.input_tokens == 300
    assert stats.output_tokens == 130


def test_analyze_user_entries_ignored():
    """userエントリはトークン集計に含まれないこと"""
    session = _make_session(
        main_entries=[
            _make_user(),
            _make_assistant("claude-sonnet-4-6", 100, 50),
        ]
    )
    result = TokenAnalyzer().analyze(session)

    stats = result.by_model[0]
    assert stats.input_tokens == 100
