"""Centralized structlog configuration.

Every entry point (CLI, test fixtures, services) calls setup_logging() once.
Trace_ids are bound per VLM decision (Pass 2a/2b/3) so audio regressions
(pre_mortem.md Risk 4) can be traced back to the originating page/panel.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog
from structlog.typing import FilteringBoundLogger


def setup_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog + stdlib logging globally.

    Args:
        level: Standard logging level (DEBUG/INFO/WARNING/ERROR).
        json_output: If True, emit JSON lines. If False, human-readable colored output.
    """
    lvl = getattr(logging, level.upper())
    # NOTE: PrintLoggerFactory handles structlog records (single write).
    # basicConfig stream is for third-party stdlib loggers (anthropic, httpx, etc.).
    # Both go to stderr by design — they are NOT duplicates.
    # force=True replaces existing handlers so subsequent setup_logging() calls
    # actually re-apply the level (basicConfig is a no-op when handlers exist).
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=lvl,
        force=True,
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.set_exc_info,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(lvl),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Return a structlog logger bound to the given name."""
    return cast(FilteringBoundLogger, structlog.get_logger(name))
