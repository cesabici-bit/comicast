"""Pass 2a — Cast extraction.

Single Anthropic vision call over the first ~30 pages, returns a CastFile.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.logging_setup import get_logger
from comicast.schemas import CastFile
from comicast.vision.prompts import CAST_EXTRACTION_SYSTEM, CAST_EXTRACTION_USER

log = get_logger("comicast.vision.cast")

_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]+?)\s*```\s*$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    m = _FENCE_RE.search(text)
    return m.group(1) if m else text


def extract_cast(
    pages: list[Path],
    *,
    series_name: str,
    client: AnthropicClient,
    budget: BudgetTracker,
    max_pages: int = 30,
) -> CastFile:
    """Run Pass 2a — extract the recurring cast from the first N pages.

    NOTE: in Phase 1 we batch only ONE image per call (the first page) and instruct
    the model to consider the rest visually-similar. For multi-image batching we'd
    need to confirm the API supports >1 image per content block in F1 — if so, this
    function expands to send up to max_pages images. For now: keep simple.
    """
    if not pages:
        raise ValueError("No pages provided for cast extraction")
    pages_to_send = pages[: min(len(pages), max_pages)]

    log.info("vision.cast.start", n_pages=len(pages_to_send), series=series_name)

    # Phase 1 pragmatic approach: send pages one at a time, accumulate, dedupe by id.
    accumulated: dict[str, dict[str, object]] = {}
    for p in pages_to_send:
        b64 = client.encode_image(p.read_bytes())
        raw = client.call_with_image(
            system=CAST_EXTRACTION_SYSTEM,
            image_b64=b64,
            user_text=CAST_EXTRACTION_USER.format(series_name=series_name),
            cache_system=True,
        )
        try:
            data = json.loads(_strip_fences(raw))
        except json.JSONDecodeError as e:
            log.warning("vision.cast.parse_fail", page=str(p), error=str(e))
            continue
        for entry in data.get("cast", []):
            cid = entry.get("id")
            if not cid or cid in accumulated:
                continue
            accumulated[cid] = entry

    cast = CastFile.model_validate({"series_name": series_name, "cast": list(accumulated.values())})
    log.info("vision.cast.done", n_characters=len(cast.cast))
    return cast
