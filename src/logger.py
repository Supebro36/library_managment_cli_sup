"""Logging setup: internal events go to a log file, not the screen."""

import logging
from pathlib import Path

from src.config import LOG_FILE

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(
    log_file: Path = LOG_FILE, level: int = logging.INFO
) -> None:
    """Send all `src.*` log records to a file (safe to call twice)."""
    logger = logging.getLogger("src")
    if logger.handlers:
        return
    logger.setLevel(level)
    try:
        handler: logging.Handler = logging.FileHandler(
            log_file, encoding="utf-8"
        )
    except OSError:
        handler = logging.NullHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
