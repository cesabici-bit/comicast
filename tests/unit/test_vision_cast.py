"""L1 unit tests for cast extraction handler. Mocks the API."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from comicast.budget import BudgetTracker
from comicast.schemas import CastFile
from comicast.vision.cast import extract_cast


@patch("comicast.vision.cast.AnthropicClient")
def test_extract_cast_parses_json_response(MockClient: MagicMock, tmp_path: Path) -> None:  # noqa: N803
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
    mock_instance = MockClient.return_value
    mock_instance.call_with_image.return_value = fake_response
    mock_instance.encode_image.return_value = "fake_b64"

    pages = [tmp_path / f"page_{i:03d}.png" for i in (1, 2, 3)]
    for p in pages:
        p.write_bytes(b"fake png")

    budget = BudgetTracker(estimate_usd=20.0)
    result = extract_cast(pages, series_name="Invincible", client=mock_instance, budget=budget)
    assert isinstance(result, CastFile)
    assert result.series_name == "Invincible"
    assert len(result.cast) == 1
    assert result.cast[0].id == "mark_grayson"


@patch("comicast.vision.cast.AnthropicClient")
def test_extract_cast_handles_markdown_fenced_json(MockClient: MagicMock, tmp_path: Path) -> None:  # noqa: N803
    """Claude sometimes wraps JSON in ```json fences. Parser must handle this."""
    fake = '```json\n{"cast":[{"id":"x","canonical_name":"X","aliases":[],"description":"long enough description here for sure","confidence":0.9}]}\n```'
    mock_instance = MockClient.return_value
    mock_instance.call_with_image.return_value = fake
    mock_instance.encode_image.return_value = "b64"
    p = tmp_path / "page_001.png"
    p.write_bytes(b"x")
    budget = BudgetTracker(estimate_usd=10.0)
    result = extract_cast([p], series_name="X", client=mock_instance, budget=budget)
    assert len(result.cast) == 1
