"""L1 unit tests for the Anthropic client wrapper. No real API calls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import anthropic
import httpx
import pytest

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetExceededError, BudgetTracker


def _mk_response(text: str = '{"ok":true}') -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(type="text", text=text)]
    # SimpleNamespace gives strict attribute access (typo'd field names raise
    # AttributeError loudly instead of returning a sentinel MagicMock).
    msg.usage = SimpleNamespace(
        input_tokens=1000,
        output_tokens=100,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    return msg


def _mk_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _mk_response_400() -> httpx.Response:
    return httpx.Response(400, request=_mk_request())


@patch("anthropic.Anthropic")
def test_call_returns_text(MockAnthropic: MagicMock) -> None:  # noqa: N803
    mock_client = MockAnthropic.return_value
    mock_client.messages.create.return_value = _mk_response('{"x":1}')

    budget = BudgetTracker(estimate_usd=10.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    text = client.call_text(system="sys", user_text="hi")
    assert text == '{"x":1}'
    assert budget.spent_usd > 0


@patch("anthropic.Anthropic")
def test_call_with_image_attaches_base64(MockAnthropic: MagicMock) -> None:  # noqa: N803
    mock_client = MockAnthropic.return_value
    mock_client.messages.create.return_value = _mk_response()
    budget = BudgetTracker(estimate_usd=10.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    client.call_with_image(system="sys", image_b64="abc", user_text="describe")
    call = mock_client.messages.create.call_args
    msgs = call.kwargs["messages"]
    image_block = msgs[0]["content"][0]
    assert image_block["type"] == "image"
    assert image_block["source"]["data"] == "abc"


@patch("anthropic.Anthropic")
def test_system_marked_as_cacheable(MockAnthropic: MagicMock) -> None:  # noqa: N803
    mock_client = MockAnthropic.return_value
    mock_client.messages.create.return_value = _mk_response()
    budget = BudgetTracker(estimate_usd=10.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    client.call_with_image(
        system="big system prompt", image_b64="abc", user_text="x", cache_system=True
    )
    call = mock_client.messages.create.call_args
    sys_param = call.kwargs["system"]
    assert isinstance(sys_param, list)
    assert sys_param[0]["cache_control"] == {"type": "ephemeral"}


@patch("anthropic.Anthropic")
def test_records_cached_tokens_to_budget(MockAnthropic: MagicMock) -> None:  # noqa: N803
    msg = MagicMock()
    msg.content = [MagicMock(type="text", text="ok")]
    msg.usage = SimpleNamespace(
        input_tokens=10000,
        output_tokens=100,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=8000,
    )
    MockAnthropic.return_value.messages.create.return_value = msg
    budget = BudgetTracker(estimate_usd=10.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    client.call_text(system="sys", user_text="hi")
    # Cost contribution audit: 10000/1M*3.00 + 8000/1M*0.30 + 0 + 100/1M*15.00
    #                       = 0.030 + 0.0024 + 0 + 0.0015 = 0.0339 USD
    assert abs(budget.spent_usd - 0.0339) < 1e-9


@patch("tenacity.nap.time.sleep")  # patch time.sleep as seen from tenacity.nap
@patch("anthropic.Anthropic")
def test_retries_on_connection_error_then_succeeds(
    MockAnthropic: MagicMock,  # noqa: N803
    mock_sleep: MagicMock,
) -> None:
    """Transient APIConnectionError is retried; second attempt succeeds."""
    mock_client = MockAnthropic.return_value
    mock_client.messages.create.side_effect = [
        anthropic.APIConnectionError(request=_mk_request()),
        _mk_response('{"recovered":true}'),
    ]
    budget = BudgetTracker(estimate_usd=10.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    text = client.call_text(system="sys", user_text="hi")
    assert text == '{"recovered":true}'
    assert mock_client.messages.create.call_count == 2
    # tenacity slept between attempts (we patched time.sleep to be instant)
    assert mock_sleep.called


@patch("anthropic.Anthropic")
def test_does_not_retry_bad_request(MockAnthropic: MagicMock) -> None:  # noqa: N803
    """Non-transient 4xx (BadRequestError) MUST NOT be retried — fail fast."""
    mock_client = MockAnthropic.return_value
    mock_client.messages.create.side_effect = anthropic.BadRequestError(
        message="bad", response=_mk_response_400(), body=None
    )
    budget = BudgetTracker(estimate_usd=10.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    with pytest.raises(anthropic.BadRequestError):
        client.call_text(system="sys", user_text="hi")
    # Exactly 1 call: no retries, no budget burn on a guaranteed-fail input
    assert mock_client.messages.create.call_count == 1


@patch("anthropic.Anthropic")
def test_budget_exceeded_raises_after_recording(MockAnthropic: MagicMock) -> None:  # noqa: N803
    """When a call pushes spend past hard limit, BudgetExceededError raises AFTER record."""
    mock_client = MockAnthropic.return_value
    msg = MagicMock()
    msg.content = [MagicMock(type="text", text="ok")]
    # 1B uncached input tokens × $3/1M = $3000 → far past 2× $1 estimate
    msg.usage = SimpleNamespace(
        input_tokens=1_000_000_000,
        output_tokens=0,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    mock_client.messages.create.return_value = msg
    budget = BudgetTracker(estimate_usd=1.0, hard_multiplier=2.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    with pytest.raises(BudgetExceededError):
        client.call_text(system="sys", user_text="hi")
    # Post-record-assert: the over-budget call IS billed before halting (debug aid)
    assert budget.spent_usd > 2.0  # > hard limit (2× estimate)
    assert len(budget._records) == 1  # the record was appended


@patch("anthropic.Anthropic")
def test_call_text_raises_on_non_text_response(MockAnthropic: MagicMock) -> None:  # noqa: N803
    """Empty text_parts (e.g. tool_use-only response) raises RuntimeError loudly.

    Catches: (a) Anthropic adding a new content block type that we'd silently
    drop (Risk 4), and (b) Pass 2b strict tool calls misusing call_text instead
    of a dedicated call_with_tool() method.
    """
    mock_client = MockAnthropic.return_value
    msg = MagicMock()
    msg.content = [MagicMock(type="tool_use", text=None)]  # no text block
    msg.usage = SimpleNamespace(
        input_tokens=1000,
        output_tokens=100,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    mock_client.messages.create.return_value = msg
    budget = BudgetTracker(estimate_usd=10.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    with pytest.raises(RuntimeError, match="expected a text response"):
        client.call_text(system="sys", user_text="hi")
