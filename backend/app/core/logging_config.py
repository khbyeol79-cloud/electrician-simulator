from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import AppPaths


def configure_logging(paths: AppPaths, debug: bool = False) -> logging.Logger:
    paths.ensure_writable_directories()
    logger = logging.getLogger("electrician_simulator")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        file_handler = RotatingFileHandler(
            paths.log_file,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

