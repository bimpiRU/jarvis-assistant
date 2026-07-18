"""Модуль распознавания и синтеза речи."""

import threading
import collections
import queue
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
from .config import LANGUAGE, SPEECH_RATE, SPEECH_VOLUME, ENERGY_THRESHOLD, PAUSE_THRESHOLD


class Microphone:
    """Замена sr.Microphone на базе sounddevice (не требует PyAudio)."""

    def __init__(self, sample_rate=16000, block_size=1024):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.audio_queue = queue.Queue()

    def _callback(self, indata, frames, time_info, status):
        """Callback для sounddevice: сохраняет блоки аудио."""
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def listen(self, timeout=5, phrase_time_limit=10):
        """Записывает речь с микрофона и возвращает sr.AudioData."""
        print("Слушаю...")

        buffer = collections.deque(maxlen=int(self.sample_rate * phrase_time_limit / self.block_size) + 1)
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
            # Пропускаем первые 0.5 секунд для адаптации к шуму
            adapt_blocks = int(0.5 * self.sample_rate / self.block_size)
            for _ in range(adapt_blocks):
                try:
                    self.audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

            while True:
                try:
                    block = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    if speech_started and silence_duration >= PAUSE_THRESHOLD:
                        break
                    if time.time() - start_time > timeout and not speech_started:
                        raise sr.WaitTimeoutError("Время ожидания речи истекло")
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

        audio_data = np.concatenate(list(buffer), axis=0).tobytes()
        return sr.AudioData(audio_data, self.sample_rate, 2)


class Speech:
    """Отвечает за распознавание речи (STT) и синтез речи (TTS)."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = ENERGY_THRESHOLD
        self.recognizer.pause_threshold = PAUSE_THRESHOLD
        self.recognizer.dynamic_energy_threshold = True
        self.microphone = Microphone()

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", SPEECH_RATE)
        self.engine.setProperty("volume", SPEECH_VOLUME)

        # Попытка выбрать русский голос
        voices = self.engine.getProperty("voices")
        for voice in voices:
            if "russian" in voice.name.lower() or "ru" in voice.id.lower():
                self.engine.setProperty("voice", voice.id)
                break

    def listen(self):
        """Слушает микрофон и возвращает распознанный текст."""
        try:
            audio = self.microphone.listen(timeout=5, phrase_time_limit=10)
            text = self.recognizer.recognize_google(audio, language=LANGUAGE)
            print(f"Распознано: {text}")
            return text.lower()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Ошибка сервиса распознавания: {e}")
            return None

    def speak(self, text):
        """Озвучивает текст в отдельном потоке, чтобы не блокировать UI."""
        if not text:
            return

        def _speak():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except RuntimeError:
                # иногда pyttsx3 падает при повторных вызовах
                pass

        threading.Thread(target=_speak, daemon=True).start()
