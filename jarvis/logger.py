"""Логирование для отладки."""

import logging
import sys
from .config import LOG_FILE


def setup_logging():
    """Настраивает логирование в файл и консоль."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Понижаем шум от сторонних библиотек
    for noisy in ["comtypes", "comtypes.client", "urllib3", "requests"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger("jarvis")


logger = setup_logging()
