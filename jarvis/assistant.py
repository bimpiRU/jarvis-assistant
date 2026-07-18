"""Главный цикл ассистента."""

import threading
import time
import numpy as np
from .speech import Speech
from .commands import CommandProcessor
from .wake_word import WakeWordDetector
from .dangerous_action import DangerousAction
from .jarvis_phrases import JarvisPersonality
from .config import ASSISTANT_NAME, USER_NAME
from .logger import logger


class Jarvis:
    """Основной класс голосового ассистента."""

    def __init__(self, on_listen=None, on_response=None, offline_only=False, use_wake_word=True, mic_device=None):
        logger.info(f"Инициализация Jarvis: offline={offline_only}, wake={use_wake_word}, device={mic_device}")
        self.speech = Speech(device=mic_device)
        self.commands = CommandProcessor()
        self.commands._mic_test_callback = self.test_microphone
        self.offline_only = offline_only
        self.use_wake_word = use_wake_word
        self.on_listen = on_listen
        self.on_response = on_response
        self.on_dangerous_action = None
        self.on_confirmation_needed = None
        self.on_audio_level = None
        self.wake_detector = None
        self._level_monitor_running = False

        if use_wake_word:
            self.wake_detector = WakeWordDetector(
                self.speech,
                on_wake=self._on_wake,
            )

    def greet(self):
        mode = "офлайн-режим" if self.offline_only else "онлайн + офлайн"
        activation = "Скажите 'Джарвис' для активации." if self.use_wake_word else ""
        greeting = (
            f"Добро пожаловать, {USER_NAME}. {ASSISTANT_NAME} к вашим услугам. "
            f"Режим: {mode}. {activation}"
        )
        self._respond(greeting)
        return greeting

    def start_wake_word(self):
        """Запускает фоновое прослушивание wake word."""
        if self.wake_detector:
            self.wake_detector.start()
        self._start_level_monitor()

    def _start_level_monitor(self):
        """Запускает мониторинг уровня звука (один раз)."""
        if self._level_monitor_running:
            return
        self._level_monitor_running = True

        def monitor():
            while self.is_active():
                level = self.speech.get_mic_level()
                if self.on_audio_level:
                    self.on_audio_level(level)
                time.sleep(0.1)
            self._level_monitor_running = False

        threading.Thread(target=monitor, daemon=True).start()

    def stop_wake_word(self):
        """Останавливает прослушивание wake word."""
        if self.wake_detector:
            self.wake_detector.stop()

    def _on_wake(self):
        """Callback при срабатывании wake word."""
        logger.info("[Wake] Срабатывание wake word")
        activation = JarvisPersonality.get("ACTIVATION")
        self._respond(activation)
        # Небольшая пауза, чтобы пользователь успел сделать вдох/паузу
        # после слова "Джарвис" и перед командой.
        time.sleep(0.4)
        self.listen_and_respond()

    def listen_and_respond(self, stop_event=None, retry=0):
        """Слушает команду и возвращает ответ. При нераспознавании делает одну повторную попытку."""
        logger.info("[Listen] Начало прослушивания команды")
        if self.on_listen:
            self.on_listen("Слушаю...")

        text = self.speech.listen(use_online_fallback=not self.offline_only, stop_event=stop_event)

        if not text:
            logger.info("[Listen] Текст не распознан")
            if retry < 1:
                logger.info("[Listen] Повторная попытка распознавания")
                self._respond("Я вас не расслышал, сэр. Повторите, пожалуйста.")
                return self.listen_and_respond(stop_event=stop_event, retry=retry + 1)
            response = "Не удалось распознать команду, сэр."
            self._respond(response)
            return text, response

        logger.info(f"[Listen] Распознано: '{text}'")
        result = self.commands.process(text)

        if isinstance(result, DangerousAction):
            self._handle_dangerous_action(result)
            return text, result

        self._respond(result)
        return text, result

    def _handle_dangerous_action(self, action):
        """Обрабатывает опасное действие, требующее подтверждения."""
        ask = JarvisPersonality.get("CONFIRMATION_ASK")
        message = f"{ask} {action.title}. {action.description}"
        self._respond(message)

        if self.on_dangerous_action:
            self.on_dangerous_action(action)

    def confirm_pending(self):
        """Подтверждает ожидающее действие."""
        result = self.commands.confirm_pending()
        self._respond(result)
        return result

    def cancel_pending(self):
        """Отменяет ожидающее действие."""
        result = self.commands.cancel_pending()
        self._respond(result)
        return result

    def _respond(self, text):
        if text:
            self.speech.speak(text)
            if self.on_response:
                self.on_response(text)

    def is_active(self):
        return self.commands.active

    def stop(self):
        self.commands.active = False
        self.stop_wake_word()

    def test_microphone(self, duration=5):
        """Записывает и сразу воспроизводит звук для проверки микрофона."""
        logger.info("[Test] Начало теста микрофона")
        self.stop_wake_word()
        audio = self.speech.microphone.record_raw(duration=duration)
        if audio is None:
            return "Не удалось записать звук. Проверьте микрофон."
        rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
        result = f"Записано. Уровень: {rms:.1f}. Воспроизвожу..."
        self.speech.speak(result)
        success = self.speech.microphone.play_audio(audio)
        self.start_wake_word()
        if success:
            return result + " Если вы услышали свою речь, микрофон работает."
        return result + " Ошибка воспроизведения."
