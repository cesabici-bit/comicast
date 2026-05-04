"""Tunable thresholds for the vision pipeline.

Centralized so prompt declarations and code defaults stay in lockstep.
See ``KNOWN_ISSUES.md`` VIS-07 for the original drift incident.
"""

from __future__ import annotations

from typing import Final

HITL_CONFIDENCE_THRESHOLD: Final[float] = 0.7
"""Bubbles with confidence < this value are flagged for human review.

Referenced from BOTH ``vision.confidence.bubbles_needing_review`` (default arg)
AND ``vision.prompts.PER_PAGE_SYSTEM`` (interpolated at format time via the
``{hitl_threshold}`` placeholder). Alignment is locked by
``tests/unit/test_threshold_alignment.py``.
"""
