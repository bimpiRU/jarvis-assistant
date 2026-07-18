"""Главный цикл ассистента."""

from .speech import Speech
from .commands import CommandProcessor
from .config import ASSISTANT_NAME, USER_NAME


class Jarvis:
    """Основной класс голосового ассистента."""

    def __init__(self, on_listen=None, on_response=None):
        self.speech = Speech()
        self.commands = CommandProcessor()
        self.on_listen = on_listen
        self.on_response = on_response

    def greet(self):
        greeting = f"Добро пожаловать, {USER_NAME}. {ASSISTANT_NAME} к вашим услугам."
        self._respond(greeting)
        return greeting

    def listen_and_respond(self):
        """Слушает команду и возвращает ответ."""
        if self.on_listen:
            self.on_listen("Слушаю...")

        text = self.speech.listen()

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
