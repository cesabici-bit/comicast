"""L1 tests for voice direction."""

from __future__ import annotations

import pytest

from comicast.schemas import (
    Bubble,
    BubbleType,
    CastEntry,
    PageScript,
    Panel,
    ScriptFile,
    SeriesProfile,
)
from comicast.voice.director import build_directed_script, emotion_to_tag


def _profile_with_voice() -> SeriesProfile:
    return SeriesProfile(
        series_name="Invincible",
        cast=[
            CastEntry(
                id="mark_grayson",
                canonical_name="Mark Grayson",
                aliases=["Mark"],
                description="Teen male, dark hair, blue/yellow costume, sarcastic",
                voice_id="EL_xyz",
                confidence=0.95,
            )
        ],
    )


def _script() -> ScriptFile:
    bubble = Bubble(
        text="Hello!",
        speaker_id="mark_grayson",
        emotion="shouted",
        type=BubbleType.DIALOGUE,
        bbox=(0, 0, 1, 1),
        confidence=0.9,
    )
    return ScriptFile(
        series_name="Invincible",
        volume_id="vol_1",
        pages=[PageScript(page=1, panels=[Panel(order=1, bubbles=[bubble])])],
    )


def test_emotion_to_tag_known() -> None:
    assert emotion_to_tag("whispered") == "[whispers]"
    assert emotion_to_tag("shouted") == "[shouts]"


def test_emotion_to_tag_unknown_returns_empty() -> None:
    assert emotion_to_tag("blissful") == ""


def test_build_directed_script_attaches_voice_id() -> None:
    directed = build_directed_script(_script(), profile=_profile_with_voice())
    bubble = directed.pages[0].panels[0].bubbles[0]
    assert bubble.voice_id == "EL_xyz"
    assert bubble.directed_text.startswith("[shouts]")


def test_build_directed_script_thought_uses_reflective() -> None:
    bubble = Bubble(
        text="hmm",
        speaker_id="mark_grayson",
        emotion="thoughtful",
        type=BubbleType.THOUGHT,
        bbox=(0, 0, 1, 1),
        confidence=0.9,
    )
    script = ScriptFile(
        series_name="Invincible",
        volume_id="v1",
        pages=[PageScript(page=1, panels=[Panel(order=1, bubbles=[bubble])])],
    )
    directed = build_directed_script(script, profile=_profile_with_voice())
    assert "[reflective]" in directed.pages[0].panels[0].bubbles[0].directed_text


def test_sfx_bubble_uses_default_sfx_voice() -> None:
    bubble = Bubble(
        text="KRRAAANG",
        speaker_id="__sfx__",
        emotion="loud",
        type=BubbleType.SFX,
        bbox=(0, 0, 1, 1),
        confidence=0.99,
    )
    script = ScriptFile(
        series_name="Invincible",
        volume_id="v1",
        pages=[PageScript(page=1, panels=[Panel(order=1, bubbles=[bubble])])],
    )
    profile = _profile_with_voice()
    profile.voice_archetype_library["__sfx__"] = "EL_sfx"
    directed = build_directed_script(script, profile=profile)
    assert directed.pages[0].panels[0].bubbles[0].voice_id == "EL_sfx"


def test_build_directed_script_raises_when_all_bubbles_miss_voice() -> None:
    """IMP-1: cardinality invariant — Risk 4 mirror of cast.py:69-72 / attribute.py:73-76.

    If 100% of input bubbles fail voice resolution, raise rather than silently
    return an empty DirectedScript (which would be indistinguishable from a
    legitimate no-data run downstream in TTS / stitching).
    """
    bubble = Bubble(
        text="who am I?",
        speaker_id="unknown_speaker",  # NOT in cast, NOT a reserved sentinel
        emotion="casual",
        type=BubbleType.DIALOGUE,
        bbox=(0, 0, 1, 1),
        confidence=0.5,
    )
    script = ScriptFile(
        series_name="Invincible",
        volume_id="v1",
        pages=[PageScript(page=1, panels=[Panel(order=1, bubbles=[bubble])])],
    )
    empty_profile = SeriesProfile(series_name="Invincible", cast=[])
    with pytest.raises(RuntimeError, match=r"0/1 bubbles received voice_id"):
        build_directed_script(script, profile=empty_profile)


