"""L1 + L2 tests for budget tracking and guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from comicast.budget import BudgetExceededError, BudgetTracker


def test_tracker_starts_at_zero() -> None:
    t = BudgetTracker(estimate_usd=20.0, hard_multiplier=2.0)
    assert t.spent_usd == 0.0


def test_record_anthropic_call_updates_spent() -> None:
    t = BudgetTracker(estimate_usd=20.0)
    t.record(provider="anthropic", input_tokens=10000, output_tokens=500, cached_input_tokens=8000)
    assert t.spent_usd > 0


def test_record_elevenlabs_call_updates_spent() -> None:
    t = BudgetTracker(estimate_usd=20.0)
    t.record(provider="elevenlabs", chars=5000)
    assert t.spent_usd > 0


def test_guard_halts_at_2x_estimate() -> None:
    t = BudgetTracker(estimate_usd=10.0, hard_multiplier=2.0)
    t.record(provider="anthropic", input_tokens=1, output_tokens=1, manual_cost=25.0)
    assert t.spent_usd == 25.0
    assert t.is_over_hard_limit()
    with pytest.raises(BudgetExceededError):
        t.assert_under_hard_limit()


def test_guard_warns_at_estimate() -> None:
    t = BudgetTracker(estimate_usd=10.0)
    t.record(provider="anthropic", input_tokens=1, output_tokens=1, manual_cost=10.5)
    assert t.is_over_estimate()
    assert not t.is_over_hard_limit()


def test_persist_to_log(tmp_path: Path) -> None:
    log_path = tmp_path / "budget.log"
    t = BudgetTracker(estimate_usd=20.0, log_path=log_path)
    t.record(provider="anthropic", input_tokens=1000, output_tokens=100)
    t.flush()
    content = log_path.read_text()
    assert "anthropic" in content
    assert "1000" in content
