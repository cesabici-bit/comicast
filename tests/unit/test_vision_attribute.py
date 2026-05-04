"""L1 unit tests for per-page attribution."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.schemas import CastEntry, CastFile, ScriptFile
from comicast.vision.attribute import attribute_pages


def test_attribute_processes_each_page(tmp_path: Path) -> None:
    response_template = {
        "page": 1,
        "panels": [
            {
                "order": 1,
                "bubbles": [
                    {
                        "text": "Hello world",
                        "speaker_id": "mark_grayson",
                        "emotion": "casual",
                        "type": "dialogue",
                        "bbox": [10, 20, 100, 80],
                        "confidence": 0.95,
                    }
                ],
            }
        ],
    }

    def side_effect(**kwargs: object) -> str:  # noqa: ANN001
        # Each call returns the template with incremented page number
        idx = side_effect._counter  # type: ignore[attr-defined]
        side_effect._counter += 1  # type: ignore[attr-defined]
        resp = dict(response_template)
        resp["page"] = idx
        return json.dumps(resp)

    side_effect._counter = 1  # type: ignore[attr-defined]

    mock = MagicMock(spec=AnthropicClient)
    mock.call_with_image.side_effect = side_effect
    mock.encode_image.return_value = "b64"

    pages = [tmp_path / f"page_{i:03d}.png" for i in range(1, 4)]
    for p in pages:
        p.write_bytes(b"x")

    cast = CastFile(
        series_name="Invincible",
        cast=[
            CastEntry(
                id="mark_grayson",
                canonical_name="Mark",
                aliases=["Mark"],
                description="teen, dark hair, blue/yellow costume, sarcastic but kind",
                confidence=0.95,
            )
        ],
    )
    budget = BudgetTracker(estimate_usd=20.0)
    script = attribute_pages(
        pages,
        cast=cast,
        common_errors=[],
        series_name="Invincible",
        volume_id="vol_1",
        client=mock,
        budget=budget,
    )
    assert isinstance(script, ScriptFile)
    assert len(script.pages) == 3
    assert script.pages[0].page == 1
    assert script.pages[2].page == 3


def test_attribute_continues_on_single_page_failure(tmp_path: Path) -> None:
    """If one page errors, other pages still process; failed page logged."""

    def side_effect(**kwargs: object) -> str:  # noqa: ANN001
        if side_effect._counter == 2:  # type: ignore[attr-defined]
            side_effect._counter += 1  # type: ignore[attr-defined]
            return "INVALID JSON"
        side_effect._counter += 1  # type: ignore[attr-defined]
        return json.dumps({"page": side_effect._counter, "panels": []})  # type: ignore[attr-defined]

    side_effect._counter = 1  # type: ignore[attr-defined]

    mock = MagicMock(spec=AnthropicClient)
    mock.call_with_image.side_effect = side_effect
    mock.encode_image.return_value = "b64"

    pages = [tmp_path / f"p{i:03d}.png" for i in range(1, 4)]
    for p in pages:
        p.write_bytes(b"x")
    cast = CastFile(series_name="X", cast=[])
    budget = BudgetTracker(estimate_usd=10.0)
    script = attribute_pages(
        pages,
        cast=cast,
        common_errors=[],
        series_name="X",
        volume_id="vol_1",
        client=mock,
        budget=budget,
    )
    # 3 input pages, 1 failed → 2 successful
    assert len(script.pages) == 2
