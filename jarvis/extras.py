"""Дополнительные функции: WiFi, Bluetooth, уведомления, таймеры, напоминания, запуск программ."""

import os
import subprocess
import shutil
import threading
import time
import winsound
from datetime import datetime, timedelta
from .notifications import show_notification


# ---------- Wi-Fi ----------

def wifi_status():
    """Возвращает статус Wi-Fi."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        profiles = [line.split(":", 1)[1].strip() for line in result.stdout.splitlines() if "All User Profile" in line or "Все профили пользователей" in line]
        return f"Wi-Fi сети: {', '.join(profiles[:5])}" if profiles else "Wi-Fi сети не найдены."
    except Exception as e:
        return f"Не удалось получить статус Wi-Fi: {e}"


def wifi_on():
    try:
        subprocess.run(["netsh", "interface", "set", "interface", "name=Wi-Fi", "admin=enabled"], check=True)
        return "Wi-Fi включён."
    except Exception as e:
        return f"Не удалось включить Wi-Fi: {e}"


def wifi_off():
    try:
        subprocess.run(["netsh", "interface", "set", "interface", "name=Wi-Fi", "admin=disabled"], check=True)
        return "Wi-Fi отключён."
    except Exception as e:
        return f"Не удалось отключить Wi-Fi: {e}"


# ---------- Bluetooth ----------

def bluetooth_status():
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-BluetoothDevice | Select-Object Name, Connected | Format-Table -AutoSize"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        output = result.stdout.strip()
        return output if output else "Bluetooth-устройства не найдены."
    except Exception as e:
        return f"Не удалось получить статус Bluetooth: {e}"


def bluetooth_on():
    return toggle_bluetooth("Enable")


def bluetooth_off():
    return toggle_bluetooth("Disable")


def toggle_bluetooth(action):
    """Включает или отключает Bluetooth через PnP."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"$d = Get-PnpDevice -Class Bluetooth | Where-Object {{$_.FriendlyName -like '*Bluetooth*' -or $_.InstanceId -like '*BTH*'}} | Select-Object -First 1; "
             f"if ($d) {{ $d | {action}-PnpDevice -Confirm:$false; 'OK' }} else {{ 'Bluetooth адаптер не найден' }}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        output = result.stdout.strip()
        if "OK" in output:
            return f"Bluetooth {'включён' if action == 'Enable' else 'отключён'}."
        return output or "Не удалось изменить состояние Bluetooth."
    except Exception as e:
        return f"Не удалось изменить состояние Bluetooth: {e}"


# ---------- Таймеры и напоминания ----------

_active_timers = {}


def _timer_thread(name, delay_seconds, message, on_complete):
    time.sleep(delay_seconds)
    on_complete(message)
    _active_timers.pop(name, None)


def set_timer(minutes, message=None, on_complete=None):
    """Устанавливает таймер на N минут."""
    if on_complete is None:
        on_complete = lambda msg: show_notification("⏰ Таймер", msg, duration=10)
    name = f"timer_{datetime.now().strftime('%H%M%S')}"
    msg = message or f"Таймер на {minutes} минут сработал."
    delay = int(minutes) * 60
    t = threading.Thread(target=_timer_thread, args=(name, delay, msg, on_complete), daemon=True)
    t.start()
    _active_timers[name] = t
    return f"Таймер установлен на {minutes} минут."


def set_reminder(minutes, message, on_complete=None):
    """Устанавливает напоминание через N минут."""
    if on_complete is None:
        on_complete = lambda msg: show_notification("📌 Напоминание", msg, duration=10)
    return set_timer(minutes, message, on_complete)


def cancel_timers():
    """Отменяет все активные таймеры (недоступно для daemon threads, просто очищает словарь)."""
    count = len(_active_timers)
    _active_timers.clear()
    return f"Активных таймеров сброшено: {count}."


# ---------- Запуск программ ----------

def _find_program(name):
    """Ищет программу в PATH и известных папках."""
    # Сначала в PATH
    path = shutil.which(name)
    if path:
        return path

    # Известные пути
    known_paths = {
        "spotify": os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        "discord": os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"),
        "telegram": os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
        "chrome": os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        "firefox": os.path.expandvars(r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"),
        "steam": os.path.expandvars(r"C:\Program Files (x86)\Steam\steam.exe"),
    }
    return known_paths.get(name.lower())


def launch_program(name):
    """Запускает программу по имени."""
    path = _find_program(name)
    if not path:
        # Пробуем через start
        try:
            os.system(f"start \"{name}\"")
            return f"Попытка запустить {name}."
        except Exception as e:
            return f"Не удалось найти программу: {name}. {e}"

    try:
        if " --processStart " in path:
            exe, args = path.split(" --processStart ", 1)
            subprocess.Popen([exe, "--processStart", args], shell=False)
        else:
            subprocess.Popen([path], shell=False)
        return f"Запускаю {name}."
    except Exception as e:
        return f"Не удалось запустить {name}: {e}"


def open_yandex_music():
    """Открывает приложение Яндекс Музыка или сайт."""
    import webbrowser
    import shutil

    # Пытаемся найти установленное приложение
    for app_name in ["Яндекс Музыка", "Yandex Music", "YandexMusic", "yandex-music"]:
        path = _find_program(app_name)
        if path:
            try:
                if " --processStart " in path:
                    exe, args = path.split(" --processStart ", 1)
                    subprocess.Popen([exe, "--processStart", args], shell=False)
                else:
                    subprocess.Popen([path], shell=False)
                return f"Запускаю {app_name}."
            except Exception:
                pass

    # Пробуем URI-схему (если приложение установлено из Microsoft Store)
    try:
        os.system("start yandexmusic://")
        return "Открываю Яндекс Музыку."
    except Exception:
        pass

    # Fallback — открываем сайт
    try:
        webbrowser.open("https://music.yandex.ru/home")
        return "Открываю Яндекс Музыку в браузере."
    except Exception as e:
        return f"Не удалось открыть Яндекс Музыку: {e}"


def play_music():
    """Включает музыку: ищет установленный музыкальный плеер и запускает его.

    Если не найдено ни одного приложения — fallback на Яндекс Музыку.
    """
    music_apps = [
        ("Яндекс Музыка", "yandexmusic"),
        ("Yandex Music", "yandex-music"),
        ("Spotify", "spotify"),
        ("VK Музыка", "vk music"),
        ("Boom", "boom"),
        ("Apple Music", "apple music"),
        ("Deezer", "deezer"),
        ("Tidal", "tidal"),
    ]

    for display_name, search_name in music_apps:
        path = _find_program(display_name) or _find_program(search_name)
        if path:
            try:
                if " --processStart " in path:
                    exe, args = path.split(" --processStart ", 1)
                    subprocess.Popen([exe, "--processStart", args], shell=False)
                else:
                    subprocess.Popen([path], shell=False)
                return f"Включаю {display_name}."
            except Exception:
                pass

    # Если приложений нет — открываем Яндекс Музыку в браузере
    return open_yandex_music()


# ---------- Дополнительные пентест-возможности (только информационные) ----------

def local_ip():
    """Возвращает локальный IP-адрес."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -eq 'Dhcp'}).IPAddress"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        ip = result.stdout.strip()
        return f"Локальный IP: {ip}" if ip else "Не удалось определить IP."
    except Exception as e:
        return f"Ошибка: {e}"


def public_ip():
    """Возвращает публичный IP-адрес."""
    try:
        import requests
        ip = requests.get("https://api.ipify.org", timeout=5).text
        return f"Публичный IP: {ip}"
    except Exception as e:
        return f"Не удалось получить публичный IP: {e}"
