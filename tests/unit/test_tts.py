"""L1 tests for TTS generation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from comicast.budget import BudgetTracker
from comicast.schemas import BubbleType
from comicast.tts import generate_audio
from comicast.voice.director import DirectedBubble, DirectedPage, DirectedPanel, DirectedScript


def _ds() -> DirectedScript:
    b1 = DirectedBubble(
        text="hi",
        directed_text="hi",
        voice_id="V1",
        speaker_id="x",
        confidence=0.9,
        type=BubbleType.DIALOGUE,
    )
    b2 = DirectedBubble(
        text="bye",
        directed_text="[whispers] bye",
        voice_id="V2",
        speaker_id="y",
        confidence=0.9,
        type=BubbleType.DIALOGUE,
    )
    return DirectedScript(
        series_name="X",
        volume_id="v1",
        pages=[
            DirectedPage(page=1, panels=[DirectedPanel(order=1, bubbles=[b1, b2])]),
        ],
    )


@patch("comicast.tts.ElevenLabsClient")
def test_generate_audio_returns_one_clip_per_bubble(MockEL: MagicMock) -> None:  # noqa: N803
    mock = MockEL.return_value
    mock.synthesize.side_effect = [b"audio1", b"audio2"]
    budget = BudgetTracker(estimate_usd=10.0)
    clips = generate_audio(_ds(), client=mock, budget=budget, max_concurrent=2)
    assert len(clips) == 2
    assert clips[0].audio == b"audio1"
    assert clips[0].bubble.voice_id == "V1"


@patch("comicast.tts.ElevenLabsClient")
def test_generate_audio_preserves_reading_order(MockEL: MagicMock) -> None:  # noqa: N803
    mock = MockEL.return_value
    # Even with parallelism, output must be in the original order.
    mock.synthesize.side_effect = lambda **kw: f"audio_{kw['voice_id']}".encode()
    budget = BudgetTracker(estimate_usd=10.0)
    clips = generate_audio(_ds(), client=mock, budget=budget, max_concurrent=4)
    assert [c.bubble.voice_id for c in clips] == ["V1", "V2"]
