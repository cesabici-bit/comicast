"""Stage 3 — Voice direction.

Maps speaker_id -> voice_id (from SeriesProfile), translates emotion -> director's
instructions inline tag, and produces a DirectedScript for TTS.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from comicast.logging_setup import get_logger
from comicast.schemas import BubbleType, ScriptFile, SeriesProfile

log = get_logger("comicast.voice.director")

# Tag VALUES are ElevenLabs v3 verb-form per F1-T06 research (docs/research/F1-elevenlabs.md §1.3).
# Tag KEYS mirror the Pass 2b prompt emotion vocabulary at src/comicast/vision/prompts.py:69
# (past-participle: "whispered", "shouted", etc.) so that VLM output looks up cleanly here.
# Schema-level vocab tightening is tracked under VIS-06; out of T31 scope.
# Unknown emotions yield empty tag (no direction).
EMOTION_TAGS: dict[str, str] = {
    "whispered": "[whispers]",
    "shouted": "[shouts]",
    "shouting": "[shouts]",
    "yelling": "[shouts]",
    "crying": "[crying]",
    "sad": "[sad]",
    "angry": "[angry]",
    "afraid": "[afraid]",
    "scared": "[afraid]",
    "joyful": "[laughs]",
    "sighing": "[sighs]",
    "thoughtful": "",  # thought balloons get [reflective] from type, not from this map
    "casual": "",
    "neutral": "",
    "urgent": "",
}


class DirectedBubble(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    directed_text: str  # text with inline director's instructions prepended
    voice_id: str
    speaker_id: str
    confidence: float
    type: BubbleType


class DirectedPanel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int
    bubbles: list[DirectedBubble]


class DirectedPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int
    panels: list[DirectedPanel]


class DirectedScript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_name: str
    volume_id: str
    pages: list[DirectedPage]


def emotion_to_tag(emotion: str) -> str:
    return EMOTION_TAGS.get(emotion.lower().strip(), "")


def build_directed_script(
    script: ScriptFile,
    *,
    profile: SeriesProfile,
    default_narrator_voice: str | None = None,
) -> DirectedScript:
    """Produce a DirectedScript from a finalized (post-HITL) ScriptFile.

    `default_narrator_voice` is a fallback narrator voice_id used ONLY when
    `profile.voice_archetype_library` has no `__narrator__` entry.
    """
    voice_by_id: dict[str, str] = {c.id: c.voice_id for c in profile.cast if c.voice_id}
    arch = profile.voice_archetype_library

    total_in = sum(len(p.bubbles) for ps in script.pages for p in ps.panels)
    out_pages: list[DirectedPage] = []
    for ps in script.pages:
        out_panels: list[DirectedPanel] = []
        for panel in ps.panels:
            out_bubbles: list[DirectedBubble] = []
            for b in panel.bubbles:
                voice_id = voice_by_id.get(b.speaker_id)
                if voice_id is None:
                    # Reserved speakers
                    if b.speaker_id == "__narrator__":
                        voice_id = arch.get("__narrator__") or default_narrator_voice
                    elif b.speaker_id == "__sfx__":
                        voice_id = arch.get("__sfx__")
                if voice_id is None:
                    log.warning("voice.direct.no_voice", speaker=b.speaker_id, page=ps.page)
                    continue

                tag = emotion_to_tag(b.emotion)
                if b.type is BubbleType.THOUGHT:
                    tag = "[reflective] " + tag if tag else "[reflective]"
                directed_text = (tag + " " + b.text).strip() if tag else b.text

                out_bubbles.append(
                    DirectedBubble(
                        text=b.text,
                        directed_text=directed_text,
                        voice_id=voice_id,
                        speaker_id=b.speaker_id,
                        confidence=b.confidence,
                        type=b.type,
                    )
                )
            out_panels.append(DirectedPanel(order=panel.order, bubbles=out_bubbles))
        out_pages.append(DirectedPage(page=ps.page, panels=out_panels))

    total_out = sum(len(p.bubbles) for pg in out_pages for p in pg.panels)
    if total_in > 0 and total_out == 0:
        raise RuntimeError(
            f"voice.direct: 0/{total_in} bubbles received voice_id "
            f"(cast.voice_id assignments and voice_archetype_library both empty?)"
        )

    return DirectedScript(
        series_name=script.series_name, volume_id=script.volume_id, pages=out_pages
    )
