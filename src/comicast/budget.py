"""Cost tracking and budget guard.

Pricing rates are best-known as of F1/T05+T06. Update via verified-deps.toml
notes when Anthropic / ElevenLabs change pricing.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

from comicast.logging_setup import get_logger

log = get_logger("comicast.budget")

# Pricing (USD per million tokens for Anthropic, USD per 1k chars for ElevenLabs)
# CONFIRM in F1/T05 and T06; update if needed.
ANTHROPIC_INPUT_PER_MTOK = 3.0  # standard input tokens
ANTHROPIC_INPUT_CACHED_PER_MTOK = 0.3  # 10% of standard for cache hits
ANTHROPIC_INPUT_CACHE_WRITE_PER_MTOK = 3.75  # 1.25x standard for cache writes
ANTHROPIC_OUTPUT_PER_MTOK = 15.0
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
        """Record a single API call's cost."""
        if manual_cost is not None:
            cost = manual_cost
        elif provider == "anthropic":
            cost = (
                (input_tokens - cached_input_tokens - cache_write_tokens)
                / 1_000_000
                * ANTHROPIC_INPUT_PER_MTOK
                + cached_input_tokens / 1_000_000 * ANTHROPIC_INPUT_CACHED_PER_MTOK
                + cache_write_tokens / 1_000_000 * ANTHROPIC_INPUT_CACHE_WRITE_PER_MTOK
                + output_tokens / 1_000_000 * ANTHROPIC_OUTPUT_PER_MTOK
            )
        elif provider == "elevenlabs":
            cost = chars / 1000 * ELEVENLABS_PER_KCHAR
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self.spent_usd += cost
        rec: dict[str, object] = {
            "ts": time.time(),
            "provider": provider,
            "cost_usd": cost,
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
            running_total_usd=round(self.spent_usd, 4),
        )

    def is_over_estimate(self) -> bool:
        return self.spent_usd > self.estimate_usd

    def is_over_hard_limit(self) -> bool:
        return self.spent_usd > self.estimate_usd * self.hard_multiplier

    def assert_under_hard_limit(self) -> None:
        if self.is_over_hard_limit():
            raise BudgetExceededError(
                f"Spent ${self.spent_usd:.2f} > {self.hard_multiplier}x estimate "
                f"${self.estimate_usd:.2f}. Halting pipeline."
            )

    def flush(self) -> None:
        if self.log_path is None:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            for rec in self._records:
                f.write(json.dumps(rec) + "\n")
        self._records.clear()
