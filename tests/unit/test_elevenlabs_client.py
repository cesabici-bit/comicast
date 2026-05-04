"""L1 unit tests for ElevenLabs wrapper. Mocked — no real API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from comicast.budget import BudgetTracker
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
    el.synthesize(text="hello", voice_id="x", model_id="eleven_v3")
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
