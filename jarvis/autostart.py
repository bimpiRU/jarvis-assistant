"""Управление автозагрузкой Windows."""

import os
import winshell
from win32com.client import Dispatch
from .config import AUTO_START_BAT


def get_startup_path():
    """Возвращает путь к папке автозагрузки текущего пользователя."""
    return winshell.startup()


def enable():
    """Добавляет start.bat в автозагрузку."""
    startup = get_startup_path()
    shortcut_path = os.path.join(startup, "Jarvis Assistant.lnk")
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = AUTO_START_BAT
    shortcut.WorkingDirectory = os.path.dirname(AUTO_START_BAT)
    shortcut.IconLocation = AUTO_START_BAT
    shortcut.save()
    return f"Автозагрузка включена: {shortcut_path}"


def disable():
    """Удаляет ярлык из автозагрузки."""
    startup = get_startup_path()
    shortcut_path = os.path.join(startup, "Jarvis Assistant.lnk")
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)
        return "Автозагрузка отключена."
    return "Ярлык автозагрузки не найден."


def is_enabled():
    """Проверяет, включена ли автозагрузка."""
    startup = get_startup_path()
    return os.path.exists(os.path.join(startup, "Jarvis Assistant.lnk"))
