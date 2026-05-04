"""Integration test for the full vision pipeline (mocked)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.vision.attribute import attribute_pages
from comicast.vision.cast import extract_cast
from comicast.vision.narrative import check_narrative


def test_full_vision_pipeline_mocked(tmp_path: Path) -> None:
    cast_client = MagicMock(spec=AnthropicClient)
    cast_client.call_with_image.return_value = json.dumps(
        {
            "cast": [
                {
                    "id": "x",
                    "canonical_name": "X",
                    "aliases": [],
                    "description": "ten or more chars desc",
                    "confidence": 0.9,
                }
            ]
        }
    )
    cast_client.encode_image.return_value = "b64"

    attr_client = MagicMock(spec=AnthropicClient)
    attr_client.call_with_image.return_value = json.dumps(
        {
            "page": 1,
            "panels": [
                {
                    "order": 1,
                    "bubbles": [
                        {
                            "text": "hi",
                            "speaker_id": "x",
                            "emotion": "casual",
                            "type": "dialogue",
                            "bbox": [0, 0, 1, 1],
                            "confidence": 0.9,
                        }
                    ],
                }
            ],
        }
    )
    attr_client.encode_image.return_value = "b64"

    nar_client = MagicMock(spec=AnthropicClient)
    nar_client.call_text.return_value = json.dumps({"flags": []})

    pages = [tmp_path / f"p{i:03d}.png" for i in range(1, 3)]
    for p in pages:
        p.write_bytes(b"x")

    budget = BudgetTracker(estimate_usd=20.0)
    cast = extract_cast(pages, series_name="X", client=cast_client, budget=budget)
    script = attribute_pages(
        pages,
        cast=cast,
        common_errors=[],
        series_name="X",
        volume_id="v1",
        client=attr_client,
        budget=budget,
    )
    flags = check_narrative(script, cast=cast, client=nar_client, budget=budget)

    assert len(cast.cast) == 1
    assert len(script.pages) == 2
    assert len(flags.flags) == 0
    assert budget.spent_usd == 0  # mocks didn't trigger real cost recording
