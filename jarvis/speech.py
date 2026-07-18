"""Модуль распознавания и синтеза речи."""

import threading
import queue
import time
import wave
import tempfile
import json
import io
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
from vosk import Model, KaldiRecognizer

from . import config as jarvis_config
from .audio_crypto import AudioCrypto


def _apply_gain(audio: np.ndarray, gain_db: float) -> np.ndarray:
    """Применяет цифровое усиление к аудио."""
    if gain_db == 0:
        return audio
    gain = 10 ** (gain_db / 20.0)
    amplified = audio.astype(np.float32) * gain
    return np.clip(amplified, -32768, 32767).astype(np.int16)


def _simple_noise_gate(audio: np.ndarray, threshold: float) -> np.ndarray:
    """Простое шумоподавление: слабые сигналы приглушаются."""
    if not jarvis_config.NOISE_SUPPRESSION:
        return audio
    audio_float = audio.astype(np.float32)
    window = 512
    out = np.zeros_like(audio_float)
    for i in range(0, len(audio_float), window):
        block = audio_float[i : i + window]
        rms = np.sqrt(np.mean(block**2))
        if rms < threshold:
            out[i : i + window] = block * 0.05
        else:
            out[i : i + window] = block
    return np.clip(out, -32768, 32767).astype(np.int16)


def _compute_rms(audio: np.ndarray) -> float:
    """Вычисляет RMS аудио-сигнала."""
    return float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))


class Microphone:
    """Запись с микрофона через sounddevice с усилением, VAD и pre-buffer."""

    def __init__(self, sample_rate=jarvis_config.SAMPLE_RATE, block_size=1024, device=None):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.device = device
        self.audio_queue = queue.Queue()
        self.crypto = AudioCrypto()
        self._last_level = 0.0

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())
        self._last_level = _compute_rms(indata)

    def get_level(self):
        """Возвращает последний уровень звука."""
        return self._last_level

    def record(self, timeout=5, phrase_time_limit=10, stop_event=None):
        """Записывает речь с микрофона и возвращает numpy array int16."""
        print("Слушаю...")

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="int16",
            channels=1,
            callback=self._callback,
            device=self.device,
        )

        with stream:
            # Адаптация к шуму и предварительный буфер
            pre_buffer = []
            noise_floor = jarvis_config.ENERGY_THRESHOLD
            adapt_blocks = int(0.5 * self.sample_rate / self.block_size)

            for _ in range(adapt_blocks):
                try:
                    block = self.audio_queue.get(timeout=0.2)
                    pre_buffer.append(block)
                    energy = _compute_rms(block)
                    noise_floor = 0.9 * noise_floor + 0.1 * energy
                except queue.Empty:
                    continue

            # Динамический порог: базовый + надбавка к шуму
            dynamic_threshold = max(jarvis_config.ENERGY_THRESHOLD * 0.25, noise_floor * 1.5)
            print(f"[Mic] Порог активации: {dynamic_threshold:.1f}, фон: {noise_floor:.1f}")

            # Pre-buffer для захвата начала фразы
            max_pre_buffer = int(0.8 * self.sample_rate / self.block_size)
            pre_buffer = pre_buffer[-max_pre_buffer:]

            buffer = []
            speech_started = False
            silence_duration = 0.0
            start_time = time.time()

            while True:
                if stop_event and stop_event.is_set():
                    return None

                try:
                    block = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    if speech_started and silence_duration >= jarvis_config.PAUSE_THRESHOLD:
                        break
                    if time.time() - start_time > timeout and not speech_started:
                        return None
                    continue

                energy = _compute_rms(block)

                if energy >= dynamic_threshold:
                    if not speech_started:
                        speech_started = True
                        # Добавляем pre-buffer, чтобы не потерять начало
                        buffer.extend(pre_buffer)
                    buffer.append(block)
                    silence_duration = 0.0
                elif speech_started:
                    buffer.append(block)
                    silence_duration += len(block) / self.sample_rate
                    if silence_duration >= jarvis_config.PAUSE_THRESHOLD:
                        break
                else:
                    pre_buffer.append(block)
                    if len(pre_buffer) > max_pre_buffer:
                        pre_buffer.pop(0)

                if time.time() - start_time > phrase_time_limit:
                    break

        if not buffer:
            return None

        audio = np.concatenate(buffer, axis=0)
        # Применяем усиление и шумоподавление
        audio = _apply_gain(audio, jarvis_config.MIC_GAIN_DB)
        audio = _simple_noise_gate(audio, noise_floor * 2)
        return audio

    def record_to_secure_wav(self, timeout=5, phrase_time_limit=10, stop_event=None):
        """Записывает речь и сохраняет в зашифрованный временный WAV-файл."""
        audio = self.record(timeout, phrase_time_limit, stop_event)
        if audio is None:
            return None

        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio.tobytes())
        wav_bytes = wav_io.getvalue()

        enc_path = self.crypto.secure_tempfile(".wav")
        self.crypto.write_encrypted(wav_bytes, enc_path)
        return enc_path, audio

    def read_secure_wav(self, enc_path):
        """Читает зашифрованный WAV и возвращает AudioData."""
        wav_bytes = self.crypto.read_encrypted(enc_path)
        return sr.AudioData(wav_bytes, self.sample_rate, 2)

    def cleanup(self, enc_path):
        """Удаляет зашифрованный временный файл."""
        self.crypto.delete(enc_path)


