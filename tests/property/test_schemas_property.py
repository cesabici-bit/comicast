"""L3 property-based tests for schemas.

This module uses Hypothesis to verify that schema invariants hold for arbitrary inputs.
Notable: T13 fix-up enforced SFX bubbles to use reserved __sfx__ speaker_id; we skip
invalid combos via assume() to avoid unsatisfiable filter ratios.
"""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from comicast.schemas import (
    Bubble,
    BubbleType,
    CastEntry,
    SeriesProfile,
)


@given(
    text=st.text(min_size=1, max_size=500),
    speaker_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_0123456789", min_size=1, max_size=64),
    emotion=st.sampled_from(["casual", "angry", "sad", "happy", "afraid", "neutral"]),
    btype=st.sampled_from(list(BubbleType)),
    x1=st.integers(0, 5000),
    y1=st.integers(0, 5000),
    w=st.integers(1, 1000),
    h=st.integers(1, 1000),
    conf=st.floats(0.0, 1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
def test_bubble_round_trip(
    text: str,
    speaker_id: str,
    emotion: str,
    btype: BubbleType,
    x1: int,
    y1: int,
    w: int,
    h: int,
    conf: float,
) -> None:
    """Any valid Bubble must round-trip through JSON.

    T13 fix-up: SFX bubbles must use reserved __sfx__; skip invalid combos.
    """
    # T13 fix-up: SFX must use reserved __sfx__; skip invalid combos
    assume(not (btype is BubbleType.SFX and speaker_id != "__sfx__"))

    b = Bubble(
        text=text,
        speaker_id=speaker_id,
        emotion=emotion,
        type=btype,
        bbox=(x1, y1, x1 + w, y1 + h),
        confidence=conf,
    )
    serialized = b.model_dump_json()
    restored = Bubble.model_validate_json(serialized)
    assert restored == b


@given(
    name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_0123456789", min_size=1, max_size=32),
    canonical=st.text(min_size=1, max_size=64),
    desc=st.text(min_size=10, max_size=500),
    conf=st.floats(0.0, 1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None)
def test_cast_entry_round_trip(name: str, canonical: str, desc: str, conf: float) -> None:
    """Any valid CastEntry must round-trip through JSON."""
    c = CastEntry(id=name, canonical_name=canonical, description=desc, confidence=conf)
    assert CastEntry.model_validate_json(c.model_dump_json()) == c


@given(series=st.text(min_size=1, max_size=64))
def test_series_profile_starts_with_zero_version(series: str) -> None:
    """SeriesProfile always initializes with version=0."""
    p = SeriesProfile(series_name=series)
    assert p.version == 0
    assert p.volumes_processed == []
