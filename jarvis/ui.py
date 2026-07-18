"""Tkinter-интерфейс для Jarvis с системным треем."""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import sys
import winsound

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except Exception:
    HAS_PYSTRAY = False

from .assistant import Jarvis
from .dangerous_action import DangerousAction
from .jarvis_phrases import JarvisPersonality
from .mic_diagnostics import list_microphones, test_microphone
from . import config as jarvis_config


class JarvisUI:
    """Окно управления ассистентом в стиле Джарвиса."""

    def __init__(self, offline_only=False, use_wake_word=True, mic_device=None):
        self.root = tk.Tk()
        self.root.title("Jarvis Assistant")
        self.root.geometry("750x650")
        self.root.configure(bg="#0a0a0a")
        self.root.resizable(False, False)

        self.jarvis = Jarvis(
            on_listen=self._on_listen,
            on_response=self._on_response,
            offline_only=offline_only,
            use_wake_word=use_wake_word,
            mic_device=mic_device,
        )
        self.jarvis.on_dangerous_action = self._on_dangerous_action

        self.tray_icon = None
        self._tray_thread = None
        self._force_exit = False

        self._build_ui()
        self._setup_tray()
        self._play_activation_sound()
        self.jarvis.greet()
        self.jarvis.start_wake_word()

    @staticmethod
    def _create_tray_image():
        """Генерирует простую иконку для трея."""
        width = 64
        height = 64
        image = Image.new("RGB", (width, height), "#0a0a0a")
        dc = ImageDraw.Draw(image)
        dc.ellipse([4, 4, width - 4, height - 4], outline="#00d4ff", width=4)
        dc.text((width // 2 - 10, height // 2 - 14), "J", fill="#00d4ff", font=None)
        return image

    def _setup_tray(self):
        """Запускает иконку в системном трее."""
        if not HAS_PYSTRAY:
            return

        def on_show(icon, item):
            self.root.after(0, self._show_window)

        def on_exit(icon, item):
            self._force_exit = True
            self.root.after(0, self._exit_app)

        menu = pystray.Menu(
            pystray.MenuItem("Открыть", on_show),
            pystray.MenuItem("Выход", on_exit),
        )

        self.tray_icon = pystray.Icon(
            "jarvis",
            self._create_tray_image(),
            "Jarvis Assistant",
            menu,
        )

        def run_tray():
            self.tray_icon.run()

        self._tray_thread = threading.Thread(target=run_tray, daemon=True)
        self._tray_thread.start()

    def _hide_window(self):
        """Сворачивает окно в трей."""
        self.root.withdraw()
        if self.tray_icon:
            self.tray_icon.notify("Джарвис продолжает слушать в фоне.", "Jarvis")

    def _show_window(self):
        """Восстанавливает окно из трея."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _exit_app(self):
        """Полностью завершает приложение."""
        self.jarvis.stop()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()
        sys.exit(0)

    def _build_ui(self):
        # Верхняя панель со статусом
        header = tk.Frame(self.root, bg="#0a0a0a")
        header.pack(fill=tk.X, padx=20, pady=(15, 5))

        self.status_dot = tk.Canvas(header, width=12, height=12, bg="#0a0a0a", highlightthickness=0)
        self.status_dot.pack(side=tk.LEFT, padx=(0, 10))
        self._set_status_dot("#00ff88")

        self.status_label = tk.Label(
            header,
            text="Система онлайн | Ожидаю команду",
            font=("Consolas", 11),
            fg="#00d4ff",
            bg="#0a0a0a",
        )
        self.status_label.pack(side=tk.LEFT)

        # Заголовок
        title = tk.Label(
            self.root,
            text="J.A.R.V.I.S.",
            font=("Consolas", 32, "bold"),
            fg="#00d4ff",
            bg="#0a0a0a",
        )
        title.pack(pady=(10, 0))

        subtitle = tk.Label(
            self.root,
            text="Just A Rather Very Intelligent System",
            font=("Consolas", 10),
            fg="#666666",
            bg="#0a0a0a",
        )
        subtitle.pack(pady=(0, 15))

        # Индикатор режима
        mode_text = "ОФЛАЙН" if self.jarvis.offline_only else "ОНЛАЙН + ОФЛАЙН"
        self.mode_label = tk.Label(
            self.root,
            text=f"Режим: {mode_text} | Активация: {'ДЖАРВИС' if self.jarvis.use_wake_word else 'КНОПКА'}",
            font=("Consolas", 9),
            fg="#888888",
            bg="#0a0a0a",
        )
        self.mode_label.pack(pady=(0, 5))

        # Индикатор уровня звука
        level_frame = tk.Frame(self.root, bg="#0a0a0a")
        level_frame.pack(fill=tk.X, padx=20, pady=(0, 5))

        tk.Label(
            level_frame,
            text="Mic:",
            font=("Consolas", 9),
            fg="#888888",
            bg="#0a0a0a",
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.level_bar = ttk.Progressbar(
            level_frame,
            orient=tk.HORIZONTAL,
            mode="determinate",
            maximum=32768,
            length=200,
        )
        self.level_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.level_value = tk.Label(
            level_frame,
            text="0",
            font=("Consolas", 9),
            fg="#00d4ff",
            bg="#0a0a0a",
            width=6,
        )
        self.level_value.pack(side=tk.LEFT, padx=(5, 0))

        # Панель настроек микрофона
        settings_frame = tk.Frame(self.root, bg="#0a0a0a")
        settings_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.mic_var = tk.StringVar()
        mics = list_microphones()
        mic_names = [f"{m['index']}: {m['name']}" for m in mics]
        if mic_names:
            self.mic_var.set(mic_names[0])

        tk.Label(
            settings_frame,
            text="Микрофон:",
            font=("Consolas", 9),
            fg="#888888",
            bg="#0a0a0a",
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.mic_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.mic_var,
            values=mic_names,
            width=35,
            state="readonly",
        )
        self.mic_combo.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            settings_frame,
            text="Порог:",
            font=("Consolas", 9),
            fg="#888888",
            bg="#0a0a0a",
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.threshold_scale = tk.Scale(
            settings_frame,
            from_=10,
            to=1000,
            orient=tk.HORIZONTAL,
            bg="#0a0a0a",
            fg="#00d4ff",
            highlightthickness=0,
            troughcolor="#1a1a1a",
            activebackground="#00d4ff",
            length=120,
            showvalue=0,
            command=self._on_threshold_change,
        )
        self.threshold_scale.set(jarvis_config.ENERGY_THRESHOLD)
        self.threshold_scale.pack(side=tk.LEFT, padx=(0, 10))

        self.threshold_label = tk.Label(
            settings_frame,
            text=str(jarvis_config.ENERGY_THRESHOLD),
            font=("Consolas", 9),
            fg="#00d4ff",
            bg="#0a0a0a",
            width=5,
        )
        self.threshold_label.pack(side=tk.LEFT, padx=(0, 10))

        diag_btn = tk.Button(
            settings_frame,
            text="Диагностика",
            font=("Segoe UI", 8),
            fg="#ffffff",
            bg="#1a1a1a",
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=3,
            command=self._run_diagnostics,
        )
        diag_btn.pack(side=tk.LEFT)

        self.jarvis.on_audio_level = self._on_audio_level


        self.history = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg="#121212",
            fg="#e0e0e0",
            insertbackground="#00d4ff",
            relief=tk.FLAT,
            padx=12,
            pady=12,
        )
        self.history.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.history.insert(tk.END, "=== История диалога ===\n")
        self.history.config(state=tk.DISABLED)

        # Панель управления
        controls = tk.Frame(self.root, bg="#0a0a0a")
        controls.pack(pady=(0, 10))

        confirm_btn = tk.Button(
            controls,
            text="✓ Подтвердить",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#1a3a1a",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            command=self._confirm_pending,
        )
        confirm_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(
            controls,
            text="✕ Отменить",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#3a1a1a",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            command=self._cancel_pending,
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        mic_test_btn = tk.Button(
            controls,
            text="🎙 Проверить микрофон",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#1a1a3a",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            command=self._test_microphone,
        )
        mic_test_btn.pack(side=tk.LEFT, padx=5)

        exit_btn = tk.Button(
            controls,
            text="Выход",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#330000",
            activebackground="#ff0000",
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=6,
            command=lambda: self._on_close(force=True),
        )
        exit_btn.pack(side=tk.LEFT, padx=5)

        # Кнопка сворачивания в трей
        tray_btn = tk.Button(
            controls,
            text="В трей",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#1a1a1a",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            command=self._hide_window,
        )
        tray_btn.pack(side=tk.LEFT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_status_dot(self, color):
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 10, 10, fill=color, outline="")

    def _add_history(self, speaker, text):
        self.history.config(state=tk.NORMAL)
        color = "#00d4ff" if speaker == "Jarvis" else "#ffffff"
        self.history.insert(tk.END, f"{speaker}: ")
        self.history.insert(tk.END, f"{text}\n", color)
        self.history.tag_config(color, foreground=color)
        self.history.see(tk.END)
        self.history.config(state=tk.DISABLED)

    def _play_activation_sound(self):
        """Короткий звук активации."""
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def _on_listen(self, text):
        self.root.after(0, lambda: self.status_label.config(text=text))
        self.root.after(0, lambda: self._set_status_dot("#ffaa00"))

    def _on_response(self, text):
        self.root.after(0, lambda: self._add_history("Jarvis", text))
        self.root.after(0, lambda: self.status_label.config(text="Система онлайн | Ожидаю команду"))
        self.root.after(0, lambda: self._set_status_dot("#00ff88"))

    def _on_audio_level(self, level):
        """Обновляет индикатор уровня звука."""
        self.root.after(0, lambda: self.level_bar.config(value=level))
        self.root.after(0, lambda: self.level_value.config(text=f"{int(level)}"))

    def _on_threshold_change(self, value):
        """Изменяет порог активации микрофона."""
        threshold = int(float(value))
        jarvis_config.ENERGY_THRESHOLD = threshold
        self.threshold_label.config(text=str(threshold))

    def _run_diagnostics(self):
        """Запускает диагностику микрофона."""
        def diag():
            device_str = self.mic_var.get()
            device = int(device_str.split(":", 1)[0]) if device_str else None
            result = test_microphone(duration=3, device=device)
            if "error" in result:
                msg = f"Ошибка: {result['error']}"
            else:
                msg = (
                    f"Диагностика микрофона\n"
                    f"RMS: {result['rms']:.1f}\n"
                    f"Peak: {result['peak']:.1f}\n"
                    f"Уровень: {result['db']:.1f} dB\n"
                    f"Статус: {result['status']}"
                )
            self.root.after(0, lambda: messagebox.showinfo("Диагностика микрофона", msg))

        threading.Thread(target=diag, daemon=True).start()

    def _on_dangerous_action(self, action):
        """Показывает диалог подтверждения для опасного действия."""
        self.root.after(0, lambda: self._show_confirmation_dialog(action))

    def _show_confirmation_dialog(self, action):
        result = messagebox.askyesno(
            "Подтверждение действия",
            f"{action.title}\n\n{action.description}\n\nПодтвердить?",
            icon="warning",
        )
        if result:
            self._confirm_pending()
        else:
            self._cancel_pending()

    def _confirm_pending(self):
        threading.Thread(target=self.jarvis.confirm_pending, daemon=True).start()

    def _cancel_pending(self):
        threading.Thread(target=self.jarvis.cancel_pending, daemon=True).start()

    def _test_microphone(self):
        """Запускает тест микрофона."""
        def run_test():
            result = self.jarvis.test_microphone(duration=5)
            self.root.after(0, lambda: self._add_history("Jarvis", result))

        self.jarvis.stop_wake_word()
        threading.Thread(target=run_test, daemon=True).start()

    def _on_close(self, force=False):
        """При закрытии окна сворачивает в трей, если не force."""
        if force or self._force_exit:
            self._exit_app()
        else:
            self._hide_window()

    def run(self):
        self.root.mainloop()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Jarvis Assistant")
    parser.add_argument("--offline", action="store_true", help="Только офлайн-распознавание (Vosk)")
    parser.add_argument("--no-wake", action="store_true", help="Отключить активацию по слову")
    parser.add_argument("--device", type=int, default=None, help="Индекс микрофона (sounddevice)")
    args = parser.parse_args()

    app = JarvisUI(offline_only=args.offline, use_wake_word=not args.no_wake, mic_device=args.device)
    app.run()
