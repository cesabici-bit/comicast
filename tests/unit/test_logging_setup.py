"""Unit tests for logging configuration."""

from __future__ import annotations

import io
import json
import logging
import sys

import pytest

from comicast.logging_setup import get_logger, setup_logging


def test_setup_logging_emits_json(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    # Reconfigure AFTER monkeypatch so PrintLoggerFactory captures the patched stderr.
    setup_logging(level="INFO", json_output=True)
    log = get_logger("test_json_emit")
    log.info("hello", trace_id="abc123", page=5)

    line = buf.getvalue().strip().splitlines()[-1]
    record = json.loads(line)
    assert record["event"] == "hello"
    assert record["trace_id"] == "abc123"
    assert record["page"] == 5
    assert record["level"] == "info"
    assert "timestamp" in record


def test_get_logger_returns_bound_logger() -> None:
    setup_logging(level="DEBUG", json_output=False)
    log = get_logger("comicast.vision")
    assert log is not None
    bound = log.bind(volume="invincible_vol_2")
    assert bound is not None


def test_logger_level_respects_setup() -> None:
    # REGRESSION: setup_logging() must re-apply level on subsequent calls.
    # logging.basicConfig is a no-op when handlers exist unless force=True.
    setup_logging(level="INFO", json_output=False)
    setup_logging(level="WARNING", json_output=False)
    assert logging.getLogger().getEffectiveLevel() == logging.WARNING
