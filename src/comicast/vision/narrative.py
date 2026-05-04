"""Pass 2c — Narrative consistency check.

Single text-only Anthropic call over the full script.json. Returns FlagsFile.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.logging_setup import get_logger
from comicast.schemas import CastFile, FlagsFile, ScriptFile
from comicast.vision._parse import strip_fences
from comicast.vision.prompts import NARRATIVE_CHECK_SYSTEM, NARRATIVE_CHECK_USER

log = get_logger("comicast.vision.narrative")


def check_narrative(
    script: ScriptFile,
    *,
    cast: CastFile,
    client: AnthropicClient,
    budget: BudgetTracker,
) -> FlagsFile:
    cast_json = cast.model_dump_json(indent=2)
    script_json = script.model_dump_json(indent=2)

    log.info(
        "vision.narrative.start",
        series=script.series_name,
        volume_id=script.volume_id,
        n_pages=len(script.pages),
        n_cast=len(cast.cast),
    )

    raw = client.call_text(
        system=NARRATIVE_CHECK_SYSTEM,
        user_text=NARRATIVE_CHECK_USER.format(cast_json=cast_json, script_json=script_json),
        cache_system=False,  # this prompt is one-shot per volume, no benefit from caching
        max_tokens=8000,
    )
    payload = strip_fences(raw)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        log.error("vision.narrative.parse_fail", error=str(e), payload_head=payload[:200])
        raise RuntimeError(f"vision.narrative: model returned unparseable JSON: {e}") from e

    # Coerce null-valued flags to empty list. Anthropic occasionally returns
    # {"flags": null} when no issues are found; FlagsFile.flags requires a list.
    # `data.get("flags", [])` would NOT defend against this — it returns None
    # when the key exists with a null value (the default only applies on
    # missing key).
    flags_raw = data.get("flags") or []
    try:
        flags_file = FlagsFile(
            series_name=script.series_name,
            volume_id=script.volume_id,
            flags=flags_raw,
        )
    except ValidationError as e:
        log.error(
            "vision.narrative.validation_fail",
            error=str(e),
            n_raw_flags=len(flags_raw) if isinstance(flags_raw, list) else -1,
        )
        raise RuntimeError(
            f"vision.narrative: model output did not satisfy FlagsFile schema: {e}"
        ) from e

    log.info("vision.narrative.done", n_flags=len(flags_file.flags))
    return flags_file
