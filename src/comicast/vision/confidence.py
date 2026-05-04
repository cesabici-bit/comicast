"""Confidence helpers for HITL escalation.

Default threshold and the calibration band declared in
``vision.prompts.PER_PAGE_SYSTEM`` share a single source of truth at
``vision.thresholds.HITL_CONFIDENCE_THRESHOLD`` (closes VIS-07).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from comicast.schemas import Bubble, PageScript, ScriptFile
from comicast.vision.thresholds import HITL_CONFIDENCE_THRESHOLD


@dataclass
class FlaggedBubble:
    page: int
    panel_order: int
    bubble: Bubble


def bubbles_needing_review(
    script: ScriptFile, *, threshold: float = HITL_CONFIDENCE_THRESHOLD
) -> Iterator[FlaggedBubble]:
    """Yield every bubble with confidence < threshold."""
    for ps in script.pages:
        for panel in ps.panels:
            for bubble in panel.bubbles:
                if bubble.confidence < threshold:
                    yield FlaggedBubble(page=ps.page, panel_order=panel.order, bubble=bubble)


def page_average_confidence(page: PageScript) -> float:
    confidences = [b.confidence for panel in page.panels for b in panel.bubbles]
    if not confidences:
        return 0.0
    return sum(confidences) / len(confidences)
