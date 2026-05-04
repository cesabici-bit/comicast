"""Pass 2b — Per-page attribution.

For each page: send to Claude vision with cast + common_errors as cached system,
parse the JSON response into PageScript objects, accumulate into ScriptFile.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.logging_setup import get_logger
from comicast.schemas import CastFile, PageScript, ScriptFile
from comicast.vision.prompts import PER_PAGE_SYSTEM, PER_PAGE_USER

log = get_logger("comicast.vision.attribute")

_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]+?)\s*```\s*$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    m = _FENCE_RE.search(text)
    return m.group(1) if m else text


def attribute_pages(
    pages: list[Path],
    *,
    cast: CastFile,
    common_errors: list[str],
    series_name: str,
    volume_id: str,
    client: AnthropicClient,
    budget: BudgetTracker,
) -> ScriptFile:
    """Run Pass 2b on each page in order. Fail-soft on a per-page basis."""
    cast_json_str = cast.model_dump_json(indent=2)
    common_errors_str = (
        "\n".join(f"- {e}" for e in common_errors) if common_errors else "(none yet)"
    )
    system_prompt = PER_PAGE_SYSTEM.format(
        cast_json=cast_json_str,
        common_errors=common_errors_str,
    )

    page_scripts: list[PageScript] = []
    parse_failures = 0
    for idx, page_path in enumerate(pages, start=1):
        b64 = client.encode_image(page_path.read_bytes())
        try:
            raw = client.call_with_image(
                system=system_prompt,
                image_b64=b64,
                user_text=PER_PAGE_USER.format(
                    page_num=idx,
                    volume_id=volume_id,
                    series_name=series_name,
                ),
                cache_system=True,
            )
            data = json.loads(_strip_fences(raw))
            page_script = PageScript.model_validate(data)
            page_scripts.append(page_script)
            log.info("vision.attribute.page_done", page=idx, n_panels=len(page_script.panels))
        except (json.JSONDecodeError, ValidationError) as e:
            parse_failures += 1
            log.warning("vision.attribute.page_fail", page=idx, error=str(e))
            continue

    # Mirror cast.py:76-79 cardinality invariant: an empty ScriptFile is
    # indistinguishable from a legitimate "volume contains no dialogue" outcome,
    # which would silently propagate to TTS as an empty audiobook (Risk 4).
    if pages and parse_failures == len(pages):
        raise RuntimeError(
            f"vision.attribute: all {len(pages)} pages failed JSON parse — cannot build ScriptFile"
        )

    return ScriptFile(series_name=series_name, volume_id=volume_id, pages=page_scripts)