class Speech:
    """Распознавание речи офлайн (Vosk) + онлайн fallback (Google), TTS через pyttsx3."""

    def __init__(self, device=None):
        self.microphone = Microphone(device=device)
        self.sample_rate = jarvis_config.SAMPLE_RATE
        self.crypto = self.microphone.crypto

        # pyttsx3 с выбором голоса
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", jarvis_config.SPEECH_RATE)
        self.engine.setProperty("volume", jarvis_config.SPEECH_VOLUME)
        self._set_voice()

        # Vosk offline model
        self.vosk_model = None
        if self._model_exists():
            try:
                self.vosk_model = Model(jarvis_config.VOSK_MODEL_PATH)
                print("Vosk модель загружена.")
            except Exception as e:
                print(f"Не удалось загрузить Vosk модель: {e}")
        else:
            print(f"Модель Vosk не найдена: {jarvis_config.VOSK_MODEL_PATH}. Запустите download_model.py")

        # Google recognizer (fallback)
        self.recognizer = sr.Recognizer()

    def _set_voice(self):
        """Выбирает голос: мужской русский > любой мужской > русский > любой."""
        voices = self.engine.getProperty("voices")
        if not voices:
            return

        selected = None
        for voice in voices:
            name = voice.name.lower()
            is_ru = "russian" in name or "ru" in voice.id.lower()
            is_male = any(m in name for m in ["david", "pavel", "male", "artem", "evgeny", "dmitry"])
            if is_ru and is_male:
                selected = voice.id
                print(f"Выбран мужской русский голос: {voice.name}")
                break

        if not selected and jarvis_config.PREFERRED_VOICE_GENDER == "male":
            for voice in voices:
                name = voice.name.lower()
                if any(m in name for m in ["david", "male", "pavel", "artem"]):
                    selected = voice.id
                    print(f"Выбран мужской голос: {voice.name}")
                    break

        if not selected:
            for voice in voices:
                name = voice.name.lower()
                if "russian" in name or "ru" in voice.id.lower():
                    selected = voice.id
                    print(f"Выбран русский голос: {voice.name}")
                    break

        if not selected:
            selected = voices[0].id
            print(f"Выбран голос по умолчанию: {voices[0].name}")

        self.engine.setProperty("voice", selected)

    def _model_exists(self):
        import os
        return os.path.exists(jarvis_config.VOSK_MODEL_PATH)

    def _recognize_vosk(self, audio_array):
        """Распознаёт офлайн через Vosk."""
        if self.vosk_model is None:
            return None
        try:
            recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
            recognizer.AcceptWaveform(audio_array.tobytes())
            result = recognizer.FinalResult()
            text = json.loads(result).get("text", "").strip()
            return text if text else None
        except Exception as e:
            print(f"Ошибка Vosk: {e}")
            return None

    def _recognize_google(self, audio_array):
        """Распознаёт онлайн через Google (fallback)."""
        try:
            audio_data = sr.AudioData(audio_array.tobytes(), self.sample_rate, 2)
            return self.recognizer.recognize_google(audio_data, language=jarvis_config.LANGUAGE).lower()
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

    def get_mic_level(self):
        """Возвращает текущий уровень микрофона."""
        return self.microphone.get_level()

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
