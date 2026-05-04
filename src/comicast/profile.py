"""Series profile manager — read, update, and persist SeriesProfile."""

from __future__ import annotations

import json
from pathlib import Path

from comicast.logging_setup import get_logger
from comicast.schemas import CastEntry, CastFile, SeriesProfile

log = get_logger("comicast.profile")


def load_profile(path: Path, *, series_name: str) -> SeriesProfile:
    """Read SeriesProfile from JSON at `path`, or create an empty one if missing."""
    log.info("profile.load.start", path=str(path), series_name=series_name)
    if not path.exists():
        log.warning("profile.load.missing", path=str(path), series_name=series_name)
        return SeriesProfile(series_name=series_name)
    data = json.loads(path.read_text(encoding="utf-8"))
    p = SeriesProfile.model_validate(data)
    log.info("profile.load.done", series_name=p.series_name, version=p.version, n_cast=len(p.cast))
    return p


def save_profile(profile: SeriesProfile, path: Path) -> None:
    """Write `profile` to `path` as indented JSON (UTF-8); creates parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    log.info("profile.saved", path=str(path), version=profile.version, n_cast=len(profile.cast))


def upsert_cast_from_extraction(profile: SeriesProfile, cast_file: CastFile) -> SeriesProfile:
    """Merge a new cast extraction into the existing profile.

    For each character:
    - If new, append.
    - If existing, update canonical_name and description (extraction is fresher),
      but PRESERVE voice_id, voice_archetype, user_confirmations, user_corrections.
    """
    log.info(
        "profile.upsert.start",
        series_name=profile.series_name,
        n_existing=len(profile.cast),
        n_extraction=len(cast_file.cast),
    )
    n_added = 0
    n_updated = 0
    by_id: dict[str, CastEntry] = {c.id: c for c in profile.cast}
    for entry in cast_file.cast:
        if entry.id in by_id:
            existing = by_id[entry.id]
            existing.canonical_name = entry.canonical_name
            existing.aliases = list(set(existing.aliases) | set(entry.aliases))
            existing.description = entry.description
            # PRESERVE voice_id, voice_archetype, user_confirmations, user_corrections
            n_updated += 1
        else:
            by_id[entry.id] = entry
            n_added += 1
    profile.cast = list(by_id.values())
    log.info(
        "profile.upsert.done",
        series_name=profile.series_name,
        n_total=len(profile.cast),
        n_added=n_added,
        n_updated=n_updated,
    )
    return profile


def apply_correction(
    profile: SeriesProfile,
    *,
    character_id: str,
    correction_type: str,
    details: str,
) -> None:
    """Increment counters when user corrects an attribution.

    correction_type ∈ {speaker_attribution, emotion, type, voice_id_change, ...}
    details: free text for audit trail (also written to corrections.jsonl).
    """
    for c in profile.cast:
        if c.id == character_id:
            c.user_corrections += 1
            log.info(
                "profile.correction",
                character=character_id,
                type=correction_type,
                details=details,
                user_corrections=c.user_corrections,
            )
            return
    log.warning("profile.correction.unknown_character", character=character_id)
