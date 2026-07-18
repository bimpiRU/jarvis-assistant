"""Wake-word детектор для активации Джарвиса голосом."""

import threading
import time
from .config import WAKE_WORDS


class WakeWordDetector:
    """Непрерывно слушает микрофон и активируется при произнесении wake word."""

    def __init__(self, speech, on_wake=None):
        self.speech = speech
        self.on_wake = on_wake
        self.listening = False
        self.thread = None
        self.stop_event = threading.Event()

    def _listen_loop(self):
        """Цикл прослушивания."""
        while self.listening and not self.stop_event.is_set():
            text = self.speech.listen_for_wake(stop_event=self.stop_event)
            if text:
                print(f"[Wake] слышал: {text}")
                if any(word in text for word in WAKE_WORDS):
                    print("[Wake] активация!")
                    if self.on_wake:
                        self.on_wake()
            time.sleep(0.1)

    def start(self):
        """Запускает фоновое прослушивание."""
        if self.listening:
            return
        self.listening = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Останавливает прослушивание."""
        self.listening = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)
