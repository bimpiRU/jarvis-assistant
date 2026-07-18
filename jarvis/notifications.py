"""Windows-уведомления без сторонних зависимостей."""

import ctypes
from ctypes import wintypes
import threading
import time


# Определяем структуры WinAPI вручную
class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)),
        ("cbClsExtra", wintypes.INT),
        ("cbWndExtra", wintypes.INT),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
    ]


class WindowsNotification:
    """Показывает Windows toast-уведомления через WinAPI."""

    def show(self, title: str, message: str, duration_ms: int = 5000):
        """Показывает уведомление."""
        try:
            return self._balloon_tip(title, message, duration_ms)
        except Exception as e:
            return f"Не удалось отправить уведомление: {e}"

    def _balloon_tip(self, title, message, duration_ms):
        h_instance = ctypes.windll.kernel32.GetModuleHandleW(None)

        # Создаём скрытое окно напрямую
        hwnd = ctypes.windll.user32.CreateWindowExW(
            0,
            "STATIC",
            "Jarvis",
            0,
            0, 0, 0, 0,
            None,
            None,
            h_instance,
            None,
        )

        if not hwnd:
            return "Не удалось создать окно для уведомления."

        # Создаём иконку в трее
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = 0x01 | 0x02 | 0x04  # NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.hIcon = ctypes.windll.user32.LoadIconW(0, 32516)  # IDI_INFORMATION
        nid.szTip = title[:127]

        # Добавляем иконку
        if not ctypes.windll.shell32.Shell_NotifyIconW(0, ctypes.byref(nid)):
            ctypes.windll.user32.DestroyWindow(hwnd)
            return "Не удалось добавить иконку в трей."

        # Показываем balloon
        nid.uFlags = 0x10 | 0x04 | 0x02  # NIF_INFO | NIF_TIP | NIF_ICON
        nid.dwInfoFlags = 0x01  # NIIF_INFO
        nid.szInfoTitle = title[:63]
        nid.szInfo = message[:255]
        ctypes.windll.shell32.Shell_NotifyIconW(1, ctypes.byref(nid))

        # Удаляем иконку через duration_ms
        def _remove():
            time.sleep(duration_ms / 1000.0)
            ctypes.windll.shell32.Shell_NotifyIconW(2, ctypes.byref(nid))
            ctypes.windll.user32.DestroyWindow(hwnd)

        threading.Thread(target=_remove, daemon=True).start()
        return "Уведомление отправлено."


def show_notification(title, message, duration=5):
    """Удобная функция для показа уведомления."""
    notifier = WindowsNotification()
    return notifier.show(title, message, duration_ms=duration * 1000)
