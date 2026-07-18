"""Обработка голосовых команд."""

import os
import subprocess
import webbrowser
import datetime
import random
from .config import ASSISTANT_NAME, USER_NAME


class CommandProcessor:
    """Анализирует текст и выполняет соответствующие действия."""

    GREETINGS = [
        f"Приветствую, {USER_NAME}.",
        f"Здравствуйте, {USER_NAME}.",
        f"Всегда к вашим услугам, {USER_NAME}.",
    ]

    HOW_ARE_YOU = [
        "Системы функционируют в штатном режиме, спасибо.",
        "Готов к работе, {USER_NAME}.",
        "Полностью оперативен.",
    ]

    FAREWELLS = [
        "До свидания, сэр.",
        "Всего доброго.",
        "Выключаюсь.",
    ]

    JOKES = [
        "Почему программисты путают Хэллоуин и Рождество? Потому что 31 октября равно 25 декабря.",
        "У меня нет тела, но я отлично умею висеть в системе.",
        "Шутка про искусственный интеллект? Я над ней ещё думаю.",
    ]

    def __init__(self):
        self.active = True

    def process(self, text):
        """Обрабатывает текст команды и возвращает ответ."""
        if not text:
            return None

        text = text.lower()

        if any(word in text for word in ["привет", "здравствуй", "доброе утро", "добрый день"]):
            return random.choice(self.GREETINGS)

        if any(phrase in text for phrase in ["как дела", "как ты", "как себя чувствуешь"]):
            return random.choice(self.HOW_ARE_YOU)

        if any(phrase in text for phrase in ["сколько время", "который час", "текущее время"]):
            now = datetime.datetime.now()
            return f"Сейчас {now.strftime('%H:%M')}"

        if any(phrase in text for phrase in ["какое сегодня число", "какая сегодня дата", "сегодняшняя дата"]):
            now = datetime.datetime.now()
            return f"Сегодня {now.strftime('%d %B %Y года')}"

        if "открой youtube" in text or "youtube" in text:
            webbrowser.open("https://www.youtube.com")
            return "Открываю YouTube."

        if "открой google" in text or "гугл" in text:
            webbrowser.open("https://www.google.com")
            return "Открываю Google."

        if "открой браузер" in text or "браузер" in text:
            webbrowser.open("https://www.google.com")
            return "Открываю браузер."

        if "открой калькулятор" in text:
            subprocess.Popen("calc.exe")
            return "Открываю калькулятор."

        if "открой блокнот" in text or "открой notepad" in text:
            subprocess.Popen("notepad.exe")
            return "Открываю блокнот."

        if "открой проводник" in text or "папку" in text:
            subprocess.Popen("explorer.exe")
            return "Открываю проводник."

        if "найди" in text or "загугли" in text or "поищи" in text:
            query = text.replace("найди", "").replace("загугли", "").replace("поищи", "").strip()
            if query:
                webbrowser.open(f"https://www.google.com/search?q={query}")
                return f"Ищу в Google: {query}"
            return "Что именно найти?"

        if any(phrase in text for phrase in ["шутка", "пошути", "анекдот", "расскажи шутку", "смешнявку"]):
            return random.choice(self.JOKES)

        if any(word in text for word in ["стоп", "выключись", "пока", "до свидания", "завершить"]):
            self.active = False
            return random.choice(self.FAREWELLS)

        if any(phrase in text for phrase in ["кто ты", "как тебя зовут", "твое имя"]):
            return f"Я {ASSISTANT_NAME}, ваш персональный голосовой ассистент."

        return "Я вас не понял. Попробуйте переформулировать команду."
