"""Stage 4c — M4B export with chapter markers."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from comicast.logging_setup import get_logger
from comicast.schemas import BubbleType, ScriptFile
from comicast.tts import AudioClip

log = get_logger("comicast.m4b")

# Heuristic: a narration bubble whose text starts with a chapter keyword
# (chapter / part / episode / prologue / epilogue / act, case-insensitive) is
# treated as a scene break. ALL-CAPS-without-keyword heuristic deferred to T44
# (see KNOWN_ISSUES M4B-05).
CHAPTER_RE = re.compile(r"^\s*(chapter|part|episode|prologue|epilogue|act)\b", re.IGNORECASE)


def detect_scene_breaks(script: ScriptFile) -> set[int]:
    """Return page numbers that begin a new scene/chapter."""
    log.info("m4b.detect.start", n_pages=len(script.pages))
    breaks: set[int] = set()
    for ps in script.pages:
        for panel in ps.panels:
            for b in panel.bubbles:
                if b.type is BubbleType.NARRATION and CHAPTER_RE.match(b.text):
                    breaks.add(ps.page)
    log.info("m4b.detect.done", n_breaks=len(breaks))
    return breaks


def build_chapter_offsets_ms(
    clips: list[AudioClip], scene_breaks_at_pages: set[int]
) -> list[tuple[int, str]]:
    """Compute (offset_ms, title) for each chapter marker.

    Walks clips in order, accumulates duration estimates (using clip lengths in
    ms — caller must have decoded). For F3 first cut, durations are approximate;
    F4 refines using actual ffprobe-measured durations.
    """
    # Placeholder simple model: each clip ~2000ms + pauses. Accurate length comes from stitch step.
    raise NotImplementedError(
        "Caller passes already-stitched offsets in T39 orchestration. "
        "T34's job is the heuristic detection in detect_scene_breaks() above."
    )


def export_m4b_with_chapters(
    mp3_path: Path,
    out_path: Path,
    chapters: list[tuple[int, str]],  # [(offset_ms, title), ...]
) -> None:
    """Use ffmpeg to wrap MP3 → M4B with chapter metadata.

    Implementation note: ffmpeg requires a chapters metadata file. Build it
    on the fly and pipe to -i.
    """
    log.info(
        "m4b.export.start",
        mp3=str(mp3_path),
        out=str(out_path),
        n_chapters=len(chapters),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_lines = [";FFMETADATA1"]
    for i, (offset_ms, title) in enumerate(chapters):
        end_ms = chapters[i + 1][0] if i + 1 < len(chapters) else offset_ms + 1
        metadata_lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={offset_ms}",
                f"END={end_ms}",
                f"title={title}",
            ]
        )
    metadata = "\n".join(metadata_lines)
    metadata_file = out_path.with_suffix(".metadata.txt")
    metadata_file.write_text(metadata)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(mp3_path),
                "-i",
                str(metadata_file),
                "-map_metadata",
                "1",
                "-codec",
                "copy",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
        log.info(
            "m4b.export.done",
            path=str(out_path),
            n_chapters=len(chapters),
            size_bytes=out_path.stat().st_size,
        )
    finally:
        metadata_file.unlink(missing_ok=True)
