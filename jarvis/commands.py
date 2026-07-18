"""Обработка голосовых команд."""

import os
import webbrowser
import datetime
import random
import re
from .config import ASSISTANT_NAME, USER_NAME
from . import system_control as sc
from . import autostart
from . import kimi_integration
from . import extras
from . import kaw_integration
from . import self_learning as sl
from .dangerous_action import DangerousAction
from .jarvis_phrases import JarvisPersonality


class CommandProcessor:
    """Анализирует текст и выполняет соответствующие действия."""

    def __init__(self):
        self.active = True
        self.pending_action = None

    def _dangerous(self, title, description, callback):
        """Создаёт опасное действие, требующее подтверждения."""
        self.pending_action = DangerousAction(title, description, callback)
        return self.pending_action

    def _kimi_command(self, text):
        """Извлекает запрос для Kimi из команды."""
        prefixes = [
            "спроси кими", "спроси у кими", "кими", "запусти кими",
            "открой кими", "попроси кими", "напиши код", "создай код",
            "помоги с кодом", "сделай код",
        ]
        query = text
        for prefix in prefixes:
            if query.startswith(prefix):
                query = query[len(prefix):].strip()
                break
        # Если запрос начинается с "для" или "на", оставляем как есть
        return query

    def process(self, text):
        """Обрабатывает текст команды и возвращает ответ или DangerousAction."""
        if not text:
            return None

        text = text.lower().strip()

        # --- Уведомления (до приветствий, чтобы не перехватывалось) ---
        if text.startswith("уведомление") or text.startswith("покажи уведомление"):
            msg = text.replace("уведомление", "").replace("покажи", "").strip()
            return extras.show_notification("Jarvis", msg or "Уведомление от Джарвиса")

        # --- Kimi Approve Watch (до базовых команд, чтобы точно перехватить) ---
        if kaw_integration.is_installed():
            if any(phrase in text for phrase in ["запусти watcher", "запусти кав", "запусти наблюдатель", "включи watcher"]):
                return kaw_integration.start_kaw()

            if any(phrase in text for phrase in ["останови watcher", "останови кав", "выключи watcher"]):
                return kaw_integration.stop_kaw()

            if any(phrase in text for phrase in ["статус watcher", "статус кав", "как watcher"]):
                return kaw_integration.status_kaw()

            if any(phrase in text for phrase in ["включи стабилизатор", "вруби стабилизатор"]):
                return kaw_integration.enable_stabilizer()

            if any(phrase in text for phrase in ["выключи стабилизатор", "отключи стабилизатор"]):
                return kaw_integration.disable_stabilizer()

            if any(phrase in text for phrase in ["включи автозагрузку кав", "автозагрузка кав", "запускай кав с компьютером"]):
                return kaw_integration.enable_autostart()

            if any(phrase in text for phrase in ["выключи автозагрузку кав", "убери кав из автозагрузки"]):
                return kaw_integration.disable_autostart()

            if "автозагрузка кав" in text:
                return "Автозагрузка KAW включена." if kaw_integration.is_autostart_enabled() else "Автозагрузка KAW отключена."

        # --- Приветствия и базовое ---
        if any(word in text for word in ["привет", "здравствуй", "доброе утро", "добрый день"]):
            return JarvisPersonality.get("GREETINGS")

        if any(phrase in text for phrase in ["как дела", "как ты", "как себя чувствуешь", "статус"]):
            return JarvisPersonality.get("STATUS_REPORTS")

        if any(phrase in text for phrase in ["кто ты", "как тебя зовут", "твое имя", "представься"]):
            return f"Я {ASSISTANT_NAME}, ваш персональный голосовой ассистент. Готов выполнить любую задачу, сэр."

        if any(phrase in text for phrase in ["сколько время", "который час", "текущее время"]):
            now = datetime.datetime.now()
            return f"Сейчас {now.strftime('%H:%M')}, сэр."

        if any(phrase in text for phrase in ["какое сегодня число", "какая сегодня дата", "сегодняшняя дата"]):
            now = datetime.datetime.now()
            return f"Сегодня {now.strftime('%d %B %Y года')}, сэр."

        if any(phrase in text for phrase in ["расскажи шутку", "пошути", "анекдот", "шутка", "развесели"]):
            return JarvisPersonality.get("JOKES")

        if any(phrase in text for phrase in ["статистика", "что ты выучил", "что ты знаешь", "сколько команд"]):
            return sl.SelfLearning().get_summary()

        # --- Открытие сайтов ---
        if "открой youtube" in text or "youtube" in text:
            webbrowser.open("https://www.youtube.com")
            return JarvisPersonality.get("SUCCESS") + " Открываю YouTube."

        if "открой google" in text or "гугл" in text:
            webbrowser.open("https://www.google.com")
            return JarvisPersonality.get("SUCCESS") + " Открываю Google."

        if "открой браузер" in text:
            webbrowser.open("https://www.google.com")
            return JarvisPersonality.get("SUCCESS") + " Открываю браузер."

        # --- Яндекс Музыка ---
        if "в яндекс музыке" in text or "включи в яндекс музыке" in text:
            query = text
            for phrase in ["в яндекс музыке", "включи в яндекс музыке", "найди в яндекс музыке", "включи"]:
                query = query.replace(phrase, "")
            query = query.strip()
            if query:
                return extras.play_yandex_song(query)

        if any(phrase in text for phrase in ["яндекс музыку", "яндекс музыка"]):
            return extras.open_yandex_music()

        if text.startswith("включи песню") or text.startswith("вруби песню") or text.startswith("найди песню"):
            query = text
            for phrase in ["включи песню", "вруби песню", "найди песню"]:
                query = query.replace(phrase, "")
            query = query.strip()
            if query:
                return extras.play_yandex_song(query)
            return "Какую песню включить, сэр?"

        if any(phrase in text for phrase in ["включи музыку", "вруби музыку", "музыку", "вруби музон"]):
            return extras.play_music()

        if any(phrase in text for phrase in ["найди", "загугли", "поищи"]):
            query = text
            for phrase in ["найди", "загугли", "поищи"]:
                query = query.replace(phrase, "")
            query = query.strip()
            if query:
                webbrowser.open(f"https://www.google.com/search?q={query}")
                return f"{JarvisPersonality.get('SUCCESS')} Ищу в Google: {query}"
            return "Что именно найти, сэр?"

        # --- Открытие программ ---
        if "открой калькулятор" in text:
            os.system("start calc.exe")
            return JarvisPersonality.get("SUCCESS") + " Открываю калькулятор."

        if "открой блокнот" in text or "открой notepad" in text:
            os.system("start notepad.exe")
            return JarvisPersonality.get("SUCCESS") + " Открываю блокнот."

        if "открой проводник" in text or "открой папку" in text:
            os.system("start explorer.exe")
            return JarvisPersonality.get("SUCCESS") + " Открываю проводник."

        if "открой рабочий стол" in text:
            return sc.open_path(os.path.join(os.path.expanduser("~"), "Desktop"))

        if "открой загрузки" in text:
            return sc.open_path(os.path.join(os.path.expanduser("~"), "Downloads"))

        # --- Kimi интеграция ---
        if any(phrase in text for phrase in ["открой кими", "запусти кими", "включи кими"]):
            return kimi_integration.open_kimi_terminal()

        if any(phrase in text for phrase in ["спроси кими", "спроси у кими", "попроси кими"]):
            query = self._kimi_command(text)
            if query:
                return kimi_integration.open_kimi_terminal(prompt=query)
            return "Что спросить у Kimi, сэр?"

        if any(phrase in text for phrase in ["напиши код", "создай код", "помоги с кодом", "сделай код"]):
            query = self._kimi_command(text)
            if not query:
                query = "напиши код"
            return kimi_integration.open_kimi_terminal(prompt=query)

        # --- Системное управление ---
        if any(phrase in text for phrase in ["заблокируй компьютер", "заблокируй пк", "блокировка"]):
            return sc.lock_pc()

        if any(phrase in text for phrase in ["выключи компьютер", "выключи пк", "завершение работы"]):
            return self._dangerous(
                "Выключение компьютера",
                "Компьютер будет выключен через 30 секунд. Подтвердите.",
                sc.shutdown_pc,
            )

        if any(phrase in text for phrase in ["перезагрузи компьютер", "перезагрузи пк", "перезагрузка"]):
            return self._dangerous(
                "Перезагрузка компьютера",
                "Компьютер будет перезагружен через 30 секунд. Подтвердите.",
                sc.restart_pc,
            )

        if any(phrase in text for phrase in ["спящий режим", "усни", "сон", "переведи в сон"]):
            return self._dangerous(
                "Переход в спящий режим",
                "Компьютер будет переведён в спящий режим. Подтвердите.",
                sc.sleep_pc,
            )

        if any(phrase in text for phrase in ["отмени выключение", "отмени перезагрузку", "отмени завершение"]):
            return sc.abort_shutdown()

        # --- Wi-Fi и Bluetooth ---
        if any(phrase in text for phrase in ["wi-fi", "wifi", "вай фай", "вай-фай"]):
            if any(word in text for word in ["включи", "вруби", "подключи"]):
                return extras.wifi_on()
            if any(word in text for word in ["выключи", "отключи", "выруби"]):
                return extras.wifi_off()
            return extras.wifi_status()

        if "bluetooth" in text or "блютуз" in text or "блутуз" in text:
            if any(word in text for word in ["включи", "вруби", "подключи"]):
                return extras.bluetooth_on()
            if any(word in text for word in ["выключи", "отключи", "выруби"]):
                return extras.bluetooth_off()
            return extras.bluetooth_status()

        # --- IP-адреса ---
        if "локальный ip" in text or "мой ip" in text or "айпи" in text:
            return extras.local_ip()
        if "публичный ip" in text or "внешний ip" in text:
            return extras.public_ip()

        # --- Таймеры и напоминания ---
        timer_match = re.search(r"таймер на (\d+) (минут|минуты|минуту|секунд|секунды|секунду)", text)
        if timer_match:
            value = int(timer_match.group(1))
            unit = timer_match.group(2)
            minutes = value if "минут" in unit else max(1, value // 60)
            return extras.set_timer(minutes)

        reminder_match = re.search(r"напомни (через) (\d+) (минут|минуты|минуту|секунд|секунды|секунду)(?: (.+))?", text)
        if reminder_match:
            value = int(reminder_match.group(2))
            unit = reminder_match.group(3)
            msg = (reminder_match.group(4) or "Напоминание!").strip()
            minutes = value if "минут" in unit else max(1, value // 60)
            return extras.set_reminder(minutes, msg)

        if "отмени таймер" in text or "сбрось таймер" in text:
            return extras.cancel_timers()

        # --- Запуск программ ---
        launch_match = re.search(r"запусти (.+)", text)
        if launch_match:
            return extras.launch_program(launch_match.group(1).strip())

        if text.startswith("открой "):
            app_name = text.replace("открой ", "").strip()
            return extras.launch_program(app_name)

        if any(phrase in text for phrase in ["очисти корзину", "пусти корзину", "очистить корзину"]):
            return self._dangerous(
                "Очистка корзины",
                "Корзина будет очищена без возможности восстановления. Подтвердите.",
                sc.empty_recycle_bin,
            )

        if "скриншот" in text or "сделай снимок экрана" in text or "фото экрана" in text:
            return sc.take_screenshot()

        if any(phrase in text for phrase in ["проверь микрофон", "тест микрофона", "проверка микрофона", "запиши и воспроизведи"]):
            return self._mic_test_callback() if hasattr(self, "_mic_test_callback") else "Функция проверки не подключена."

        if any(phrase in text for phrase in ["система", "загрузка системы", "процессор", "оперативка", "ресурсы"]):
            return sc.get_system_info()

        if "процессы" in text or "что тормозит" in text:
            return sc.list_processes()

        if text.startswith("заверши процесс") or text.startswith("закрой процесс") or text.startswith("убей процесс"):
            name = text
            for prefix in ["заверши процесс", "закрой процесс", "убей процесс"]:
                name = name.replace(prefix, "")
            name = name.strip()
            if name:
                return self._dangerous(
                    f"Завершение процесса '{name}'",
                    f"Процесс {name} будет принудительно завершён. Подтвердите.",
                    lambda n=name: sc.kill_process(n),
                )
            return "Какой процесс завершить, сэр?"

        # --- Громкость ---
        if "выключи звук" in text or "без звука" in text or "mute" in text:
            return sc.mute_volume()

        match = re.search(r"громкость (\d+)", text)
        if match:
            return sc.set_volume(int(match.group(1)))

        if any(phrase in text for phrase in ["громче", "прибавь громкость", "громче сделай"]):
            return sc.change_volume(10)

        if any(phrase in text for phrase in ["тише", "убавь громкость", "тише сделай"]):
            return sc.change_volume(-10)

        # --- Яркость ---
        match = re.search(r"яркость (\d+)", text)
        if match:
            return sc.set_brightness(int(match.group(1)))

        if any(phrase in text for phrase in ["ярче", "прибавь яркость", "ярче сделай"]):
            return sc.change_brightness(10)

        if any(phrase in text for phrase in ["тускнее", "убавь яркость", "тускнее сделай"]):
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
            return "Какую клавишу нажать, сэр?"

        # --- Автозагрузка ---
        if any(phrase in text for phrase in ["включи автозагрузку", "запускайся с компьютером", "добавь в автозагрузку"]):
            return autostart.enable()

        if any(phrase in text for phrase in ["выключи автозагрузку", "убери из автозагрузки", "не запускайся с компьютером"]):
            return autostart.disable()

        if "автозагрузка" in text or "автозапуск" in text:
            return "Автозагрузка включена, сэр." if autostart.is_enabled() else "Автозагрузка отключена, сэр."

        # --- Завершение ---
        if any(word in text for word in ["стоп", "выключись", "пока", "до свидания", "завершить", "спасибо все"]):
            self.active = False
            return "До свидания, сэр. Выключаюсь."

        # --- Smart fallback: додумываем по ключевым словам ---
        fallback = self._smart_fallback(text)
        if fallback:
            return fallback

        return JarvisPersonality.get("MISUNDERSTOOD")

    def _smart_fallback(self, text):
        """Пытается угадать намерение по ключевым словам, если команда не распознана."""
        if any(word in text for word in ["музык", "песн", "трек", "плеер"]):
            return extras.play_music()

        if any(word in text for word in ["видео", "ютуб", "youtube", "ролик"]):
            import webbrowser
            webbrowser.open("https://www.youtube.com")
            return JarvisPersonality.get("SUCCESS") + " Открываю YouTube."

        if any(word in text for word in ["почта", "почту", "email", "gmail", "письмо"]):
            import webbrowser
            webbrowser.open("https://mail.google.com")
            return JarvisPersonality.get("SUCCESS") + " Открываю почту."

        if any(word in text for word in ["калькулятор", "посчитай", "сколько будет"]):
            os.system("start calc.exe")
            return JarvisPersonality.get("SUCCESS") + " Открываю калькулятор."

        if any(word in text for word in ["блокнот", "заметк", "note"]):
            os.system("start notepad.exe")
            return JarvisPersonality.get("SUCCESS") + " Открываю блокнот."

        if any(word in text for word in ["погода", "дождь", "снег", "температура"]):
            import webbrowser
            webbrowser.open("https://yandex.ru/pogoda")
            return JarvisPersonality.get("SUCCESS") + " Открываю погоду."

        return None

    def confirm_pending(self):
        """Подтверждает ожидающее опасное действие."""
        if not self.pending_action:
            return "Нет действий, требующих подтверждения."
        result = self.pending_action.execute()
        self.pending_action = None
        return JarvisPersonality.get("CONFIRMED") + " " + result

    def cancel_pending(self):
        """Отменяет ожидающее опасное действие."""
        if not self.pending_action:
            return "Нет действий для отмены."
        self.pending_action = None
        return JarvisPersonality.get("CANCELLED")
