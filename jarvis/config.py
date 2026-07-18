"""Конфигурация ассистента."""

import os

# Основные настройки
ASSISTANT_NAME = "Джарвис"
USER_NAME = "сэр"
LANGUAGE = "ru-RU"
WAKE_WORDS = ["джарвис", "jarvis", "дарвис"]

# Настройки речи
SPEECH_RATE = 180  # скорость речи (слов в минуту)
SPEECH_VOLUME = 0.9  # громкость от 0.0 до 1.0

# Настройки распознавания
ENERGY_THRESHOLD = 300  # чувствительность микрофона
PAUSE_THRESHOLD = 0.8   # секунды тишины перед окончанием фразы
TIMEOUT = 5             # секунды ожидания речи
PHRASE_TIME_LIMIT = 10  # максимальная длительность фразы
SAMPLE_RATE = 16000     # частота дискретизации для Vosk

# Пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "jarvis.log")
MODEL_DIR = os.path.join(BASE_DIR, "models")
VOSK_MODEL_NAME = "vosk-model-small-ru-0.22"
VOSK_MODEL_PATH = os.path.join(MODEL_DIR, VOSK_MODEL_NAME)
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"

# Автозагрузка
AUTO_START_BAT = os.path.join(BASE_DIR, "start.bat")
