"""Centralised logging configuration.

Replaces the print-based reporting of the original scraper. Log records are
emitted to the console and (optionally) a UTF-8 encoded rotating log file.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from src.config import REPO_ROOT, get_settings

_LOG_NAME = "jmip"


def _file_handler(log_path) -> logging.Handler:
    handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
    )
    return handler


def _console_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
    )
    return handler


def configure_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return the root application logger."""
    settings = get_settings()
    level = logging.DEBUG if verbose else getattr(
        logging, settings.log_level.upper(), logging.INFO
    )

    root = logging.getLogger()
    root.setLevel(level)
    # Remove any pre-existing handlers so config is idempotent.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    root.addHandler(_console_handler())

    log_file = REPO_ROOT / "logs" / "etl.log"
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        root.addHandler(_file_handler(log_file))
    except OSError:  # pragma: no cover - filesystem write failure
        root.warning("Could not attach file handler at %s", log_file)

    logger = logging.getLogger(_LOG_NAME)
    # Silence noisy third-party loggers at DEBUG level.
    for noisy in ("urllib3", "asyncio", "httpcore", "h11"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger


def get_logger(name: str = _LOG_NAME) -> logging.Logger:
    """Return a child logger of the application logger."""
    return logging.getLogger(f"{_LOG_NAME}.{name}" if name else _LOG_NAME)