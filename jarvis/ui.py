"""Tkinter-интерфейс для Jarvis."""

import tkinter as tk
from tkinter import scrolledtext
import threading
import sys
from .assistant import Jarvis


class JarvisUI:
    """Простое окно управления ассистентом."""

    def __init__(self, offline_only=False, use_wake_word=True):
        self.root = tk.Tk()
        self.root.title("Jarvis Assistant")
        self.root.geometry("700x600")
        self.root.configure(bg="#0f0f0f")
        self.root.resizable(False, False)

        self.jarvis = Jarvis(
            on_listen=self._on_listen,
            on_response=self._on_response,
            offline_only=offline_only,
            use_wake_word=use_wake_word,
        )

        self._build_ui()
        self.jarvis.greet()
        self.jarvis.start_wake_word()

    def _build_ui(self):
        # Заголовок
        title = tk.Label(
            self.root,
            text="J.A.R.V.I.S.",
            font=("Consolas", 28, "bold"),
            fg="#00d4ff",
            bg="#0f0f0f",
        )
        title.pack(pady=(20, 5))

        subtitle = tk.Label(
            self.root,
            text="Just A Rather Very Intelligent System",
            font=("Consolas", 10),
            fg="#888888",
            bg="#0f0f0f",
        )
        subtitle.pack(pady=(0, 10))

        # Индикатор статуса
        self.status_label = tk.Label(
            self.root,
            text="Готов к работе | Скажите 'Джарвис'",
            font=("Segoe UI", 12),
            fg="#00d4ff",
            bg="#0f0f0f",
        )
        self.status_label.pack(pady=(0, 10))

        # Кнопка микрофона
        self.mic_button = tk.Button(
            self.root,
            text="🎤 Удерживайте для голосовой команды",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#1a1a1a",
            activebackground="#00d4ff",
            activeforeground="#000000",
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=12,
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
            bg="#1a1a1a",
            fg="#eeeeee",
            insertbackground="#00d4ff",
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.history.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.history.insert(tk.END, "=== История диалога ===\n")
        self.history.config(state=tk.DISABLED)

        # Кнопки управления
        controls = tk.Frame(self.root, bg="#0f0f0f")
        controls.pack(pady=(0, 10))

        wake_btn = tk.Button(
            controls,
            text="Переключить wake word",
            font=("Segoe UI", 10),
            fg="#ffffff",
            bg="#1a1a1a",
            relief=tk.FLAT,
            bd=0,
            padx=15,
            pady=8,
            command=self._toggle_wake,
        )
        wake_btn.pack(side=tk.LEFT, padx=5)

        exit_btn = tk.Button(
            controls,
            text="Выход",
            font=("Segoe UI", 10),
            fg="#ffffff",
            bg="#330000",
            activebackground="#ff0000",
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=8,
            command=self._on_close,
        )
        exit_btn.pack(side=tk.LEFT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _add_history(self, speaker, text):
        self.history.config(state=tk.NORMAL)
        self.history.insert(tk.END, f"{speaker}: {text}\n")
        self.history.see(tk.END)
        self.history.config(state=tk.DISABLED)

    def _on_listen(self, text):
        self.root.after(0, lambda: self.status_label.config(text=text))

    def _on_response(self, text):
        self.root.after(0, lambda: self._add_history("Jarvis", text))
        self.root.after(0, lambda: self.status_label.config(text="Готов к работе | Скажите 'Джарвис'"))

    def _on_mic_press(self, event=None):
        self.jarvis.stop_wake_word()
        self.status_label.config(text="Слушаю...")
        self.mic_button.config(bg="#00d4ff", fg="#000000")
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _on_mic_release(self, event=None):
        self.mic_button.config(bg="#1a1a1a", fg="#ffffff")

    def _listen_thread(self):
        text, response = self.jarvis.listen_and_respond()
        if text:
            self.root.after(0, lambda: self._add_history("Вы", text))
        self.jarvis.start_wake_word()
        if not self.jarvis.is_active():
            self.root.after(1000, self._on_close)

    def _toggle_wake(self):
        if self.jarvis.wake_detector and self.jarvis.wake_detector.listening:
            self.jarvis.stop_wake_word()
            self.status_label.config(text="Wake word отключён")
        else:
            self.jarvis.start_wake_word()
            self.status_label.config(text="Готов к работе | Скажите 'Джарвис'")

    def _on_close(self):
        self.jarvis.stop()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        self.root.mainloop()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Jarvis Assistant")
    parser.add_argument("--offline", action="store_true", help="Работать только офлайн (Vosk)")
    parser.add_argument("--no-wake", action="store_true", help="Отключить wake word")
    args = parser.parse_args()

    app = JarvisUI(offline_only=args.offline, use_wake_word=not args.no_wake)
    app.run()
