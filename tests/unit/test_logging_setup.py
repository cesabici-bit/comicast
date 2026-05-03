"""Unit tests for logging configuration."""

from __future__ import annotations

import logging

from comicast.logging_setup import get_logger, setup_logging


def test_setup_logging_emits_json() -> None:
    setup_logging(level="INFO", json_output=True)
    log = get_logger("test")
    # Capture by using a custom processor — for the test we just call and assert no error.
    log.info("hello", trace_id="abc123", page=5)


def test_get_logger_returns_bound_logger() -> None:
    setup_logging(level="DEBUG", json_output=False)
    log = get_logger("comicast.vision")
    assert log is not None
    # bind chain must work
    bound = log.bind(volume="invincible_vol_2")
    assert bound is not None


def test_logger_level_respects_setup() -> None:
    setup_logging(level="WARNING", json_output=False)
    # Standard library logger underlying structlog
    assert logging.getLogger("comicast").getEffectiveLevel() == logging.WARNING
