"""Shared parse helpers for the vision pipeline.

Promoted from triple-duplication across cast.py / attribute.py / narrative.py
once the 3rd handler landed (VIS-10 trigger condition met in F3-T27).
"""

from __future__ import annotations

import re

# Match a triple-backtick fenced block, optionally tagged "json", anywhere in
# a multi-line response. Group 1 = the fenced payload (whitespace-stripped).
_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]+?)\s*```\s*$", re.MULTILINE)


def strip_fences(text: str) -> str:
    """Strip a single ```/```json fenced block from ``text``.

    If no fenced block is present, returns ``text`` unchanged. If multiple
    fenced blocks exist, returns the first match (non-greedy).
    """
    m = _FENCE_RE.search(text)
    return m.group(1) if m else text
