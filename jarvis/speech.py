"""Модуль распознавания и синтеза речи."""

import threading
import queue
import time
import wave
import tempfile
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
from vosk import Model, KaldiRecognizer

from .config import (
    LANGUAGE,
    SPEECH_RATE,
    SPEECH_VOLUME,
    ENERGY_THRESHOLD,
    PAUSE_THRESHOLD,
    SAMPLE_RATE,
    VOSK_MODEL_PATH,
)


class Microphone:
    """Запись с микрофона через sounddevice (не требует PyAudio)."""

    def __init__(self, sample_rate=SAMPLE_RATE, block_size=1024):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.audio_queue = queue.Queue()

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def record(self, timeout=5, phrase_time_limit=10, stop_event=None):
        """Записывает речь с микрофона и возвращает numpy array int16."""
        print("Слушаю...")

        buffer = []
        speech_started = False
        silence_duration = 0.0
        start_time = time.time()

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )

        with stream:
            # Пропускаем первые 0.3 секунды для адаптации к шуму
            adapt_blocks = int(0.3 * self.sample_rate / self.block_size)
            for _ in range(adapt_blocks):
                try:
                    self.audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

            while True:
                if stop_event and stop_event.is_set():
                    return None

                try:
                    block = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    if speech_started and silence_duration >= PAUSE_THRESHOLD:
                        break
                    if time.time() - start_time > timeout and not speech_started:
                        return None
                    continue

                buffer.append(block)
                energy = np.sqrt(np.mean(block.astype(np.float32) ** 2))

                if energy >= ENERGY_THRESHOLD:
                    speech_started = True
                    silence_duration = 0.0
                elif speech_started:
                    silence_duration += len(block) / self.sample_rate
                    if silence_duration >= PAUSE_THRESHOLD:
                        break

                if time.time() - start_time > phrase_time_limit:
                    break

        if not buffer:
            return None
        return np.concatenate(buffer, axis=0)

    def record_to_wav(self, timeout=5, phrase_time_limit=10, stop_event=None):
        """Записывает речь и возвращает путь к WAV-файлу."""
        audio = self.record(timeout, phrase_time_limit, stop_event)
        if audio is None:
            return None

        fd, path = tempfile.mkstemp(suffix=".wav")
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio.tobytes())
        return path


class Speech:
    """Распознавание речи офлайн (Vosk) + онлайн fallback (Google), TTS через pyttsx3."""

    def __init__(self):
        self.microphone = Microphone()
        self.sample_rate = SAMPLE_RATE

        # pyttsx3
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", SPEECH_RATE)
        self.engine.setProperty("volume", SPEECH_VOLUME)
        voices = self.engine.getProperty("voices")
        for voice in voices:
            if "russian" in voice.name.lower() or "ru" in voice.id.lower():
                self.engine.setProperty("voice", voice.id)
                break

        # Vosk offline model
        self.vosk_model = None
        if self._model_exists():
            try:
                self.vosk_model = Model(VOSK_MODEL_PATH)
                print("Vosk модель загружена.")
            except Exception as e:
                print(f"Не удалось загрузить Vosk модель: {e}")
        else:
            print(f"Модель Vosk не найдена: {VOSK_MODEL_PATH}. Запустите download_model.py")

        # Google recognizer (fallback)
        self.recognizer = sr.Recognizer()

    def _model_exists(self):
        import os
        return os.path.exists(VOSK_MODEL_PATH)

    def _recognize_vosk(self, audio_array):
        """Распознаёт офлайн через Vosk."""
        if self.vosk_model is None:
            return None
        try:
            recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
            recognizer.AcceptWaveform(audio_array.tobytes())
            result = recognizer.FinalResult()
            import json
            text = json.loads(result).get("text", "").strip()
            return text if text else None
        except Exception as e:
            print(f"Ошибка Vosk: {e}")
            return None

    def _recognize_google(self, audio_array):
        """Распознаёт онлайн через Google (fallback)."""
        try:
            audio_data = sr.AudioData(audio_array.tobytes(), self.sample_rate, 2)
            return self.recognizer.recognize_google(audio_data, language=LANGUAGE).lower()
        except Exception as e:
            print(f"Ошибка Google Speech: {e}")
            return None

    def listen(self, use_online_fallback=True, stop_event=None):
        """Слушает микрофон и возвращает распознанный текст."""
        audio = self.microphone.record(stop_event=stop_event)
        if audio is None:
            return None

        text = self._recognize_vosk(audio)
        if text:
            print(f"[Vosk] Распознано: {text}")
            return text.lower()

        if use_online_fallback:
            print("Vosk не распознал, пробую Google...")
            text = self._recognize_google(audio)
            if text:
                print(f"[Google] Распознано: {text}")
                return text.lower()

        return None

    def listen_for_wake(self, stop_event=None):
        """Короткое прослушивание для поиска wake word."""
        return self.listen(use_online_fallback=False, stop_event=stop_event)

    def speak(self, text):
        """Озвучивает текст в отдельном потоке."""
        if not text:
            return

        def _speak():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except RuntimeError:
                pass

        threading.Thread(target=_speak, daemon=True).start()
