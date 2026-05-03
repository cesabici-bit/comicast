"""L3 property-based tests for schemas.

This module uses Hypothesis to verify that schema invariants hold for arbitrary inputs.
Notable: T14 fix-up uses co-generated strategy to avoid invalid SFX combos rejected by
`Bubble._sfx_uses_reserved_speaker`.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from comicast.schemas import (
    Bubble,
    BubbleType,
    CastEntry,
    SeriesProfile,
)

# Co-generated strategy: avoid invalid SFX-speaker_id combos that would be rejected
# by Bubble._sfx_uses_reserved_speaker validator (schemas.py:38-42).
btype_and_speaker = st.one_of(
    st.tuples(
        st.just(BubbleType.SFX),
        st.just("__sfx__"),
    ),
    st.tuples(
        st.sampled_from([BubbleType.DIALOGUE, BubbleType.THOUGHT, BubbleType.NARRATION]),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz_0123456789", min_size=1, max_size=64),
    ),
)


@given(
    text=st.text(min_size=1, max_size=500),
    btype_and_speaker=btype_and_speaker,
    emotion=st.sampled_from(["casual", "angry", "sad", "happy", "afraid", "neutral"]),
    x1=st.integers(0, 5000),
    y1=st.integers(0, 5000),
    w=st.integers(1, 1000),
    h=st.integers(1, 1000),
    conf=st.floats(0.0, 1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
def test_bubble_round_trip(
    text: str,
    btype_and_speaker: tuple[BubbleType, str],
    emotion: str,
    x1: int,
    y1: int,
    w: int,
    h: int,
    conf: float,
) -> None:
    """Any valid Bubble must round-trip through JSON.

    The strategy avoids the SFX-vs-non-__sfx__ invalid combo enforced by the
    schema validator `_sfx_uses_reserved_speaker` (schemas.py).
    """
    btype, speaker_id = btype_and_speaker

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
    cast_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_0123456789", min_size=1, max_size=32),
    canonical=st.text(min_size=1, max_size=64),
    desc=st.text(min_size=10, max_size=500),
    conf=st.floats(0.0, 1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None)
def test_cast_entry_round_trip(cast_id: str, canonical: str, desc: str, conf: float) -> None:
    """Any valid CastEntry must round-trip through JSON."""
    c = CastEntry(id=cast_id, canonical_name=canonical, description=desc, confidence=conf)
    assert CastEntry.model_validate_json(c.model_dump_json()) == c


@given(series=st.text(min_size=1, max_size=64))
@settings(max_examples=100, deadline=None)
def test_series_profile_starts_with_zero_version(series: str) -> None:
    """SeriesProfile always initializes with version=0."""
    p = SeriesProfile(series_name=series)
    assert p.version == 0
    assert p.volumes_processed == []
