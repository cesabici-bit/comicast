"""L1 tests for M4B chapter generation."""

from __future__ import annotations

from comicast.m4b import detect_scene_breaks
from comicast.schemas import (
    Bubble,
    BubbleType,
    PageScript,
    Panel,
    ScriptFile,
)


def _page(n: int, narration_text: str | None = None) -> PageScript:
    bubbles = []
    if narration_text:
        bubbles.append(
            Bubble(
                text=narration_text,
                speaker_id="__narrator__",
                emotion="neutral",
                type=BubbleType.NARRATION,
                bbox=(0, 0, 1, 1),
                confidence=0.9,
            )
        )
    return PageScript(page=n, panels=[Panel(order=1, bubbles=bubbles)])


def test_detect_scene_breaks_finds_chapter_markers() -> None:
    """Pages with narration boxes that look like chapter titles are scene breaks."""
    script = ScriptFile(
        series_name="X",
        volume_id="v1",
        pages=[
            _page(1, "Chapter 1: The Beginning"),
            _page(2),
            _page(3, "Chapter 2: Rising Action"),
            _page(4),
        ],
    )
    breaks = detect_scene_breaks(script)
    assert 1 in breaks
    assert 3 in breaks
    assert 2 not in breaks


def test_detect_scene_breaks_no_chapters_returns_empty() -> None:
    script = ScriptFile(series_name="X", volume_id="v1", pages=[_page(1), _page(2)])
    assert detect_scene_breaks(script) == set()
