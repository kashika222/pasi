"""Stdlib logging setup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pasi.config.settings import get_settings

_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once for the process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    log_level_name = (level or settings.log_level).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logs_dir = settings.resolve(settings.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "pasi.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (call configure_logging at process start)."""
    return logging.getLogger(name)
