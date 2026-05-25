from __future__ import annotations

import logging
from pathlib import Path


def setup_logger(log_file: str | Path) -> logging.Logger:
    logger = logging.getLogger("pko_rate_watcher")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
