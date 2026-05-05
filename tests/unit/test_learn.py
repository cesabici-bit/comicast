"""L1 tests for the corrections summarizer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from comicast.budget import BudgetTracker
from comicast.learn import update_common_errors_from_log
from comicast.schemas import SeriesProfile


def _seed_corrections(log_path: Path, n: int = 5) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as f:
        for i in range(n):
            rec = {
                "ts": float(i),
                "page": i + 1,
                "panel": 1,
                "bubble_index": 0,
                "correction_type": "speaker_attribution",
                "before": {"speaker_id": "atom_eve"},
                "after": {"speaker_id": "mark_grayson"},
                "user_note": "Mark in costume",
            }
            f.write(json.dumps(rec) + "\n")


@patch("comicast.learn.AnthropicClient")
def test_update_common_errors_calls_claude_and_updates_profile(
    MockClient: MagicMock,  # noqa: N803
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "corrections.jsonl"
    _seed_corrections(log_path)

    mock = MockClient.return_value
    mock.call_text.return_value = json.dumps(
        {
            "common_errors_learned": [
                "Mark in costume is sometimes confused with Atom Eve",
                "Distinguish them by costume colors (blue/yellow vs pink)",
            ]
        }
    )

    profile = SeriesProfile(series_name="Invincible")
    budget = BudgetTracker(estimate_usd=10.0)
    updated = update_common_errors_from_log(
        profile,
        log_path,
        client=mock,
        budget=budget,
    )
    assert len(updated.common_errors_learned) == 2
    assert "Mark" in updated.common_errors_learned[0]


@patch("comicast.learn.AnthropicClient")
def test_update_common_errors_skips_if_log_empty(
    MockClient: MagicMock,  # noqa: N803
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "empty.jsonl"
    log_path.write_text("")
    profile = SeriesProfile(series_name="X")
    budget = BudgetTracker(estimate_usd=10.0)
    updated = update_common_errors_from_log(
        profile, log_path, client=MockClient.return_value, budget=budget
    )
    assert updated.common_errors_learned == []
    MockClient.return_value.call_text.assert_not_called()
