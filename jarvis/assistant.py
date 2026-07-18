"""Главный цикл ассистента."""

from .speech import Speech
from .commands import CommandProcessor
from .wake_word import WakeWordDetector
from .config import ASSISTANT_NAME, USER_NAME


class Jarvis:
    """Основной класс голосового ассистента."""

    def __init__(self, on_listen=None, on_response=None, offline_only=False, use_wake_word=True):
        self.speech = Speech()
        self.commands = CommandProcessor()
        self.offline_only = offline_only
        self.use_wake_word = use_wake_word
        self.on_listen = on_listen
        self.on_response = on_response
        self.wake_detector = None

        if use_wake_word:
            self.wake_detector = WakeWordDetector(
                self.speech,
                on_wake=self._on_wake,
            )

    def greet(self):
        mode = "офлайн-режим" if self.offline_only else "онлайн + офлайн"
        activation = "Скажите 'Джарвис' для активации." if self.use_wake_word else ""
        greeting = f"Добро пожаловать, {USER_NAME}. {ASSISTANT_NAME} к вашим услугам. Режим: {mode}. {activation}"
        self._respond(greeting)
        return greeting

    def start_wake_word(self):
        """Запускает прослушивание wake word."""
        if self.wake_detector:
            self.wake_detector.start()

    def stop_wake_word(self):
        """Останавливает прослушивание wake word."""
        if self.wake_detector:
            self.wake_detector.stop()

    def _on_wake(self):
        """Callback при срабатывании wake word."""
        self._respond("Слушаю вас, сэр.")
        self.listen_and_respond()

    def listen_and_respond(self):
        """Слушает команду и возвращает ответ."""
        if self.on_listen:
            self.on_listen("Слушаю...")

        text = self.speech.listen(use_online_fallback=not self.offline_only)

        if not text:
            response = "Я вас не расслышал. Повторите, пожалуйста."
            self._respond(response)
            return text, response

        response = self.commands.process(text)
        self._respond(response)
        return text, response

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
