"""L1 unit tests for narrative consistency check."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.schemas import (
    Bubble,
    BubbleType,
    CastEntry,
    CastFile,
    FlagsFile,
    PageScript,
    Panel,
    ScriptFile,
)
from comicast.vision.narrative import check_narrative


def _empty_script() -> ScriptFile:
    page = PageScript(
        page=1,
        panels=[
            Panel(
                order=1,
                bubbles=[
                    Bubble(
                        text="hello",
                        speaker_id="x",
                        emotion="x",
                        type=BubbleType.DIALOGUE,
                        bbox=(0, 0, 1, 1),
                        confidence=0.9,
                    ),
                ],
            )
        ],
    )
    return ScriptFile(series_name="X", volume_id="vol_1", pages=[page])


def _cast() -> CastFile:
    return CastFile(
        series_name="X",
        cast=[
            CastEntry(
                id="x",
                canonical_name="X",
                aliases=[],
                description="some character description, long enough to validate",
                confidence=0.9,
            )
        ],
    )


def test_narrative_check_returns_flags() -> None:
    response = json.dumps(
        {
            "flags": [
                {
                    "page": 47,
                    "panel": 2,
                    "issue": "Atom Eve attributed but not in scene",
                    "severity": "high",
                    "suggestion": "Likely mark_grayson",
                }
            ]
        }
    )
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.call_text.return_value = response
    result = check_narrative(
        _empty_script(),
        cast=_cast(),
        client=mock_client,
        budget=BudgetTracker(estimate_usd=10.0),
    )
    assert isinstance(result, FlagsFile)
    assert len(result.flags) == 1
    assert result.flags[0].severity == "high"


def test_narrative_check_handles_empty_flags() -> None:
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.call_text.return_value = json.dumps({"flags": []})
    result = check_narrative(
        _empty_script(),
        cast=_cast(),
        client=mock_client,
        budget=BudgetTracker(estimate_usd=10.0),
    )
    assert result.flags == []
