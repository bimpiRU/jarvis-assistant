"""Интеграция с Kimi Code CLI."""

import os
import subprocess
import shutil
import tempfile


def find_kimi():
    """Находит исполняемый файл kimi в PATH."""
    return shutil.which("kimi")


def _escape_for_ps(text):
    """Экранирует строку для PowerShell."""
    return text.replace("'", "''").replace('"', '`"')


def open_kimi_terminal(prompt=None, cwd=None):
    """Открывает новый терминал с запущенной Kimi CLI.

    Если prompt передан, Kimi получит его сразу через режим -p (non-interactive).
    После выполнения терминал останется открытым благодаря -NoExit.
    """
    kimi = find_kimi()
    if not kimi:
        return "Kimi CLI не найден. Убедитесь, что он установлен и добавлен в PATH."

    work_dir = cwd or os.path.expanduser("~")
    os.makedirs(work_dir, exist_ok=True)

    # Формируем команду для PowerShell
    if prompt:
        escaped = _escape_for_ps(prompt)
        # Запускаем kimi -p, затем оставляем оболочку открытой
        ps_cmd = (
            f"cd '{work_dir}'; "
            f"Write-Host 'Запуск Kimi с запросом: {escaped}' -ForegroundColor Cyan; "
            f"& '{kimi}' -p '{escaped}'; "
            f"Write-Host 'Kimi завершил работу. Окно остаётся открытым.' -ForegroundColor Green"
        )
    else:
        ps_cmd = (
            f"cd '{work_dir}'; "
            f"Write-Host 'Запуск интерактивной сессии Kimi...' -ForegroundColor Cyan; "
            f"& '{kimi}'"
        )

    # Пробуем Windows Terminal
    wt = shutil.which("wt")
    if wt:
        try:
            subprocess.Popen(
                [
                    wt,
                    "new-tab",
                    "-d",
                    work_dir,
                    "powershell",
                    "-NoExit",
                    "-Command",
                    ps_cmd,
                ],
                shell=False,
            )
            return "Открываю Kimi в новой вкладке Windows Terminal."
        except Exception:
            pass

    # Fallback: обычный PowerShell
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoExit",
                "-Command",
                ps_cmd,
            ],
            cwd=work_dir,
            shell=False,
        )
        return "Открываю Kimi в новом окне PowerShell."
    except Exception as e:
        return f"Не удалось открыть Kimi: {e}"


def ask_kimi(prompt, cwd=None):
    """Запускает Kimi в фоне с prompt и возвращает ответ (non-interactive)."""
    kimi = find_kimi()
    if not kimi:
        return None, "Kimi CLI не найден."

    work_dir = cwd or os.path.expanduser("~")
    try:
        result = subprocess.run(
            [kimi, "-p", prompt],
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            output += f"\n[Ошибка: {result.stderr.strip()}]"
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Kimi не ответил вовремя (timeout 120 сек)."
    except Exception as e:
        return False, f"Ошибка запуска Kimi: {e}"
