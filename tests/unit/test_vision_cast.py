"""L1 unit tests for cast extraction handler. Mocks the API."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.schemas import CastFile
from comicast.vision.cast import extract_cast


def test_extract_cast_parses_json_response(tmp_path: Path) -> None:
    fake_response = json.dumps(
        {
            "cast": [
                {
                    "id": "mark_grayson",
                    "canonical_name": "Mark Grayson",
                    "aliases": ["Mark", "Invincible"],
                    "description": "Teen male, ~17, dark hair. In suit blue/yellow. Out of suit casual.",
                    "confidence": 0.92,
                }
            ]
        }
    )
    mock_instance = MagicMock(spec=AnthropicClient)
    mock_instance.call_with_image.return_value = fake_response

    pages = [tmp_path / f"page_{i:03d}.png" for i in (1, 2, 3)]
    for p in pages:
        p.write_bytes(b"fake png")

    budget = BudgetTracker(estimate_usd=20.0)
    result = extract_cast(pages, series_name="Invincible", client=mock_instance, budget=budget)
    assert isinstance(result, CastFile)
    assert result.series_name == "Invincible"
    assert len(result.cast) == 1
    assert result.cast[0].id == "mark_grayson"


def test_extract_cast_handles_markdown_fenced_json(tmp_path: Path) -> None:
    """Claude sometimes wraps JSON in ```json fences. Parser must handle this."""
    long_desc = (
        "Adult male, average build, brown hair and beard. In costume: dark armoured suit "
        "with cape and gauntlets. Out of costume: business attire, occasionally casual jacket. "
        "Speaks with measured authority and dry humour."
    )
    fake = (
        "```json\n"
        + json.dumps(
            {
                "cast": [
                    {
                        "id": "x",
                        "canonical_name": "X",
                        "aliases": [],
                        "description": long_desc,
                        "confidence": 0.9,
                    }
                ]
            }
        )
        + "\n```"
    )
    mock_instance = MagicMock(spec=AnthropicClient)
    mock_instance.call_with_image.return_value = fake
    p = tmp_path / "page_001.png"
    p.write_bytes(b"x")
    budget = BudgetTracker(estimate_usd=10.0)
    result = extract_cast([p], series_name="X", client=mock_instance, budget=budget)
    assert len(result.cast) == 1


def test_extract_cast_raises_when_all_pages_fail_parse(tmp_path: Path) -> None:
    """Regression guard for IMP-1 (Risk 4 — silent quality regression).

    If every page returns unparseable text, the function must raise rather than
    return an empty CastFile, which is indistinguishable downstream from a
    legitimate "no recurring named characters" result.
    """
    mock_instance = MagicMock(spec=AnthropicClient)
    mock_instance.call_with_image.return_value = "not json at all, sorry"

    pages = [tmp_path / f"page_{i:03d}.png" for i in (1, 2, 3)]
    for p in pages:
        p.write_bytes(b"fake png")

    budget = BudgetTracker(estimate_usd=10.0)
    with pytest.raises(RuntimeError, match="all 3 pages failed JSON parse"):
        extract_cast(pages, series_name="Invincible", client=mock_instance, budget=budget)