def test_build_directed_script_uses_default_narrator_voice_fallback() -> None:
    """MIN-2 (a)+(c)+MIN-4: when archetype library has no __narrator__,
    the `default_narrator_voice` arg fills the gap.
    """
    bubble = Bubble(
        text="Meanwhile, in space...",
        speaker_id="__narrator__",
        emotion="neutral",
        type=BubbleType.NARRATION,
        bbox=(0, 0, 1, 1),
        confidence=0.95,
    )
    script = ScriptFile(
        series_name="Invincible",
        volume_id="v1",
        pages=[PageScript(page=1, panels=[Panel(order=1, bubbles=[bubble])])],
    )
    profile = _profile_with_voice()  # voice_archetype_library is {} by default
    directed = build_directed_script(
        script, profile=profile, default_narrator_voice="EL_narrator_default"
    )
    assert directed.pages[0].panels[0].bubbles[0].voice_id == "EL_narrator_default"


def test_narration_with_shouted_emotion_keeps_shouts_tag_no_reflective() -> None:
    """VOI-03 (b): NARRATION type + emotion=shouted should preserve [shouts] tag
    WITHOUT prepending [reflective] (which is gated on THOUGHT type only, see director.py:110-111).

    This test locks the design: NARRATION is a distinct type from THOUGHT,
    and emotion tags apply uniformly regardless of type, except that THOUGHT
    type specifically adds [reflective] prefix in addition to the emotion tag.
    """
    bubble = Bubble(
        text="The blast was incredible!",
        speaker_id="__narrator__",
        emotion="shouted",
        type=BubbleType.NARRATION,
        bbox=(0, 0, 1, 1),
        confidence=0.95,
    )
    script = ScriptFile(
        series_name="Invincible",
        volume_id="v1",
        pages=[PageScript(page=1, panels=[Panel(order=1, bubbles=[bubble])])],
    )
    profile = _profile_with_voice()
    profile.voice_archetype_library["__narrator__"] = "EL_narrator"
    directed = build_directed_script(script, profile=profile)
    directed_bubble = directed.pages[0].panels[0].bubbles[0]

    # Should have [shouts] because emotion="shouted"
    assert "[shouts]" in directed_bubble.directed_text
    # Should NOT have [reflective] because NARRATION type, not THOUGHT type
    assert "[reflective]" not in directed_bubble.directed_text
    # Verify the exact form: emotion tag followed by text
    assert directed_bubble.directed_text == "[shouts] The blast was incredible!"


def test_narration_with_empty_emotion_has_no_tag() -> None:
    """VOI-03 (c) boundary: NARRATION + emotion="" should produce directed_text
    with no tag prefix, because emotion_to_tag("") returns "" and NARRATION type
    doesn't prepend [reflective] unconditionally.
    """
    bubble = Bubble(
        text="The story continues.",
        speaker_id="__narrator__",
        emotion="",
        type=BubbleType.NARRATION,
        bbox=(0, 0, 1, 1),
        confidence=0.95,
    )
    script = ScriptFile(
        series_name="Invincible",
        volume_id="v1",
        pages=[PageScript(page=1, panels=[Panel(order=1, bubbles=[bubble])])],
    )
    profile = _profile_with_voice()
    profile.voice_archetype_library["__narrator__"] = "EL_narrator"
    directed = build_directed_script(script, profile=profile)
    directed_bubble = directed.pages[0].panels[0].bubbles[0]

    # Empty emotion should produce no tag
    assert directed_bubble.directed_text == "The story continues."
    assert "[" not in directed_bubble.directed_text  # No tag markers


def test_thought_with_emotion_tag_prepends_reflective() -> None:
    """VOI-03 (b) cross-product: THOUGHT type with emotion tag should prepend [reflective]
    in addition to the emotion tag (contrast with NARRATION, which does not).

    This test strengthens the distinction: THOUGHT + emotion="shouted" should produce
    "[reflective] [shouts] text", not just "[shouts] text".
    """
    bubble = Bubble(
        text="This is overwhelming!",
        speaker_id="mark_grayson",
        emotion="shouted",
        type=BubbleType.THOUGHT,
        bbox=(0, 0, 1, 1),
        confidence=0.9,
    )
    script = ScriptFile(
        series_name="Invincible",
        volume_id="v1",
        pages=[PageScript(page=1, panels=[Panel(order=1, bubbles=[bubble])])],
    )
    directed = build_directed_script(script, profile=_profile_with_voice())
    directed_bubble = directed.pages[0].panels[0].bubbles[0]

    # THOUGHT with emotion="shouted" should have BOTH [reflective] and [shouts]
    assert directed_bubble.directed_text == "[reflective] [shouts] This is overwhelming!"
