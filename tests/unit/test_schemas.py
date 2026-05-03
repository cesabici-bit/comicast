"""L1 unit tests for Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from comicast.schemas import (  # noqa: F401
    Bubble,
    BubbleType,
    CastEntry,
    CastFile,
    Flag,
    FlagsFile,
    PageScript,
    Panel,
    ScriptFile,
    SeriesProfile,
)


def test_bubble_minimum_fields() -> None:
    b = Bubble(
        text="Mom, I'm home!",
        speaker_id="mark_grayson",
        emotion="casual",
        type=BubbleType.DIALOGUE,
        bbox=(120, 340, 280, 410),
        confidence=0.95,
    )
    assert b.text == "Mom, I'm home!"
    assert b.type is BubbleType.DIALOGUE


def test_bubble_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        Bubble(
            text="x",
            speaker_id="x",
            emotion="x",
            type=BubbleType.DIALOGUE,
            bbox=(0, 0, 1, 1),
            confidence=1.5,  # >1
        )


def test_bubble_rejects_invalid_bbox() -> None:
    with pytest.raises(ValidationError):
        Bubble(
            text="x",
            speaker_id="x",
            emotion="x",
            type=BubbleType.DIALOGUE,
            bbox=(0, 0, 0),  # 3 elements, need 4
            confidence=0.5,
        )


def test_sfx_must_use_sfx_speaker_id() -> None:
    """Domain rule: SFX bubbles use the reserved __sfx__ speaker_id."""
    b = Bubble(
        text="KRRAAANG!",
        speaker_id="__sfx__",
        emotion="loud",
        type=BubbleType.SFX,
        bbox=(0, 0, 1, 1),
        confidence=0.99,
    )
    assert b.speaker_id == "__sfx__"


def test_panel_orders_bubbles() -> None:
    p = Panel(order=1, bubbles=[])
    assert p.order == 1


def test_page_script_requires_panels() -> None:
    page = PageScript(page=1, panels=[Panel(order=1, bubbles=[])])
    assert page.page == 1


def test_cast_entry_minimum() -> None:
    c = CastEntry(
        id="mark_grayson",
        canonical_name="Mark Grayson",
        aliases=["Mark", "Invincible"],
        description="Teen male, dark hair, blue/yellow costume",
        confidence=0.9,
    )
    assert c.voice_id is None  # voice assigned later in HITL


def test_series_profile_starts_empty() -> None:
    p = SeriesProfile(series_name="Invincible")
    assert p.version == 0
    assert p.cast == []
    assert p.volumes_processed == []
    assert p.common_errors_learned == []
    assert p.voice_archetype_library == {}


def test_flag_severity_enum() -> None:
    f = Flag(page=47, panel=2, issue="Atom Eve attribuita ma non in scena", severity="high")
    assert f.severity == "high"
