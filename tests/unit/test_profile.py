"""L1 tests for SeriesProfile read/update/write."""

from __future__ import annotations

from pathlib import Path

from comicast.profile import (
    apply_correction,
    load_profile,
    save_profile,
    upsert_cast_from_extraction,
)
from comicast.schemas import CastEntry, CastFile, SeriesProfile


def test_load_creates_empty_if_missing(tmp_path: Path) -> None:
    p = load_profile(tmp_path / "missing.json", series_name="Invincible")
    assert p.series_name == "Invincible"
    assert p.version == 0


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    file = tmp_path / "p.json"
    p = SeriesProfile(series_name="X", version=2)
    save_profile(p, file)
    loaded = load_profile(file, series_name="X")
    assert loaded.version == 2


def test_upsert_cast_adds_new_chars(tmp_path: Path) -> None:
    profile = SeriesProfile(series_name="X")
    cast_file = CastFile(
        series_name="X",
        cast=[
            CastEntry(
                id="mark",
                canonical_name="Mark",
                description="kid in suit, dark hair",
                confidence=0.9,
            ),
        ],
    )
    updated = upsert_cast_from_extraction(profile, cast_file)
    assert len(updated.cast) == 1
    assert updated.cast[0].id == "mark"


def test_upsert_cast_preserves_existing_voice_id() -> None:
    """If the user already assigned a voice, don't overwrite from new extraction."""
    profile = SeriesProfile(
        series_name="X",
        cast=[
            CastEntry(
                id="mark",
                canonical_name="Mark",
                description="user-edited description here",
                voice_id="EL_user",
                confidence=0.5,
            ),
        ],
    )
    cast_file = CastFile(
        series_name="X",
        cast=[
            CastEntry(
                id="mark",
                canonical_name="Mark Grayson",
                description="extraction's new description text",
                confidence=0.95,
            ),
        ],
    )
    updated = upsert_cast_from_extraction(profile, cast_file)
    mark = next(c for c in updated.cast if c.id == "mark")
    assert mark.voice_id == "EL_user"  # preserved
    assert mark.canonical_name == "Mark Grayson"  # updated


def test_apply_correction_increments_user_corrections() -> None:
    profile = SeriesProfile(
        series_name="X",
        cast=[
            CastEntry(
                id="mark",
                canonical_name="Mark",
                description="ten chars or more please here ok",
                confidence=0.9,
            ),
        ],
    )
    apply_correction(
        profile,
        character_id="mark",
        correction_type="speaker_attribution",
        details="user changed from atom_eve → mark",
    )
    assert profile.cast[0].user_corrections == 1
