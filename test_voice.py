#!/usr/bin/env python3
"""Детальный тест микрофона и распознавания речи."""

import os
import sys
import time
import wave
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jarvis.config import SAMPLE_RATE, VOSK_MODEL_PATH


def list_mics():
    print("=== Доступные микрофоны ===")
    devices = sd.query_devices()
    default = sd.default.device[0]
    mics = []
    for i, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0:
            marker = " [ПО УМОЛЧАНИЮ]" if i == default else ""
            print(f"  {i}: {dev['name']} | {dev['max_input_channels']} ch | {dev['default_samplerate']} Hz{marker}")
            mics.append(i)
    return mics


def record_and_save(device=None, duration=5, output="test_recording.wav"):
    print(f"\n=== Запись {duration} секунд с устройства {device or 'по умолчанию'} ===")
    print("Начинайте говорить прямо сейчас...")

    sample_rate = SAMPLE_RATE
    block_size = 1024
    buffer = []

    def callback(indata, frames, time_info, status):
        if status:
            print(f"  [status] {status}")
        buffer.append(indata.copy())

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            blocksize=block_size,
            dtype="int16",
            channels=1,
            callback=callback,
            device=device,
        ):
            time.sleep(duration)
    except Exception as e:
        print(f"ОШИБКА при открытии микрофона: {e}")
        return None

    if not buffer:
        print("ОШИБКА: аудио-буфер пуст!")
        return None

    audio = np.concatenate(buffer, axis=0)
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    peak = float(np.max(np.abs(audio)))

    with wave.open(output, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

    print(f"  Сохранено: {output}")
    print(f"  RMS: {rms:.1f}")
    print(f"  Peak: {peak:.1f}")
    print(f"  Статус: {'есть звук' if rms > 100 else 'почти тишина'}")
    return audio


def recognize_vosk(audio):
    print("\n=== Распознавание через Vosk ===")
    if not os.path.exists(VOSK_MODEL_PATH):
        print(f"ОШИБКА: модель не найдена: {VOSK_MODEL_PATH}")
        print("Запустите: python download_model.py")
        return

    try:
        model = Model(VOSK_MODEL_PATH)
    except Exception as e:
        print(f"ОШИБКА загрузки модели: {e}")
        return

    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    recognizer.AcceptWaveform(audio.tobytes())
    result = json.loads(recognizer.FinalResult())
    text = result.get("text", "").strip()
    print(f"Распознано: '{text}'")

    partial = json.loads(recognizer.PartialResult())
    print(f"Partial: '{partial.get('partial', '')}'")


def test_wake_word(audio):
    print("\n=== Тест wake word ===")
    if not os.path.exists(VOSK_MODEL_PATH):
        return

    from jarvis.config import WAKE_WORDS
    model = Model(VOSK_MODEL_PATH)
    grammar = json.dumps(WAKE_WORDS + ["[unk]"])
    recognizer = KaldiRecognizer(model, SAMPLE_RATE, grammar)
    recognizer.AcceptWaveform(audio.tobytes())
    result = json.loads(recognizer.FinalResult())
    text = result.get("text", "").strip()
    print(f"Wake word распознано: '{text}'")


def main():
    mics = list_mics()
    if not mics:
        print("Микрофоны не найдены!")
        return

    device = input("\nВведите индекс микрофона (Enter — по умолчанию): ").strip()
    device = int(device) if device else None

    audio = record_and_save(device=device)
    if audio is not None:
        recognize_vosk(audio)
        test_wake_word(audio)

    print("\nГотово. Проверьте файл test_recording.wav в папке проекта.")


if __name__ == "__main__":
    main()
