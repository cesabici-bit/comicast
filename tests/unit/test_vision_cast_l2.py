"""L2 domain sanity for cast extraction.

# SOURCE: Spec sez. 4.2 Pass 2a — cast extraction must find recurring named
# characters and assign stable snake_case ids. Validated against curated example.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from comicast.budget import BudgetTracker
from comicast.vision.cast import extract_cast


@pytest.mark.domain
@patch("comicast.vision.cast.AnthropicClient")
def test_extract_cast_finds_main_invincible_chars(mock_client: MagicMock, tmp_path: Path) -> None:
    """SOURCE: Invincible Vol 1 cast (publicly known) — Mark, Nolan, Debbie expected."""
    response = json.dumps(
        {
            "cast": [
                {
                    "id": "mark_grayson",
                    "canonical_name": "Mark Grayson",
                    "aliases": ["Mark", "Invincible"],
                    "description": "Teenage male, dark hair. In costume: blue/yellow suit. Out of costume: casual.",
                    "confidence": 0.93,
                },
                {
                    "id": "nolan_grayson",
                    "canonical_name": "Nolan Grayson",
                    "aliases": ["Omni-Man", "Dad"],
                    "description": "Adult male, mustache, white hair. In costume: red/white. Out of costume: civilian.",
                    "confidence": 0.91,
                },
                {
                    "id": "debbie_grayson",
                    "canonical_name": "Debbie Grayson",
                    "aliases": ["Mom"],
                    "description": "Adult female, dark hair, mother of Mark, real estate agent.",
                    "confidence": 0.88,
                },
            ]
        }
    )
    mock = mock_client.return_value
    mock.call_with_image.return_value = response
    mock.encode_image.return_value = "b64"

    pages = [tmp_path / f"p{i:03d}.png" for i in range(1, 4)]
    for p in pages:
        p.write_bytes(b"x")

    result = extract_cast(
        pages, series_name="Invincible", client=mock, budget=BudgetTracker(estimate_usd=10.0)
    )
    ids = {c.id for c in result.cast}
    assert "mark_grayson" in ids
    assert "nolan_grayson" in ids
    assert "debbie_grayson" in ids
    # Confidence threshold for headline characters
    for c in result.cast:
        assert c.confidence >= 0.7
