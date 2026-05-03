"""Cost tracking and budget guard.

Pricing verified 2026-05-02 against:
- docs/research/F1-anthropic.md (Sonnet 4.6 lanes, 5m ephemeral cache)
- docs/research/F1-elevenlabs.md (v3 GA standard rate)
Re-verify whenever the Anthropic/ElevenLabs pricing pages change.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

from comicast.logging_setup import get_logger

log = get_logger("comicast.budget")

# Anthropic Sonnet 4.6 pricing — USD per million tokens.
# Per F1-anthropic.md:78-86, the four counters (input_tokens, cache_read_input_tokens,
# cache_creation_input_tokens, output_tokens) returned by the SDK are DISJOINT —
# input_tokens already excludes the cached/created portions. The cost formula
# multiplies each counter by its own rate; do NOT subtract.
ANTHROPIC_INPUT_PER_MTOK = 3.0  # uncached input — F1-anthropic.md:80
ANTHROPIC_INPUT_CACHED_PER_MTOK = 0.3  # 0.1x input (cache read) — F1-anthropic.md:84
ANTHROPIC_INPUT_CACHE_WRITE_PER_MTOK = 3.75  # 1.25x input (5m cache write) — F1-anthropic.md:82
ANTHROPIC_OUTPUT_PER_MTOK = 15.0  # F1-anthropic.md:81

# ELEVENLABS_PER_KCHAR is set as a CONSERVATIVE CEILING (premium-voice 3x rate per
# F1-elevenlabs.md:316,442). The GA standard is $0.10/kchar (F1-elevenlabs.md:121),
# but per-voice rate multipliers are not yet plumbed through `record()`. Setting the
# constant to 0.30 over-bills non-premium voices but preserves 2x guard headroom on
# worst-case voice mix. Revisit when Pass 3 wires per-voice rate (see Backlog B5).
ELEVENLABS_PER_KCHAR = 0.30


class BudgetExceededError(RuntimeError):
    """Raised when cost exceeds hard_multiplier * estimate."""


class BudgetTracker:
    """Track API spend and halt pipeline if it exceeds the hard limit."""

    def __init__(
        self,
        estimate_usd: float,
        hard_multiplier: float = 2.0,
        log_path: Path | None = None,
    ) -> None:
        self.estimate_usd = estimate_usd
        self.hard_multiplier = hard_multiplier
        self.spent_usd = 0.0
        self.log_path = log_path
        self._records: list[dict[str, object]] = []

    def record(
        self,
        provider: Literal["anthropic", "elevenlabs"],
        *,
        input_tokens: int = 0,
        cached_input_tokens: int = 0,
        cache_write_tokens: int = 0,
        output_tokens: int = 0,
        chars: int = 0,
        manual_cost: float | None = None,
    ) -> None:
        """Record a single API call's cost.

        For provider="anthropic", pass the four SDK usage counters directly (they
        are disjoint per F1-anthropic.md). For provider="elevenlabs", pass `chars`.
        Pass `manual_cost` to override the formula (e.g. for tests). When
        `manual_cost` is set, token/char counts are still logged for audit but do
        NOT contribute to cost; the record is tagged `cost_source="manual"`.
        """
        cost_source: Literal["manual", "computed"]
        if manual_cost is not None:
            cost = manual_cost
            cost_source = "manual"
            if input_tokens or cached_input_tokens or cache_write_tokens or output_tokens or chars:
                # Audit anomaly: caller passed both manual_cost and tokens — the
                # tokens won't drive the cost, but they will appear in the log row.
                log.warning(
                    "budget.manual_cost_with_tokens",
                    provider=provider,
                    manual_cost=manual_cost,
                )
        elif provider == "anthropic":
            cost = (
                input_tokens / 1_000_000 * ANTHROPIC_INPUT_PER_MTOK
                + cached_input_tokens / 1_000_000 * ANTHROPIC_INPUT_CACHED_PER_MTOK
                + cache_write_tokens / 1_000_000 * ANTHROPIC_INPUT_CACHE_WRITE_PER_MTOK
                + output_tokens / 1_000_000 * ANTHROPIC_OUTPUT_PER_MTOK
            )
            cost_source = "computed"
        elif provider == "elevenlabs":
            cost = chars / 1000 * ELEVENLABS_PER_KCHAR
            cost_source = "computed"
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self.spent_usd += cost
        rec: dict[str, object] = {
            "ts": time.time(),
            "provider": provider,
            "cost_usd": cost,
            "cost_source": cost_source,
            "running_total_usd": self.spent_usd,
            "input_tokens": input_tokens,
            "cached_input_tokens": cached_input_tokens,
            "cache_write_tokens": cache_write_tokens,
            "output_tokens": output_tokens,
            "chars": chars,
        }
        self._records.append(rec)
        log.info(
            "budget.record",
            provider=provider,
            cost_usd=round(cost, 4),
            cost_source=cost_source,
            running_total_usd=round(self.spent_usd, 4),
        )

    def is_over_estimate(self) -> bool:
        """True when spend has crossed the soft estimate (1.0x)."""
        return self.spent_usd > self.estimate_usd

    def is_over_hard_limit(self) -> bool:
        """True when spend has crossed `hard_multiplier * estimate` (default 2x)."""
        return self.spent_usd > self.estimate_usd * self.hard_multiplier

    def assert_under_hard_limit(self) -> None:
        """Raise BudgetExceededError when over the hard limit. Halts the pipeline.

        NOTE: this method raises unconditionally — it does NOT use Python's
        `assert` statement (which would be stripped under `python -O`). Do not
        refactor to `assert not self.is_over_hard_limit(), msg`: that would
        silently disable Risk 3 protection in optimized builds. The `assert_`
        prefix is preserved for call-site readability; rename is tracked in
        Backlog (KNOWN_ISSUES `BG-01`).
        """
        if self.is_over_hard_limit():
            raise BudgetExceededError(
                f"Spent ${self.spent_usd:.2f} > {self.hard_multiplier}x estimate "
                f"${self.estimate_usd:.2f}. Halting pipeline."
            )

    def flush(self) -> None:
        """Append in-memory records to log_path as JSONL and clear the buffer.

        No-op when log_path is None.
        """
        if self.log_path is None:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            for rec in self._records:
                f.write(json.dumps(rec) + "\n")
        self._records.clear()
