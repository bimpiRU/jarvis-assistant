"""Wake-word детектор для активации Джарвиса голосом."""

import threading
import time
import json
import numpy as np
import sounddevice as sd
from vosk import KaldiRecognizer

from . import config as jarvis_config


class WakeWordDetector:
    """Непрерывно слушает микрофон и активируется при произнесении wake word."""

    def __init__(self, speech, on_wake=None):
        self.speech = speech
        self.on_wake = on_wake
        self.listening = False
        self.thread = None
        self.stop_event = threading.Event()
        self.sample_rate = jarvis_config.SAMPLE_RATE
        self.block_size = 1024
        self.audio_queue = None
        self._stream = None
        self._recognizer = None
        self._last_audio_level = 0.0

        if self.speech.vosk_model:
            # Создаём распознаватель, заточенный только на wake words
            grammar = json.dumps(jarvis_config.WAKE_WORDS + ["[unk]"])
            self._recognizer = KaldiRecognizer(self.speech.vosk_model, self.sample_rate, grammar)

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Wake] Audio status: {status}")
        if self.audio_queue is not None:
            self.audio_queue.put(indata.copy())
            # Обновляем уровень звука
            self._last_audio_level = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))

    def get_audio_level(self):
        """Возвращает последний уровень звука (RMS)."""
        return self._last_audio_level

    def _listen_loop(self):
        """Цикл прослушивания."""
        self.audio_queue = Queue()

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                dtype="int16",
                channels=1,
                callback=self._callback,
            )

            with self._stream:
                # Пропускаем шум
                for _ in range(int(0.3 * self.sample_rate / self.block_size)):
                    try:
                        self.audio_queue.get(timeout=0.2)
                    except Empty:
                        continue

                print("[Wake] Ожидаю слова 'Джарвис'...")
                while self.listening and not self.stop_event.is_set():
                    try:
                        block = self.audio_queue.get(timeout=0.1)
                    except Empty:
                        continue

                    # Проверяем энергию
                    energy = np.sqrt(np.mean(block.astype(np.float32) ** 2))
                    if energy < jarvis_config.ENERGY_THRESHOLD * 0.5:
                        continue

                    # Короткая буферизация для распознавания
                    phrase_buffer = [block]
                    silence = 0.0
                    start_time = time.time()

                    while silence < jarvis_config.PAUSE_THRESHOLD and time.time() - start_time < 3:
                        try:
                            block = self.audio_queue.get(timeout=0.1)
                        except Empty:
                            continue
                        phrase_buffer.append(block)
                        e = np.sqrt(np.mean(block.astype(np.float32) ** 2))
                        if e < jarvis_config.ENERGY_THRESHOLD * 0.5:
                            silence += len(block) / self.sample_rate
                        else:
                            silence = 0

                    audio = np.concatenate(phrase_buffer, axis=0)
                    text = self._recognize_wake(audio)
                    if text:
                        print(f"[Wake] распознано: {text}")
                        if self.on_wake:
                            self.on_wake()

        except Exception as e:
            print(f"[Wake] Ошибка: {e}")
        finally:
            self.audio_queue = None
            self._stream = None

    def _recognize_wake(self, audio):
        """Распознаёт только wake words."""
        if self._recognizer is None:
            return None
        try:
            self._recognizer.AcceptWaveform(audio.tobytes())
            result = json.loads(self._recognizer.FinalResult())
            text = result.get("text", "").strip().lower()
            # Проверяем частичный результат
            if not text:
                partial = json.loads(self._recognizer.PartialResult())
                text = partial.get("partial", "").strip().lower()
            return text if text and any(w in text for w in jarvis_config.WAKE_WORDS) else None
        except Exception as e:
            print(f"[Wake] Ошибка распознавания: {e}")
            return None

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
        if self._stream:
            try:
                self._stream.stop()
            except Exception:
                pass
        if self.thread:
            self.thread.join(timeout=1)


from queue import Queue, Empty
