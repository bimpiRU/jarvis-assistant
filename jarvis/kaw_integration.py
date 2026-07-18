"""Интеграция с Kimi Approve Watch."""

import os
import subprocess
from .logger import logger

KAW_DIR = os.path.join(os.path.expanduser("~"), "kimi-approve-watch")


def _run_ps(script_name, args=None, wait=False):
    """Запускает PowerShell-скрипт из kimi-approve-watch."""
    script_path = os.path.join(KAW_DIR, script_name)
    if not os.path.exists(script_path):
        return f"Скрипт не найден: {script_path}. Установите kimi-approve-watch."

    ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    cmd = [
        ps,
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", script_path,
    ]
    if args:
        cmd.extend(args)

    try:
        logger.info(f"[KAW] Запуск: {script_name} {' '.join(args or [])}")
        if wait:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=30,
            )
            return result.stdout.strip() or result.stderr.strip() or f"{script_name} выполнен."
        else:
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            return f"{script_name} запущен в фоне."
    except Exception as e:
        logger.exception(f"[KAW] Ошибка запуска {script_name}: {e}")
        return f"Ошибка запуска {script_name}: {e}"


def start_kaw():
    """Запускает watcher и stabilizer."""
    return _run_ps("start-all.ps1")


def stop_kaw():
    """Останавливает watcher и stabilizer."""
    return _run_ps("stop-watcher.ps1")


def status_kaw():
    """Возвращает статус watcher/stabilizer."""
    return _run_ps("status.ps1", wait=True)


def enable_stabilizer():
    """Создаёт файл stabilizer.enabled."""
    flag = os.path.join(KAW_DIR, "stabilizer.enabled")
    try:
        with open(flag, "w") as f:
            f.write("")
        return "Стабилизатор включён. Запустите watcher для применения."
    except Exception as e:
        return f"Ошибка: {e}"


def disable_stabilizer():
    """Удаляет файл stabilizer.enabled."""
    flag = os.path.join(KAW_DIR, "stabilizer.enabled")
    try:
        if os.path.exists(flag):
            os.remove(flag)
            return "Стабилизатор отключён."
        return "Стабилизатор уже был отключён."
    except Exception as e:
        return f"Ошибка: {e}"


def is_installed():
    """Проверяет, установлен ли kimi-approve-watch."""
    return os.path.exists(os.path.join(KAW_DIR, "start-all.ps1"))


def _startup_shortcut_path():
    """Возвращает путь к ярлыку автозагрузки KAW."""
    startup = os.path.join(
        os.path.expanduser("~"),
        "AppData",
        "Roaming",
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
        "Kimi Approve Watch.lnk",
    )
    return startup


def enable_autostart():
    """Добавляет KAW в автозагрузку Windows."""
    try:
        from win32com.client import Dispatch
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(_startup_shortcut_path())
        shortcut.Targetpath = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        shortcut.Arguments = f'-NoProfile -ExecutionPolicy Bypass -File "{os.path.join(KAW_DIR, "start-all.ps1")}"'
        shortcut.WorkingDirectory = KAW_DIR
        shortcut.IconLocation = os.path.join(KAW_DIR, "kaw.ps1")
        shortcut.save()
        return "Kimi Approve Watch добавлен в автозагрузку."
    except Exception as e:
        return f"Ошибка: {e}"


def disable_autostart():
    """Удаляет KAW из автозагрузки Windows."""
    path = _startup_shortcut_path()
    try:
        if os.path.exists(path):
            os.remove(path)
            return "Kimi Approve Watch убран из автозагрузки."
        return "Kimi Approve Watch не был в автозагрузке."
    except Exception as e:
        return f"Ошибка: {e}"


def is_autostart_enabled():
    """Проверяет, включена ли автозагрузка KAW."""
    return os.path.exists(_startup_shortcut_path())
