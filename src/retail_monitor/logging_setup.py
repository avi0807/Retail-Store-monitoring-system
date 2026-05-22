"""Logging setup."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO", logger_name: str | None = None) -> logging.Logger:
    """Configure logging for the retail_monitor package. Idempotent."""
    logger = logging.getLogger(logger_name or "retail_monitor")
    logger.setLevel(level.upper())

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(stream=sys.stdout)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
