"""Pass 2c — Narrative consistency check.

Single text-only Anthropic call over the full script.json. Returns FlagsFile.
"""

from __future__ import annotations

import json
import re

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.logging_setup import get_logger
from comicast.schemas import CastFile, FlagsFile, ScriptFile
from comicast.vision.prompts import NARRATIVE_CHECK_SYSTEM, NARRATIVE_CHECK_USER

log = get_logger("comicast.vision.narrative")

_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]+?)\s*```\s*$", re.MULTILINE)


def check_narrative(
    script: ScriptFile,
    *,
    cast: CastFile,
    client: AnthropicClient,
    budget: BudgetTracker,
) -> FlagsFile:
    cast_json = cast.model_dump_json(indent=2)
    script_json = script.model_dump_json(indent=2)

    raw = client.call_text(
        system=NARRATIVE_CHECK_SYSTEM,
        user_text=NARRATIVE_CHECK_USER.format(cast_json=cast_json, script_json=script_json),
        cache_system=False,  # this prompt is one-shot per volume, no benefit from caching
        max_tokens=8000,
    )
    m = _FENCE_RE.search(raw)
    payload = m.group(1) if m else raw
    data = json.loads(payload)

    flags_file = FlagsFile(
        series_name=script.series_name,
        volume_id=script.volume_id,
        flags=data.get("flags", []),
    )
    log.info("vision.narrative.done", n_flags=len(flags_file.flags))
    return flags_file
