"""Stage 4b — Audio stitching with pacing rules.

Concatenates AudioClips into a single MP3 using pydub. Adds silence pauses
between clips based on panel boundary detection.
"""

from __future__ import annotations

import io
from pathlib import Path

from pydub import AudioSegment  # type: ignore[import-untyped]
from pydub.exceptions import CouldntDecodeError  # type: ignore[import-untyped]

from comicast.logging_setup import get_logger
from comicast.tts import AudioClip

log = get_logger("comicast.stitch")

PAUSE_INTRA_PANEL_MS = 150
PAUSE_INTER_PANEL_MS = 400
PAUSE_INTER_SCENE_MS = 1500
UNDECODABLE_PLACEHOLDER_MS = 200


def compute_pause_ms(prev: AudioClip, curr: AudioClip) -> int:
    if prev.page == curr.page and prev.panel_order == curr.panel_order:
        return PAUSE_INTRA_PANEL_MS
    return PAUSE_INTER_PANEL_MS


def _decode_or_silence(clip: AudioClip) -> AudioSegment:
    """STITCH-07: tolerant decode. ElevenLabs occasionally returns MP3 bytes that
    ffmpeg cannot parse (e.g. truncated frames on very-short text like 4 chars).
    Skip with structured warning + insert short silence so timing isn't lost."""
    try:
        return AudioSegment.from_file(io.BytesIO(clip.audio), format="mp3")
    except CouldntDecodeError as exc:
        log.warning(
            "stitch.clip_undecodable_skip",
            page=clip.page,
            panel_order=clip.panel_order,
            bubble_index=clip.bubble_index,
            text=clip.bubble.text[:60],
            audio_size_bytes=len(clip.audio),
            error_class=type(exc).__name__,
        )
        return AudioSegment.silent(duration=UNDECODABLE_PLACEHOLDER_MS)


def stitch_clips(
    clips: list[AudioClip], scene_breaks_at_pages: set[int] | None = None
) -> AudioSegment:
    """Concatenate clips with appropriate pauses. Scene breaks insert longer silence."""
    scene_breaks = scene_breaks_at_pages or set()
    log.info("stitch.start", n_clips=len(clips), n_scene_breaks=len(scene_breaks))
    if not clips:
        log.warning("stitch.empty_input", n_clips=0, duration_ms=0)
        return AudioSegment.silent(duration=0)

    segments: list[AudioSegment] = [_decode_or_silence(clips[0])]
    for prev, curr in zip(clips, clips[1:], strict=False):
        # STITCH-05 (deferred to T34): scene-break is suppressed for intra-page transitions
        # (prev.page == curr.page); only fires on page boundaries. Western mainstream comics
        # align chapter breaks to page boundaries — see KNOWN_ISSUES.md STITCH-05.
        if curr.page in scene_breaks and prev.page != curr.page:
            pause_ms = PAUSE_INTER_SCENE_MS
        else:
            pause_ms = compute_pause_ms(prev, curr)
        segments.append(AudioSegment.silent(duration=pause_ms))
        segments.append(_decode_or_silence(curr))

    final = segments[0]
    for s in segments[1:]:
        final = final + s
    log.info("stitch.done", n_clips=len(clips), duration_ms=len(final))
    return final


def export_mp3(segment: AudioSegment, out: Path, bitrate: str = "128k") -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    segment.export(out, format="mp3", bitrate=bitrate)
    log.info("stitch.export", path=str(out), size_bytes=out.stat().st_size)
