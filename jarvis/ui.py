"""Tkinter-интерфейс для Jarvis."""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import sys
import winsound
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

        self._build_ui()
        self._play_activation_sound()
        self.jarvis.greet()
        self.jarvis.start_wake_word()

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

        # Кнопка микрофона
        self.mic_button = tk.Button(
            self.root,
            text="🎤 Удерживайте для голосовой команды",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#151515",
            activebackground="#00d4ff",
            activeforeground="#000000",
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=14,
            cursor="hand2",
        )
        self.mic_button.pack(pady=10)
        self.mic_button.bind("<ButtonPress-1>", self._on_mic_press)
        self.mic_button.bind("<ButtonRelease-1>", self._on_mic_release)

        # История диалога
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

        wake_btn = tk.Button(
            controls,
            text="🔔 Wake word",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#1a1a1a",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            command=self._toggle_wake,
        )
        wake_btn.pack(side=tk.LEFT, padx=5)

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
            command=self._on_close,
        )
        exit_btn.pack(side=tk.LEFT, padx=5)

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

    def _on_mic_press(self, event=None):
        self.jarvis.stop_wake_word()
        self.status_label.config(text="Слушаю...")
        self.mic_button.config(bg="#00d4ff", fg="#000000")
        self._set_status_dot("#ffaa00")
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _on_mic_release(self, event=None):
        self.mic_button.config(bg="#151515", fg="#ffffff")

    def _listen_thread(self):
        text, result = self.jarvis.listen_and_respond()
        if text:
            self.root.after(0, lambda: self._add_history("Вы", text))

        # Обработка голосового подтверждения/отмены
        if isinstance(result, DangerousAction):
            # После опасного действия слушаем подтверждение
            self.root.after(0, lambda: self.status_label.config(text="Жду подтверждения..."))
            confirm_text = self.jarvis.speech.listen(use_online_fallback=not self.jarvis.offline_only)
            if confirm_text:
                self.root.after(0, lambda: self._add_history("Вы", confirm_text))
                if any(word in confirm_text for word in ["подтверждаю", "да", "выполняй", "делай", "конечно"]):
                    self.jarvis.confirm_pending()
                elif any(word in confirm_text for word in ["отмена", "нет", "не надо", "стоп"]):
                    self.jarvis.cancel_pending()
                else:
                    self.jarvis.cancel_pending()
            else:
                self.jarvis.cancel_pending()

        self.jarvis.start_wake_word()
        if not self.jarvis.is_active():
            self.root.after(1000, self._on_close)

    def _toggle_wake(self):
        if self.jarvis.wake_detector and self.jarvis.wake_detector.listening:
            self.jarvis.stop_wake_word()
            self.status_label.config(text="Wake word отключён")
            self._set_status_dot("#ff4444")
        else:
            self.jarvis.start_wake_word()
            self.status_label.config(text="Система онлайн | Скажите 'Джарвис'")
            self._set_status_dot("#00ff88")

    def _on_close(self):
        self.jarvis.stop()
        self.root.destroy()
        sys.exit(0)

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
