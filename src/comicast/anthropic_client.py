"""Thin wrapper around anthropic.Anthropic.

Responsibilities:
- Retry with exponential backoff on transient errors
- Prompt caching (system block marked ephemeral)
- BudgetTracker integration (cost recorded after every call)
- Structured logging with trace_ids
"""

from __future__ import annotations

import base64
import os
from typing import Any
from uuid import uuid4

import anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from comicast.budget import BudgetTracker
from comicast.logging_setup import get_logger

log = get_logger("comicast.anthropic")


class AnthropicClient:
    """Wrapper that integrates retry, caching, budget tracking."""

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        budget: BudgetTracker,
        api_key: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.budget = budget
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if key is None:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self._client = anthropic.Anthropic(api_key=key)

    @retry(
        retry=retry_if_exception_type((anthropic.APIError, anthropic.APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _create(self, **kwargs: Any) -> Any:  # noqa: ANN401
        return self._client.messages.create(**kwargs)

    @staticmethod
    def encode_image(image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode("ascii")

    def call_text(
        self,
        *,
        system: str,
        user_text: str,
        cache_system: bool = False,
        max_tokens: int | None = None,
    ) -> str:
        return self._call(
            system=system,
            user_content=[{"type": "text", "text": user_text}],
            cache_system=cache_system,
            max_tokens=max_tokens,
        )

    def call_with_image(
        self,
        *,
        system: str,
        image_b64: str,
        user_text: str,
        media_type: str = "image/png",
        cache_system: bool = True,
        max_tokens: int | None = None,
    ) -> str:
        return self._call(
            system=system,
            user_content=[
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                },
                {"type": "text", "text": user_text},
            ],
            cache_system=cache_system,
            max_tokens=max_tokens,
        )

    def _call(
        self,
        *,
        system: str,
        user_content: list[dict[str, Any]],
        cache_system: bool,
        max_tokens: int | None,
    ) -> str:
        trace_id = uuid4().hex[:8]
        sys_param: str | list[dict[str, Any]]
        if cache_system:
            sys_param = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        else:
            sys_param = system

        log.info("anthropic.call", trace_id=trace_id, cache=cache_system, model=self.model)
        msg = self._create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            system=sys_param,
            messages=[{"role": "user", "content": user_content}],
        )

        usage = msg.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.budget.record(
            provider="anthropic",
            input_tokens=usage.input_tokens,
            cached_input_tokens=cache_read,
            cache_write_tokens=cache_write,
            output_tokens=usage.output_tokens,
        )
        self.budget.assert_under_hard_limit()

        # Concatenate text blocks (Claude usually returns 1)
        text_parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        return "".join(text_parts)
