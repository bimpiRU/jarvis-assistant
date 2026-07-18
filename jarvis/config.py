"""Конфигурация ассистента."""

import os

# Основные настройки
ASSISTANT_NAME = "Джарвис"
USER_NAME = "сэр"
LANGUAGE = "ru-RU"

# Настройки речи
SPEECH_RATE = 180  # скорость речи (слов в минуту)
SPEECH_VOLUME = 0.9  # громкость от 0.0 до 1.0

# Настройки распознавания
ENERGY_THRESHOLD = 300  # чувствительность микрофона
PAUSE_THRESHOLD = 0.8   # секунды тишины перед окончанием фразы
TIMEOUT = 5             # секунды ожидания речи
PHRASE_TIME_LIMIT = 10  # максимальная длительность фразы

# Пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "jarvis.log")
