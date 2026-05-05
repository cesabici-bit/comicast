"""L1 tests for voice assignment helpers."""

from __future__ import annotations

from comicast.schemas import CastEntry, SeriesProfile
from comicast.voice_assign import (
    cast_members_needing_voice,
    suggest_query_from_description,
)


def test_cast_members_needing_voice() -> None:
    profile = SeriesProfile(
        series_name="X",
        cast=[
            CastEntry(
                id="a",
                canonical_name="A",
                description="character A description here",
                confidence=0.9,
            ),
            CastEntry(
                id="b",
                canonical_name="B",
                description="character B description here",
                voice_id="EL_xx",
                confidence=0.9,
            ),
        ],
    )
    needing = cast_members_needing_voice(profile)
    assert len(needing) == 1
    assert needing[0].id == "a"


def test_suggest_query_extracts_age_gender_tone() -> None:
    desc = "Teenage male, ~17, dark hair. In costume: blue and yellow superhero suit. Sarcastic but kind."
    q = suggest_query_from_description(desc)
    assert "teen" in q.lower() or "young" in q.lower()
    assert "male" in q.lower() or "boy" in q.lower()
