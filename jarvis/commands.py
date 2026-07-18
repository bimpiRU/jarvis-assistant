"""Обработка голосовых команд."""

import os
import webbrowser
import datetime
import random
import re
from .config import ASSISTANT_NAME, USER_NAME
from . import system_control as sc
from . import autostart


class CommandProcessor:
    """Анализирует текст и выполняет соответствующие действия."""

    GREETINGS = [
        f"Приветствую, {USER_NAME}.",
        f"Здравствуйте, {USER_NAME}.",
        f"Всегда к вашим услугам, {USER_NAME}.",
    ]

    HOW_ARE_YOU = [
        "Системы функционируют в штатном режиме, спасибо.",
        f"Готов к работе, {USER_NAME}.",
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

        text = text.lower().strip()

        # --- Приветствия и базовое ---
        if any(word in text for word in ["привет", "здравствуй", "доброе утро", "добрый день"]):
            return random.choice(self.GREETINGS)

        if any(phrase in text for phrase in ["как дела", "как ты", "как себя чувствуешь"]):
            return random.choice(self.HOW_ARE_YOU)

        if any(phrase in text for phrase in ["кто ты", "как тебя зовут", "твое имя"]):
            return f"Я {ASSISTANT_NAME}, ваш персональный голосовой ассистент."

        if any(phrase in text for phrase in ["сколько время", "который час", "текущее время"]):
            now = datetime.datetime.now()
            return f"Сейчас {now.strftime('%H:%M')}"

        if any(phrase in text for phrase in ["какое сегодня число", "какая сегодня дата", "сегодняшняя дата"]):
            now = datetime.datetime.now()
            return f"Сегодня {now.strftime('%d %B %Y года')}"

        if any(phrase in text for phrase in ["расскажи шутку", "пошути", "анекдот", "шутка"]):
            return random.choice(self.JOKES)

        # --- Открытие сайтов ---
        if "открой youtube" in text or "youtube" in text:
            webbrowser.open("https://www.youtube.com")
            return "Открываю YouTube."

        if "открой google" in text or "гугл" in text:
            webbrowser.open("https://www.google.com")
            return "Открываю Google."

        if "открой браузер" in text:
            webbrowser.open("https://www.google.com")
            return "Открываю браузер."

        if any(phrase in text for phrase in ["найди", "загугли", "поищи"]):
            query = text
            for phrase in ["найди", "загугли", "поищи"]:
                query = query.replace(phrase, "")
            query = query.strip()
            if query:
                webbrowser.open(f"https://www.google.com/search?q={query}")
                return f"Ищу в Google: {query}"
            return "Что именно найти?"

        # --- Открытие программ ---
        if "открой калькулятор" in text:
            os.system("start calc.exe")
            return "Открываю калькулятор."

        if "открой блокнот" in text or "открой notepad" in text:
            os.system("start notepad.exe")
            return "Открываю блокнот."

        if "открой проводник" in text or "открой папку" in text:
            os.system("start explorer.exe")
            return "Открываю проводник."

        if "открой рабочий стол" in text:
            return sc.open_path(os.path.join(os.path.expanduser("~"), "Desktop"))

        if "открой загрузки" in text:
            return sc.open_path(os.path.join(os.path.expanduser("~"), "Downloads"))

        # --- Системное управление ---
        if any(phrase in text for phrase in ["заблокируй компьютер", "заблокируй пк", "блокировка"]):
            return sc.lock_pc()

        if any(phrase in text for phrase in ["выключи компьютер", "выключи пк", "завершение работы"]):
            return sc.shutdown_pc()

        if any(phrase in text for phrase in ["перезагрузи компьютер", "перезагрузи пк", "перезагрузка"]):
            return sc.restart_pc()

        if any(phrase in text for phrase in ["спящий режим", "усни", "сон"]):
            return sc.sleep_pc()

        if any(phrase in text for phrase in ["очисти корзину", "пусти корзину"]):
            return sc.empty_recycle_bin()

        if "скриншот" in text or "сделай снимок экрана" in text or "фото экрана" in text:
            return sc.take_screenshot()

        if any(phrase in text for phrase in ["система", "загрузка системы", "процессор", "оперативка"]):
            return sc.get_system_info()

        if "процессы" in text or "что тормозит" in text:
            return sc.list_processes()

        if text.startswith("заверши процесс") or text.startswith("закрой процесс"):
            name = text.replace("заверши процесс", "").replace("закрой процесс", "").strip()
            if name:
                return sc.kill_process(name)
            return "Какой процесс завершить?"

        # --- Громкость ---
        if "выключи звук" in text or "без звука" in text or "mute" in text:
            return sc.mute_volume()

        match = re.search(r"громкость (\d+)", text)
        if match:
            return sc.set_volume(int(match.group(1)))

        if any(phrase in text for phrase in ["громче", "прибавь громкость"]):
            return sc.change_volume(10)

        if any(phrase in text for phrase in ["тише", "убавь громкость"]):
            return sc.change_volume(-10)

        # --- Яркость ---
        match = re.search(r"яркость (\d+)", text)
        if match:
            return sc.set_brightness(int(match.group(1)))

        if any(phrase in text for phrase in ["ярче", "прибавь яркость"]):
            return sc.change_brightness(10)

        if any(phrase in text for phrase in ["тускнее", "убавь яркость"]):
            return sc.change_brightness(-10)

        # --- Мышь и клавиатура ---
        if "кликни" in text or "нажми мышью" in text:
            return sc.click_mouse()

        if text.startswith("напечатай"):
            txt = text.replace("напечатай", "").strip()
            return sc.type_text(txt)

        if text.startswith("нажми клавишу") or text.startswith("нажми"):
            key = text.replace("нажми клавишу", "").replace("нажми", "").strip()
            if key:
                return sc.press_key(key)
            return "Какую клавишу нажать?"

        # --- Автозагрузка ---
        if any(phrase in text for phrase in ["включи автозагрузку", "запускайся с компьютером", "добавь в автозагрузку"]):
            return autostart.enable()

        if any(phrase in text for phrase in ["выключи автозагрузку", "убери из автозагрузки", "не запускайся с компьютером"]):
            return autostart.disable()

        if "автозагрузка" in text or "автозапуск" in text:
            return "Автозагрузка включена." if autostart.is_enabled() else "Автозагрузка отключена."

        # --- Завершение ---
        if any(word in text for word in ["стоп", "выключись", "пока", "до свидания", "завершить"]):
            self.active = False
            return random.choice(self.FAREWELLS)

        return "Я вас не понял. Попробуйте переформулировать команду."
