"""Stage 4b — Audio stitching with pacing rules.

Concatenates AudioClips into a single MP3 using pydub. Adds silence pauses
between clips based on panel boundary detection.
"""

from __future__ import annotations

import io
from pathlib import Path

from pydub import AudioSegment  # type: ignore[import-untyped]

from comicast.logging_setup import get_logger
from comicast.tts import AudioClip

log = get_logger("comicast.stitch")

PAUSE_INTRA_PANEL_MS = 150
PAUSE_INTER_PANEL_MS = 400
PAUSE_INTER_SCENE_MS = 1500


def compute_pause_ms(prev: AudioClip, curr: AudioClip) -> int:
    if prev.page == curr.page and prev.panel_order == curr.panel_order:
        return PAUSE_INTRA_PANEL_MS
    return PAUSE_INTER_PANEL_MS


def stitch_clips(
    clips: list[AudioClip], scene_breaks_at_pages: set[int] | None = None
) -> AudioSegment:
    """Concatenate clips with appropriate pauses. Scene breaks insert longer silence."""
    scene_breaks = scene_breaks_at_pages or set()
    if not clips:
        return AudioSegment.silent(duration=0)

    segments: list[AudioSegment] = [
        AudioSegment.from_file(io.BytesIO(clips[0].audio), format="mp3")
    ]
    for prev, curr in zip(clips, clips[1:], strict=False):
        if curr.page in scene_breaks and prev.page != curr.page:
            pause_ms = PAUSE_INTER_SCENE_MS
        else:
            pause_ms = compute_pause_ms(prev, curr)
        segments.append(AudioSegment.silent(duration=pause_ms))
        segments.append(AudioSegment.from_file(io.BytesIO(curr.audio), format="mp3"))

    final = segments[0]
    for s in segments[1:]:
        final = final + s
    log.info("stitch.done", n_clips=len(clips), duration_ms=len(final))
    return final


def export_mp3(segment: AudioSegment, out: Path, bitrate: str = "128k") -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    segment.export(out, format="mp3", bitrate=bitrate)
    log.info("stitch.export", path=str(out), size_bytes=out.stat().st_size)
