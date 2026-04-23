"""Structured logging configuration via structlog. @zara"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO") -> structlog.stdlib.BoundLogger:
    """Configure structlog with JSON-ish ConsoleRenderer for HA logs. @zara"""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    _NOISY_LOGGERS = (
        "aiosqlite",
        "apscheduler",
        "apscheduler.scheduler",
        "apscheduler.executors",
        "apscheduler.executors.default",
        "httpx",
        "httpcore",
        "httpcore.http11",
        "httpcore.connection",
        "urllib3",
        "urllib3.connectionpool",
        "hpack",
        "uvicorn.access",
    )
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger. @zara"""
    return structlog.get_logger(name)
