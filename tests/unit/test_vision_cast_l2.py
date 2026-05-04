"""L2 domain sanity for cast extraction.

# SOURCE: Spec sez. 4.2 Pass 2a — cast extraction must find recurring named
# characters and assign stable snake_case ids. Validated against curated example.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.vision.cast import extract_cast


@pytest.mark.domain
def test_extract_cast_finds_main_invincible_chars(tmp_path: Path) -> None:
    """SOURCE: Invincible Vol 1 cast (Robert Kirkman, Image Comics, 2003) — Mark, Nolan, Debbie expected.

    L2 contract: given a curated 3-character response that mirrors the documented
    Vol 1 cast, the extractor must (a) surface all three with snake_case ids,
    (b) keep confidence above the 0.7 headline threshold, (c) collapse the
    9-entry stream from 3 identical-page responses into 3 unique entries via
    the dedup loop in cast.py. The mock supplies the oracle; this test verifies
    the plumbing preserves it. Behavioural L2 against a real VLM lands in T46+.
    """
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
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.call_with_image.return_value = response

    pages = [tmp_path / f"p{i:03d}.png" for i in range(1, 4)]
    for p in pages:
        p.write_bytes(b"x")

    result = extract_cast(
        pages,
        series_name="Invincible",
        client=mock_client,
        budget=BudgetTracker(estimate_usd=10.0),
    )
    ids = {c.id for c in result.cast}
    assert "mark_grayson" in ids
    assert "nolan_grayson" in ids
    assert "debbie_grayson" in ids
    # Confidence threshold for headline characters
    for c in result.cast:
        assert c.confidence >= 0.7
    # Cardinality invariant: same 3-entry response replayed across 3 pages
    # (9 entries on the wire) must collapse to exactly 3 unique cast members.
    # Catches a regression where `accumulated` is replaced with a list (or where
    # the result builder duplicates entries from a side-channel). The dict-level
    # dedup-by-id at cast.py:67-70 is the mechanism; this assertion guards the
    # contract independently of the implementation.
    assert len(result.cast) == 3, f"cardinality failed: got {len(result.cast)} entries"
