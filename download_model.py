#!/usr/bin/env python3
"""Скачивает офлайн-модель Vosk для русского языка."""

import os
import zipfile
import urllib.request
from jarvis.config import MODEL_DIR, VOSK_MODEL_URL, VOSK_MODEL_NAME


def download():
    os.makedirs(MODEL_DIR, exist_ok=True)
    zip_path = os.path.join(MODEL_DIR, "vosk-model-small-ru.zip")
    model_path = os.path.join(MODEL_DIR, VOSK_MODEL_NAME)

    if os.path.exists(model_path):
        print(f"Модель уже скачана: {model_path}")
        return

    print("Скачивание модели Vosk...")
    urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path)

    print("Распаковка...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(MODEL_DIR)

    os.remove(zip_path)
    print(f"Готово: {model_path}")


if __name__ == "__main__":
    download()
