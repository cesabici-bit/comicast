"""L1 unit tests for ElevenLabs wrapper. Mocked — no real API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from elevenlabs import UnprocessableEntityError
from elevenlabs.core import ApiError

from comicast.budget import BudgetExceededError, BudgetTracker
from comicast.elevenlabs_client import ElevenLabsClient


@patch("comicast.elevenlabs_client.ElevenLabs")
def test_synthesize_returns_audio_bytes(MockEL: MagicMock) -> None:  # noqa: N803
    mock_client = MockEL.return_value
    # The SDK's text_to_speech.convert returns an iterator of bytes chunks
    mock_client.text_to_speech.convert.return_value = iter([b"audio", b"bytes"])

    budget = BudgetTracker(estimate_usd=10.0)
    el = ElevenLabsClient(api_key="el-test", budget=budget)
    audio = el.synthesize(text="Hello world", voice_id="EL_xyz", model_id="eleven_v3")
    assert audio == b"audiobytes"
    assert budget.spent_usd > 0  # cost recorded


@patch("comicast.elevenlabs_client.ElevenLabs")
def test_synthesize_records_chars_to_budget(MockEL: MagicMock) -> None:  # noqa: N803
    mock_client = MockEL.return_value
    mock_client.text_to_speech.convert.return_value = iter([b""])
    budget = BudgetTracker(estimate_usd=10.0)
    el = ElevenLabsClient(api_key="el-test", budget=budget)
    audio = el.synthesize(text="hello", voice_id="x", model_id="eleven_v3")
    assert audio == b""
    assert budget._records[0]["chars"] == 5


@patch("comicast.elevenlabs_client.ElevenLabs")
def test_voice_search_returns_candidates(MockEL: MagicMock) -> None:  # noqa: N803
    """Stubbed search — F1/T06 confirms exact API."""
    mock_voice = MagicMock(voice_id="EL_xyz", name="Deep Voice")
    MockEL.return_value.voices.search.return_value = MagicMock(voices=[mock_voice])
    budget = BudgetTracker(estimate_usd=10.0)
    el = ElevenLabsClient(api_key="el-test", budget=budget)
    results = el.search_voices(query="deep authoritative middle-aged man", limit=3)
    assert len(results) >= 1


@patch("comicast.elevenlabs_client.ElevenLabs")
def test_synthesize_raises_when_budget_exceeded(MockEL: MagicMock) -> None:  # noqa: N803
    """IMP-1 fix-up T30: hard-limit guard must fail-fast, NOT be swallowed by @retry.

    BudgetExceededError is a RuntimeError — Risk 3 circuit-breaker semantics require
    a single raise, not 3× retries × cost on every soft-budget breach.
    """
    MockEL.return_value.text_to_speech.convert.return_value = iter([b"audio"])
    budget = BudgetTracker(estimate_usd=0.000001)  # near-zero hard limit (2× estimate)
    el = ElevenLabsClient(api_key="el-test", budget=budget)
    with pytest.raises(BudgetExceededError):
        el.synthesize(text="hello world", voice_id="x", model_id="eleven_v3")
    # Single call — retry must NOT fire on BudgetExceededError
    assert MockEL.return_value.text_to_speech.convert.call_count == 1


@patch("comicast.elevenlabs_client.ElevenLabs")
def test_synthesize_does_not_retry_on_validation_error(MockEL: MagicMock) -> None:  # noqa: N803
    """C-1 regression T30: 422 UnprocessableEntityError must fail-fast.

    Retry on validation errors burns 3× cost+latency on calls that cannot succeed.
    The transient-predicate filters by ApiError.status_code (422 → False).
    """
    MockEL.return_value.text_to_speech.convert.side_effect = UnprocessableEntityError(
        body={"detail": "invalid voice_id"}
    )
    budget = BudgetTracker(estimate_usd=10.0)
    el = ElevenLabsClient(api_key="el-test", budget=budget)
    with pytest.raises(UnprocessableEntityError):
        el.synthesize(text="hi", voice_id="bad", model_id="eleven_v3")
    assert MockEL.return_value.text_to_speech.convert.call_count == 1


@patch("comicast.elevenlabs_client.ElevenLabs")
def test_synthesize_retries_on_transient_api_error(MockEL: MagicMock) -> None:  # noqa: N803
    """C-1 regression T30: 429/5xx ApiError must trigger retry.

    Mock raises 429 twice, then returns audio on third attempt. With
    stop_after_attempt(3) the call must succeed via 3 attempts.
    """
    MockEL.return_value.text_to_speech.convert.side_effect = [
        ApiError(status_code=429, body={"detail": "rate limited"}),
        ApiError(status_code=503, body={"detail": "server overloaded"}),
        iter([b"ok"]),
    ]
    budget = BudgetTracker(estimate_usd=10.0)
    el = ElevenLabsClient(api_key="el-test", budget=budget)
    audio = el.synthesize(text="hi", voice_id="x", model_id="eleven_v3")
    assert audio == b"ok"
    assert MockEL.return_value.text_to_speech.convert.call_count == 3
