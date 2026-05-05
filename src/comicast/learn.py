"""Self-improving — summarize past corrections into prompt-injectable common errors."""

from __future__ import annotations

import json
import re
from pathlib import Path

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.logging_setup import get_logger
from comicast.schemas import SeriesProfile

log = get_logger("comicast.learn")

_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]+?)\s*```\s*$", re.MULTILINE)

SUMMARIZER_SYSTEM = """You are a quality engineer reviewing a log of human corrections to a vision-LLM's comic transcription. Your job is to extract the most common error patterns so we can prevent them on future volumes.

Output format (STRICT JSON):
{
  "common_errors_learned": [
    "Brief 1-line statement of an error pattern with how to avoid it",
    ...
  ]
}

Guidelines:
- 1-7 entries total. Quality over quantity.
- Each entry must be actionable in a system prompt: 'Avoid X' or 'When you see Y, do Z'.
- Cluster similar corrections (5 corrections about Mark/Atom Eve become 1 entry).
- Skip noisy corrections (typos, one-offs)."""


def update_common_errors_from_log(
    profile: SeriesProfile,
    corrections_log: Path,
    *,
    client: AnthropicClient,
    budget: BudgetTracker,
) -> SeriesProfile:
    """Read corrections.jsonl, summarize via Claude, update profile in-place."""
    if not corrections_log.exists() or corrections_log.stat().st_size == 0:
        log.info("learn.no_corrections", path=str(corrections_log))
        return profile

    try:
        raw_text = corrections_log.read_text(encoding="utf-8")
    except OSError as exc:
        log.error(
            "learn.read_failed",
            path=str(corrections_log),
            error_class=type(exc).__name__,
        )
        raise

    lines = [line for line in raw_text.splitlines() if line.strip()]
    if not lines:
        log.info("learn.no_corrections_after_strip", path=str(corrections_log))
        log.info("learn.done", n_errors=0)
        return profile

    log.info("learn.summarizing", n_corrections=len(lines))
    user_prompt = "Recent corrections (jsonl):\n" + "\n".join(
        lines[-200:]
    )  # last 200 to bound prompt
    raw = client.call_text(
        system=SUMMARIZER_SYSTEM,
        user_text=user_prompt,
        cache_system=False,
        max_tokens=2000,
    )
    m = _FENCE_RE.search(raw)
    payload = m.group(1) if m else raw
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        log.error(
            "learn.parse_failed",
            error_class=type(exc).__name__,
            msg=str(exc),
            payload_prefix=payload[:200],
        )
        raise
    profile.common_errors_learned = data.get("common_errors_learned", [])
    log.info("learn.done", n_errors=len(profile.common_errors_learned))
    return profile
