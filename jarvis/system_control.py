"""Расширенное управление системой Windows."""

import os
import subprocess
import ctypes
import time
import psutil
import pyautogui
from datetime import datetime


def lock_pc():
    """Блокирует компьютер."""
    ctypes.windll.user32.LockWorkStation()
    return "Компьютер заблокирован."


def shutdown_pc():
    """Выключает компьютер."""
    subprocess.call("shutdown /s /t 10 /c 'Выключение по команде Джарвиса'", shell=True)
    return "Выключаю компьютер через 10 секунд."


def restart_pc():
    """Перезагружает компьютер."""
    subprocess.call("shutdown /r /t 10 /c 'Перезагрузка по команде Джарвиса'", shell=True)
    return "Перезагружаю компьютер через 10 секунд."


def sleep_pc():
    """Переводит компьютер в спящий режим."""
    subprocess.call("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
    return "Перевожу в спящий режим."


def empty_recycle_bin():
    """Очищает корзину."""
    try:
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 1)
        return "Корзина очищена."
    except Exception as e:
        return f"Не удалось очистить корзину: {e}"


def take_screenshot():
    """Делает скриншот и сохраняет на рабочий стол."""
    try:
        screenshot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Jarvis_Screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        filename = os.path.join(screenshot_dir, f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        pyautogui.screenshot(filename)
        return f"Скриншот сохранён: {filename}"
    except Exception as e:
        return f"Не удалось сделать скриншот: {e}"


def set_volume(level):
    """Устанавливает громкость от 0 до 100."""
    try:
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        volume.SetMasterVolumeLevelScalar(level / 100, None)
        return f"Громкость установлена на {level}%."
    except Exception as e:
        return f"Не удалось установить громкость: {e}"


def change_volume(delta):
    """Изменяет громкость на +/- delta %."""
    try:
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        current = volume.GetMasterVolumeLevelScalar() * 100
        new_level = max(0, min(100, current + delta))
        volume.SetMasterVolumeLevelScalar(new_level / 100, None)
        return f"Громкость изменена на {int(new_level)}%."
    except Exception as e:
        return f"Не удалось изменить громкость: {e}"


def set_brightness(level):
    """Устанавливает яркость экрана от 0 до 100."""
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return f"Яркость установлена на {level}%."
    except Exception as e:
        return f"Не удалось установить яркость: {e}"


def change_brightness(delta):
    """Изменяет яркость на +/- delta %."""
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness()[0]
        new_level = max(0, min(100, current + delta))
        sbc.set_brightness(new_level)
        return f"Яркость изменена на {int(new_level)}%."
    except Exception as e:
        return f"Не удалось изменить яркость: {e}"


def get_system_info():
    """Возвращает краткую информацию о системе."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return (
            f"CPU: {cpu}% | RAM: {ram.percent}% ({ram.used // (1024**3)} / {ram.total // (1024**3)} ГБ) | "
            f"Диск: {disk.percent}% занято"
        )
    except Exception as e:
        return f"Не удалось получить информацию о системе: {e}"


def list_processes(limit=5):
    """Возвращает список топ-процессов по потреблению CPU."""
    try:
        procs = sorted(
            psutil.process_iter(["pid", "name", "cpu_percent"]),
            key=lambda p: p.info["cpu_percent"] or 0,
            reverse=True,
        )[:limit]
        return "Топ процессов:\n" + "\n".join(
            f"{p.info['name']} (PID {p.info['pid']}): {p.info['cpu_percent']}%" for p in procs
        )
    except Exception as e:
        return f"Не удалось получить список процессов: {e}"


def kill_process(name):
    """Завершает процесс по имени."""
    try:
        killed = []
        for proc in psutil.process_iter(["pid", "name"]):
            if name.lower() in proc.info["name"].lower():
                proc.terminate()
                killed.append(proc.info["name"])
        return f"Завершены процессы: {', '.join(killed)}" if killed else f"Процессы с именем '{name}' не найдены."
    except Exception as e:
        return f"Не удалось завершить процесс: {e}"


def type_text(text):
    """Печатает текст в активное окно."""
    try:
        pyautogui.typewrite(text, interval=0.01)
        return "Текст напечатан."
    except Exception as e:
        return f"Не удалось напечатать текст: {e}"


def press_key(key):
    """Нажимает клавишу или комбинацию."""
    try:
        pyautogui.press(key)
        return f"Нажата клавиша {key}."
    except Exception as e:
        return f"Не удалось нажать клавишу: {e}"


def click_mouse():
    """Клик левой кнопкой мыши."""
    try:
        pyautogui.click()
        return "Клик выполнен."
    except Exception as e:
        return f"Не удалось кликнуть: {e}"


def mute_volume():
    """Включает/выключает звук."""
    try:
        pyautogui.press("volumemute")
        return "Звук переключён."
    except Exception as e:
        return f"Не удалось переключить звук: {e}"


def open_path(path):
    """Открывает файл или папку."""
    if os.path.exists(path):
        os.startfile(path)
        return f"Открываю {path}."
    return f"Путь не найден: {path}."
