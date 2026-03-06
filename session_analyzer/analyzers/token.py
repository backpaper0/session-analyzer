"""トークン使用量とコスト推定アナライザー"""
from __future__ import annotations

from collections import defaultdict

from session_analyzer.models import (
    AssistantEntry,
    ParsedSession,
    TokenReport,
    TokenUsageStats,
)

# 料金テーブル（USD / MTok）
PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-6": {
        "input": 15.0,
        "output": 75.0,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    "claude-sonnet-4-6": {
        "input": 3.0,
        "output": 15.0,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.80,
        "output": 4.0,
        "cache_write": 1.00,
        "cache_read": 0.08,
    },
}

_MTOK = 1_000_000.0


def _calc_cost(model: str, input_tokens: int, output_tokens: int,
               cache_creation: int, cache_read: int) -> float | None:
    """既知モデルの料金を計算する。未知モデルは None を返す。"""
    pricing = PRICING.get(model)
    if pricing is None:
        return None
    return (
        input_tokens / _MTOK * pricing["input"]
        + output_tokens / _MTOK * pricing["output"]
        + cache_creation / _MTOK * pricing["cache_write"]
        + cache_read / _MTOK * pricing["cache_read"]
    )


class TokenAnalyzer:
    """全ログからトークン使用量を集計し、モデル別集計とコスト推定を算出する"""

    def analyze(self, session: ParsedSession) -> TokenReport:
        # モデル別に (input, output, cache_creation, cache_read) を集計
        counters: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])

        all_entries = list(session.main_entries)
        for sub_entries in session.subagent_entries.values():
            all_entries.extend(sub_entries)

        has_unknown = False
        for entry in all_entries:
            if not isinstance(entry, AssistantEntry):
                continue
            c = counters[entry.model]
            c[0] += entry.usage.input_tokens
            c[1] += entry.usage.output_tokens
            c[2] += entry.usage.cache_creation_input_tokens
            c[3] += entry.usage.cache_read_input_tokens
            if entry.model not in PRICING:
                has_unknown = True

        by_model: list[TokenUsageStats] = []
        total_input = total_output = total_cache_create = total_cache_read = 0
        total_cost: float | None = 0.0

        for model, (inp, out, cc, cr) in counters.items():
            cost = _calc_cost(model, inp, out, cc, cr)
            by_model.append(TokenUsageStats(
                model=model,
                input_tokens=inp,
                output_tokens=out,
                cache_creation_tokens=cc,
                cache_read_tokens=cr,
                estimated_cost_usd=cost,
            ))
            total_input += inp
            total_output += out
            total_cache_create += cc
            total_cache_read += cr
            if cost is not None and total_cost is not None:
                total_cost += cost
            else:
                total_cost = None

        # has_unknown がある場合、total_cost を None にする
        if has_unknown:
            total_cost = None

        total = TokenUsageStats(
            model="total",
            input_tokens=total_input,
            output_tokens=total_output,
            cache_creation_tokens=total_cache_create,
            cache_read_tokens=total_cache_read,
            estimated_cost_usd=total_cost,
        )

        return TokenReport(by_model=by_model, total=total)
