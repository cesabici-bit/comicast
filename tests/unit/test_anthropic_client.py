"""L1 unit tests for the Anthropic client wrapper. No real API calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker


def _mk_response(text: str = '{"ok":true}') -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(type="text", text=text)]
    msg.usage = MagicMock(
        input_tokens=1000,
        output_tokens=100,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    return msg


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
    msg.usage = MagicMock(
        input_tokens=10000,
        output_tokens=100,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=8000,
    )
    MockAnthropic.return_value.messages.create.return_value = msg
    budget = BudgetTracker(estimate_usd=10.0)
    client = AnthropicClient(model="claude-sonnet-4-6", budget=budget, api_key="sk-test")
    client.call_text(system="sys", user_text="hi")
    # cost should be lower than non-cached because most input is cached
    assert budget.spent_usd > 0
