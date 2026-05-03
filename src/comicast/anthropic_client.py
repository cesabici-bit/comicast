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

# Transient errors worth retrying. Per anthropic SDK 0.97 hierarchy:
# - APIConnectionError covers APITimeoutError (subclass) — network/connection failures.
# - RateLimitError (429) — caller's quota; backoff lets it clear.
# - InternalServerError (5xx) — server-side; retry per Anthropic best practice.
# Non-transient errors (BadRequestError, AuthenticationError, NotFoundError,
# UnprocessableEntityError, PermissionDeniedError, ConflictError) are NOT in this
# tuple — retrying them burns 14s + 3x token budget on calls guaranteed to fail.
TRANSIENT_EXCEPTIONS = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class AnthropicClient:
    """Wrapper that integrates retry, caching, budget tracking.

    Use `call_text` for text-in/text-out and `call_with_image` for vision calls
    (Pass 2a/2b). Set `cache_system=True` when the system prompt is large enough
    to benefit from caching (≥1024 tokens; see F1-anthropic.md:116). This wrapper
    does NOT yet support strict tool-use responses — when Pass 2b lands strict
    tool calls, add a dedicated `call_with_tool()` method (the current methods
    raise on a tool_use-only response, see `_call` below).
    """

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
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
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
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            system=sys_param,
            messages=[{"role": "user", "content": user_content}],
        )

        usage = msg.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0)
        cache_write = getattr(usage, "cache_creation_input_tokens", 0)
        # Post-record-assert ordering: the offending call IS billed and logged
        # before halting — debug aid for runaway-cost forensics.
        self.budget.record(
            provider="anthropic",
            input_tokens=usage.input_tokens,
            cached_input_tokens=cache_read,
            cache_write_tokens=cache_write,
            output_tokens=usage.output_tokens,
        )
        self.budget.assert_under_hard_limit()

        # Concatenate text blocks. Fail loudly when there are none — this catches
        # both new content types added by Anthropic (Risk 4) and Pass 2b strict
        # tool-use responses misusing call_text/call_with_image (use a dedicated
        # call_with_tool() method when that path lands).
        text_parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        if not text_parts:
            block_types = [getattr(b, "type", None) for b in msg.content]
            raise RuntimeError(
                f"AnthropicClient expected a text response, got block types: {block_types}. "
                "If this is a strict tool-use call, use a dedicated call_with_tool() method."
            )
        return "".join(text_parts)
