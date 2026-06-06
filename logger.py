from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from config import CFG

_DEF_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(_DEF_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    log_path = CFG.base_dir / CFG.log_file
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    try:
        console_stream = open(
            sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1, closefd=False
        )
    except Exception:
        console_stream = sys.stdout

    console_handler = logging.StreamHandler(console_stream)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root.addHandler(console_handler)

    for noisy in (
        "comtypes",
        "urllib3",
        "speechbrain",
        "torch",
        "torchaudio",
        "filelock",
        "numba",
        "huggingface_hub",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root.info("Logging initialised. Log file: %s", log_path)