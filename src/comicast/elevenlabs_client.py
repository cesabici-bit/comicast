"""ElevenLabs SDK wrapper — TTS + voice search + budget tracking."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from elevenlabs import ElevenLabs
from elevenlabs.core import ApiError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from comicast.budget import BudgetTracker
from comicast.logging_setup import get_logger

log = get_logger("comicast.elevenlabs")


def _is_transient_elevenlabs(exc: BaseException) -> bool:
    """Predicate for tenacity retry: True only on transient ElevenLabs/network errors.

    The ElevenLabs Python SDK 2.x has no typed RateLimitError or 5xx subclass:
    422 raises elevenlabs.UnprocessableEntityError (subclass of ApiError),
    everything else (429, 5xx) raises bare elevenlabs.core.ApiError(status_code=N).
    Retry only on 429 (rate-limit) and 5xx (server error). 422 and other 4xx
    (auth/permission/validation) must fail-fast — they will not succeed on retry
    and burn cost+latency. BudgetExceededError (RuntimeError subclass) also
    fails-fast: the hard-limit circuit-breaker must NOT become a 3× cost multiplier.
    Network errors (httpx ConnectError, TimeoutException) are transient → retry.
    """
    if isinstance(exc, ApiError):
        code = exc.status_code
        if code is None:
            return True  # unknown status — treat as transient
        return code == 429 or code >= 500
    try:
        import httpx

        return isinstance(exc, httpx.ConnectError | httpx.TimeoutException)
    except ImportError:
        return False


@dataclass
class VoiceCandidate:
    voice_id: str
    name: str
    description: str = ""


class ElevenLabsClient:
    def __init__(
        self,
        *,
        budget: BudgetTracker,
        api_key: str | None = None,
    ) -> None:
        key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if key is None:
            raise RuntimeError("ELEVENLABS_API_KEY not set")
        self._client = ElevenLabs(api_key=key)
        self.budget = budget

    @retry(
        retry=retry_if_exception(_is_transient_elevenlabs),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        reraise=True,
    )
    def synthesize(
        self,
        *,
        text: str,
        voice_id: str,
        model_id: str = "eleven_v3",
        output_format: str = "mp3_44100_128",
    ) -> bytes:
        """Convert text to audio bytes. Record cost to budget."""
        log.info("elevenlabs.synthesize", voice_id=voice_id, chars=len(text))
        audio_iter: Any = self._client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format=output_format,
        )
        audio = b"".join(audio_iter)
        self.budget.record(provider="elevenlabs", chars=len(text))
        self.budget.assert_under_hard_limit()
        return audio

    def search_voices(self, *, query: str, limit: int = 5) -> list[VoiceCandidate]:
        """Search the voice library by natural language description.

        NOTE (T30 stub): This calls voices.search() (GET /v2/voices — workspace voices).
        Per F1-elevenlabs.md §1.3, Pass 3 voice discovery MUST use voices.get_shared()
        (GET /v1/shared-voices) to access structured gender/age/accent/descriptives fields.
        The correct endpoint is deferred to T19+. This stub is intentionally best-effort.
        """
        log.info("elevenlabs.search_voices", query=query, limit=limit)
        # The SDK shape varies — F1/T06 confirms exact method. This is a best-effort.
        result = self._client.voices.search(search=query, page_size=limit)
        candidates: list[VoiceCandidate] = []
        for v in getattr(result, "voices", []):
            # NOTE (T19 follow-up): when migrating to voices.get_shared(), change
            # extraction to getattr(v, "descriptive", "") — the /v1/shared-voices
            # field is "descriptive" (singular), NOT "description". See
            # F1-elevenlabs.md:245 and KNOWN_ISSUES.md AUD-04.
            candidates.append(
                VoiceCandidate(
                    voice_id=v.voice_id,
                    name=v.name,
                    description=getattr(v, "description", "") or "",
                )
            )
        if not candidates:
            log.warning("elevenlabs.search_voices.no_candidates", query=query, limit=limit)
        return candidates
