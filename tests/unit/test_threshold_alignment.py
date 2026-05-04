"""VIS-07 lock: prompt body and code default share one source of truth.

If a future edit drifts the constant from the prompt placeholder (or removes
the placeholder and re-hardcodes the literal), these tests fail loudly.
"""

from __future__ import annotations

import inspect

from comicast.vision import confidence
from comicast.vision.prompts import PER_PAGE_SYSTEM
from comicast.vision.thresholds import HITL_CONFIDENCE_THRESHOLD


def test_per_page_system_uses_placeholder_not_literal() -> None:
    """The unformatted prompt must declare the threshold via {hitl_threshold},
    not by hardcoding the numeric literal."""
    assert "{hitl_threshold}" in PER_PAGE_SYSTEM


def test_per_page_system_renders_threshold_value_when_formatted() -> None:
    """After ``.format(hitl_threshold=HITL_CONFIDENCE_THRESHOLD)`` the body
    must contain the constant's value adjacent to the ``<`` operator, matching
    the calibration band declared by the prompt."""
    formatted = PER_PAGE_SYSTEM.format(
        cast_json="{}",
        common_errors="(none)",
        hitl_threshold=HITL_CONFIDENCE_THRESHOLD,
    )
    assert f"<{HITL_CONFIDENCE_THRESHOLD}" in formatted


def test_bubbles_needing_review_default_is_shared_constant() -> None:
    """``bubbles_needing_review`` must default to the shared constant — never
    a re-hardcoded literal that could drift independently."""
    sig = inspect.signature(confidence.bubbles_needing_review)
    default = sig.parameters["threshold"].default
    assert default == HITL_CONFIDENCE_THRESHOLD
