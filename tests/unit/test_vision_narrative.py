"""L1 unit tests for narrative consistency check."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

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
    # MIN-2: pin kwarg propagation so a refactor flipping cache_system or
    # max_tokens trips a test failure (mirrors VIS-12 gap for narrative).
    assert mock_client.call_text.call_args.kwargs["cache_system"] is False
    assert mock_client.call_text.call_args.kwargs["max_tokens"] == 8000


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


def test_narrative_check_raises_on_unparseable_json() -> None:
    """IMP-1: malformed model response surfaces as typed RuntimeError."""
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.call_text.return_value = "not json at all"
    with pytest.raises(RuntimeError, match="unparseable JSON"):
        check_narrative(
            _empty_script(),
            cast=_cast(),
            client=mock_client,
            budget=BudgetTracker(estimate_usd=10.0),
        )


def test_narrative_check_handles_null_flags() -> None:
    """IMP-1: Anthropic occasionally returns {"flags": null}; coerce to []."""
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.call_text.return_value = json.dumps({"flags": None})
    result = check_narrative(
        _empty_script(),
        cast=_cast(),
        client=mock_client,
        budget=BudgetTracker(estimate_usd=10.0),
    )
    assert result.flags == []


def test_narrative_check_raises_on_invalid_severity() -> None:
    """IMP-1: out-of-Literal severity surfaces as typed RuntimeError."""
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.call_text.return_value = json.dumps(
        {
            "flags": [
                {
                    "page": 1,
                    "panel": 1,
                    "issue": "blah blah",
                    "severity": "critical",
                    "suggestion": None,
                }
            ]
        }
    )
    with pytest.raises(RuntimeError, match="FlagsFile schema"):
        check_narrative(
            _empty_script(),
            cast=_cast(),
            client=mock_client,
            budget=BudgetTracker(estimate_usd=10.0),
        )
