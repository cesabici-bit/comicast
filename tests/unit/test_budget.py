"""L1 + L2 tests for budget tracking and guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from comicast.budget import BudgetExceededError, BudgetTracker


def test_tracker_starts_at_zero() -> None:
    t = BudgetTracker(estimate_usd=20.0, hard_multiplier=2.0)
    assert t.spent_usd == 0.0


def test_record_anthropic_cost_matches_sonnet_4_6_pricing() -> None:
    """L2: Anthropic cost is computed from disjoint SDK usage counters.

    The four counters returned by Anthropic SDK on Sonnet 4.6 are disjoint —
    `input_tokens` already excludes cached/created portions. Cost is the sum
    of each counter times its own rate, NOT (input - cached) * input_rate.
    """
    # SOURCE: docs/research/F1-anthropic.md:80-84 (Sonnet 4.6 prices, 5m cache lane)
    #   Input (uncached):       $3.00 / 1M
    #   Output:                  $15.00 / 1M
    #   Cache write 5m:          $3.75 / 1M  (1.25x input)
    #   Cache read:              $0.30 / 1M  (0.10x input)
    # Worked example: realistic Pass 2b call shape (per-page user prompt + system cache hit)
    #   input_tokens=10_000, cached_input_tokens=8_000, cache_write_tokens=0, output_tokens=500
    # Expected: 10000/1M*3.00 + 8000/1M*0.30 + 0 + 500/1M*15.00
    #         = 0.030 + 0.0024 + 0 + 0.0075
    #         = 0.0399 USD
    t = BudgetTracker(estimate_usd=20.0)
    t.record(
        provider="anthropic",
        input_tokens=10_000,
        cached_input_tokens=8_000,
        cache_write_tokens=0,
        output_tokens=500,
    )
    assert abs(t.spent_usd - 0.0399) < 1e-9


def test_record_anthropic_with_cache_write() -> None:
    """L2: cache_write_tokens (1.25x input) bills as a separate disjoint counter."""
    # SOURCE: docs/research/F1-anthropic.md:82 — cache write 5m at $3.75/1M
    # Worked example: first call of a 5m cache window (system prompt freshly written)
    #   input_tokens=200, cached_input_tokens=0, cache_write_tokens=8_000, output_tokens=500
    # Expected: 200/1M*3.00 + 0 + 8000/1M*3.75 + 500/1M*15.00
    #         = 0.0006 + 0 + 0.030 + 0.0075
    #         = 0.0381 USD
    t = BudgetTracker(estimate_usd=20.0)
    t.record(
        provider="anthropic",
        input_tokens=200,
        cached_input_tokens=0,
        cache_write_tokens=8_000,
        output_tokens=500,
    )
    assert abs(t.spent_usd - 0.0381) < 1e-9


def test_record_elevenlabs_cost_matches_kchar_rate() -> None:
    """L2: ElevenLabs cost is `chars / 1000 * ELEVENLABS_PER_KCHAR`.

    The constant is the conservative premium-voice ceiling (3x GA standard).
    """
    # SOURCE: docs/research/F1-elevenlabs.md:316,442 — premium-voice 3x rate ($0.30/kchar);
    #         GA standard is $0.10/kchar (F1-elevenlabs.md:121).
    # Worked example: 5_000 chars at the conservative ceiling
    # Expected: 5000 / 1000 * 0.30 = 1.50 USD
    t = BudgetTracker(estimate_usd=20.0)
    t.record(provider="elevenlabs", chars=5000)
    assert abs(t.spent_usd - 1.50) < 1e-9


def test_guard_halts_at_2x_estimate() -> None:
    t = BudgetTracker(estimate_usd=10.0, hard_multiplier=2.0)
    t.record(provider="anthropic", manual_cost=25.0)
    assert t.spent_usd == 25.0
    assert t.is_over_hard_limit()
    with pytest.raises(BudgetExceededError):
        t.assert_under_hard_limit()


def test_guard_warns_at_estimate() -> None:
    t = BudgetTracker(estimate_usd=10.0)
    t.record(provider="anthropic", manual_cost=10.5)
    assert t.is_over_estimate()
    assert not t.is_over_hard_limit()


def test_manual_cost_tags_record_source() -> None:
    """When manual_cost is set, the record is tagged cost_source='manual'."""
    log_path: Path | None = None
    t = BudgetTracker(estimate_usd=10.0, log_path=log_path)
    t.record(provider="anthropic", manual_cost=5.0)
    assert len(t._records) == 1
    assert t._records[0]["cost_source"] == "manual"
    assert t._records[0]["cost_usd"] == 5.0


def test_computed_cost_tags_record_source() -> None:
    """When manual_cost is None, the record is tagged cost_source='computed'."""
    t = BudgetTracker(estimate_usd=10.0)
    t.record(provider="elevenlabs", chars=1000)
    assert t._records[0]["cost_source"] == "computed"


def test_persist_to_log(tmp_path: Path) -> None:
    log_path = tmp_path / "budget.log"
    t = BudgetTracker(estimate_usd=20.0, log_path=log_path)
    t.record(provider="anthropic", input_tokens=1000, output_tokens=100)
    t.flush()
    content = log_path.read_text()
    assert "anthropic" in content
    assert "1000" in content
    assert "computed" in content  # cost_source field present in JSONL
