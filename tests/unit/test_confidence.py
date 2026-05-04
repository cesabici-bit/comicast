"""L1 tests for confidence-based filtering."""

from __future__ import annotations

from comicast.schemas import Bubble, BubbleType, PageScript, Panel, ScriptFile
from comicast.vision.confidence import (
    bubbles_needing_review,
    page_average_confidence,
)


def _mk_bubble(conf: float) -> Bubble:
    return Bubble(
        text="x",
        speaker_id="x",
        emotion="x",
        type=BubbleType.DIALOGUE,
        bbox=(0, 0, 1, 1),
        confidence=conf,
    )


def test_bubbles_below_threshold_returned() -> None:
    page = PageScript(
        page=1,
        panels=[
            Panel(
                order=1,
                bubbles=[
                    _mk_bubble(0.5),
                    _mk_bubble(0.9),
                    _mk_bubble(0.65),
                ],
            )
        ],
    )
    script = ScriptFile(series_name="x", volume_id="x", pages=[page])
    low = list(bubbles_needing_review(script, threshold=0.7))
    assert len(low) == 2  # 0.5 and 0.65


def test_page_average_confidence() -> None:
    page = PageScript(
        page=1,
        panels=[
            Panel(
                order=1,
                bubbles=[
                    _mk_bubble(0.4),
                    _mk_bubble(0.6),
                ],
            )
        ],
    )
    avg = page_average_confidence(page)
    assert abs(avg - 0.5) < 1e-6


def test_page_with_no_bubbles_returns_one_zero_confidence() -> None:
    """An empty page is treated as 'no info' — confidence 0."""
    page = PageScript(page=1, panels=[Panel(order=1, bubbles=[])])
    assert page_average_confidence(page) == 0.0
