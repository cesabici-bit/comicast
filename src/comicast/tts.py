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

    NOTE on concurrency burst-overshoot (KNOWN_ISSUES TTS-02): the assert fires
    AFTER record() and AFTER the API call returns, so under max_concurrent=N up
    to N over-budget calls may already be in flight (and billed by ElevenLabs)
    before the guard trips. Effective hard-fail granularity is therefore
    `2× estimate + N × max_call_cost`, not `2× + 1`. Acceptable in steady state;
    revisit at T39 (BudgetGuard wrapper) if tighter granularity is required.
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
        # ThreadPoolExecutor.map preserves input order, so the result is
        # already in reading order despite the parallel dispatch.
        clips_in_order = list(ex.map(_synth, tasks))

    log.info("tts.done", n_clips=len(clips_in_order))
    return clips_in_order
