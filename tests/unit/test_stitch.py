"""L1 tests for audio stitching pacing."""

from __future__ import annotations

from comicast.schemas import BubbleType
from comicast.stitch import compute_pause_ms, stitch_clips  # noqa: F401
from comicast.tts import AudioClip
from comicast.voice.director import DirectedBubble


def _b() -> DirectedBubble:
    return DirectedBubble(
        text="x",
        directed_text="x",
        voice_id="V",
        speaker_id="y",
        confidence=0.9,
        type=BubbleType.DIALOGUE,
    )


def test_compute_pause_intra_panel() -> None:
    """Two bubbles in same panel: short pause (~150ms)."""
    a = AudioClip(page=1, panel_order=1, bubble_index=0, bubble=_b(), audio=b"")
    b = AudioClip(page=1, panel_order=1, bubble_index=1, bubble=_b(), audio=b"")
    assert compute_pause_ms(a, b) == 150


def test_compute_pause_inter_panel() -> None:
    a = AudioClip(page=1, panel_order=1, bubble_index=0, bubble=_b(), audio=b"")
    b = AudioClip(page=1, panel_order=2, bubble_index=0, bubble=_b(), audio=b"")
    assert compute_pause_ms(a, b) == 400


def test_compute_pause_inter_page_treated_like_panel() -> None:
    a = AudioClip(page=1, panel_order=3, bubble_index=0, bubble=_b(), audio=b"")
    b = AudioClip(page=2, panel_order=1, bubble_index=0, bubble=_b(), audio=b"")
    assert compute_pause_ms(a, b) == 400  # default; chapter break detection comes later
