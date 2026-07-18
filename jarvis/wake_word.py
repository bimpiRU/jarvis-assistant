"""Wake-word детектор для активации Джарвиса голосом."""

import threading
import time
import json
import numpy as np
import sounddevice as sd
from vosk import KaldiRecognizer

from . import config as jarvis_config
from .logger import logger


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
        self._last_audio_level = 0.0
        self.device = speech.microphone.device

        self._recognizer = None
        if self.speech.vosk_model:
            try:
                # Используем recognizer без grammar — small-ru модель лучше распознаёт
                # короткие слова в полном словаре, чем в жёстком grammar
                self._recognizer = KaldiRecognizer(self.speech.vosk_model, self.sample_rate)
                logger.info("Wake word recognizer создан (без grammar)")
            except Exception as e:
                logger.error(f"Ошибка создания wake word recognizer: {e}")

    def get_audio_level(self):
        """Возвращает последний уровень звука (RMS)."""
        return self._last_audio_level

    def _rms(self, block):
        arr = np.frombuffer(block, dtype=np.int16) if not isinstance(block, np.ndarray) else block
        return float(np.sqrt(np.mean(arr.astype(np.float32) ** 2)))

    def _listen_loop(self):
        """Цикл прослушивания через blocking read."""
        logger.info("[Wake] Запуск цикла прослушивания")

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                dtype="int16",
                channels=1,
                device=self.device,
            ) as stream:
                logger.info(f"[Wake] Поток открыт, устройство={self.device}")

                # Адаптация к шуму
                noise_floor = jarvis_config.ENERGY_THRESHOLD
                adapt_blocks = int(0.5 * self.sample_rate / self.block_size)
                for _ in range(adapt_blocks):
                    if self.stop_event.is_set():
                        return
                    block, _ = stream.read(self.block_size)
                    noise_floor = 0.9 * noise_floor + 0.1 * self._rms(block)

                dynamic_threshold = max(jarvis_config.ENERGY_THRESHOLD * 0.25, noise_floor * 1.5)
                logger.info(f"[Wake] Порог активации: {dynamic_threshold:.1f}, фон: {noise_floor:.1f}")

                while self.listening and not self.stop_event.is_set():
                    block, _ = stream.read(self.block_size)
                    self._last_audio_level = self._rms(block)

                    if self._last_audio_level < dynamic_threshold:
                        continue

                    # Началась речь — собираем фразу
                    logger.debug(f"[Wake] Звук превысил порог: {self._last_audio_level:.1f}")
                    phrase_blocks = [block]
                    silence = 0.0
                    start_time = time.time()

                    while silence < jarvis_config.PAUSE_THRESHOLD and time.time() - start_time < 3:
                        if self.stop_event.is_set():
                            return
                        block, _ = stream.read(self.block_size)
                        phrase_blocks.append(block)
                        self._last_audio_level = self._rms(block)
                        if self._last_audio_level < dynamic_threshold:
                            silence += len(block) / self.sample_rate
                        else:
                            silence = 0

                    arrays = [np.frombuffer(b, dtype=np.int16) if not isinstance(b, np.ndarray) else b for b in phrase_blocks]
                    audio = np.concatenate(arrays, axis=0)
                    text = self._recognize_wake(audio)
                    if text:
                        logger.info(f"[Wake] Распознано: {text}")
                        if self.on_wake:
                            self.on_wake()
                    else:
                        logger.debug("[Wake] Wake word не распознано")

        except Exception as e:
            logger.exception(f"[Wake] Ошибка в цикле прослушивания: {e}")
        finally:
            logger.info("[Wake] Цикл прослушивания завершён")

    def _recognize_wake(self, audio):
        """Распознаёт только wake words."""
        if self._recognizer is None:
            return None
        try:
            # Создаём свежий recognizer для каждой попытки, чтобы избежать
            # накопления состояния от предыдущих шумов.
            recognizer = KaldiRecognizer(self.speech.vosk_model, self.sample_rate)
            recognizer.AcceptWaveform(audio.tobytes())
            result = json.loads(recognizer.FinalResult())
            text = result.get("text", "").strip().lower()
            logger.debug(f"[Wake] Результат Vosk: '{text}'")
            if text and any(w in text for w in jarvis_config.WAKE_WORDS):
                return text
            return None
        except Exception as e:
            logger.exception(f"[Wake] Ошибка распознавания: {e}")
            return None

    def start(self):
        """Запускает фоновое прослушивание."""
        if self.listening:
            return
        self.listening = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        logger.info("[Wake] Старт wake word detector")

    def stop(self):
        """Останавливает прослушивание."""
        self.listening = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)
        logger.info("[Wake] Стоп wake word detector")
