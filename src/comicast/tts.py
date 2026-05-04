"""Stage 4a — TTS per-bubble generation, parallelized."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from comicast.budget import BudgetTracker
from comicast.elevenlabs_client import ElevenLabsClient
from comicast.logging_setup import get_logger
from comicast.voice.director import DirectedBubble, DirectedScript

log = get_logger("comicast.tts")


@dataclass
class AudioClip:
    page: int
    panel_order: int
    bubble_index: int
    bubble: DirectedBubble
    audio: bytes


def generate_audio(
    script: DirectedScript,
    *,
    client: ElevenLabsClient,
    budget: BudgetTracker,
    max_concurrent: int = 8,
    model_id: str = "eleven_v3",
) -> list[AudioClip]:
    """Generate one audio clip per bubble, preserving reading order in result.

    Budget hard-fail enforced inside ElevenLabsClient.synthesize per call
    (elevenlabs_client.py:88 — budget.assert_under_hard_limit() called after
    each cost record). T17 lesson cross-applied; no per-loop guard needed here.
    See KNOWN_ISSUES BG-01 for rationale on raise-not-assert semantics.
    """
    tasks: list[tuple[int, int, int, DirectedBubble]] = []
    for page in script.pages:
        for panel in page.panels:
            for idx, bubble in enumerate(panel.bubbles):
                tasks.append((page.page, panel.order, idx, bubble))

    log.info("tts.start", n_bubbles=len(tasks), concurrency=max_concurrent)

    def _synth(t: tuple[int, int, int, DirectedBubble]) -> AudioClip:
        page, panel_order, idx, bubble = t
        audio = client.synthesize(
            text=bubble.directed_text,
            voice_id=bubble.voice_id,
            model_id=model_id,
        )
        return AudioClip(
            page=page,
            panel_order=panel_order,
            bubble_index=idx,
            bubble=bubble,
            audio=audio,
        )

    with ThreadPoolExecutor(max_workers=max_concurrent) as ex:
        results_unordered = list(ex.map(_synth, tasks))

    # ThreadPoolExecutor.map preserves input order.
    log.info("tts.done", n_clips=len(results_unordered))
    return results_unordered
