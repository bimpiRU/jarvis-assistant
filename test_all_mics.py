#!/usr/bin/env python3
"""Тест всех доступных аудиоустройств ввода."""

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


def get_input_devices():
    """Возвращает все устройства ввода."""
    devices = sd.query_devices()
    default = sd.default.device[0]
    inputs = []
    for i, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0:
            inputs.append({
                "index": i,
                "name": dev.get("name", "Unknown"),
                "channels": dev.get("max_input_channels"),
                "sample_rate": dev.get("default_samplerate"),
                "is_default": i == default,
            })
    return inputs


def test_device(device_info, duration=3):
    """Тестирует одно устройство."""
    idx = device_info["index"]
    name = device_info["name"]
    print(f"\n--- Тест устройства {idx}: {name} ---")

    sample_rate = SAMPLE_RATE
    block_size = 1024
    buffer = []
    error = None

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
            device=idx,
        ):
            time.sleep(duration)
    except Exception as e:
        error = str(e)
        print(f"  ❌ ОШИБКА: {error}")
        return None

    if not buffer:
        print("  ❌ Нет аудио-данных")
        return None

    audio = np.concatenate(buffer, axis=0)
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    peak = float(np.max(np.abs(audio)))

    print(f"  ✓ Запись OK")
    print(f"  RMS: {rms:.1f}")
    print(f"  Peak: {peak:.1f}")
    print(f"  Уровень: {'хороший' if rms > 300 else 'слабый' if rms > 50 else 'очень слабый / тишина'}")

    return {
        "device": device_info,
        "rms": rms,
        "peak": peak,
        "audio": audio,
    }


def recognize_with_device(audio):
    """Пробует распознать аудио через Vosk."""
    if not os.path.exists(VOSK_MODEL_PATH):
        return "модель не найдена"

    try:
        model = Model(VOSK_MODEL_PATH)
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)
        recognizer.AcceptWaveform(audio.tobytes())
        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip() or "(тишина)"
    except Exception as e:
        return f"ошибка: {e}"


def save_test_wav(audio, filename):
    """Сохраняет тестовый WAV."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())


def main():
    print("=== Тест всех аудиоустройств ввода ===")
    print("Говорите что-то во время теста, чтобы устройство поймало звук.\n")

    devices = get_input_devices()
    if not devices:
        print("Устройства ввода не найдены!")
        return

    results = []
    for dev in devices:
        result = test_device(dev, duration=3)
        if result:
            results.append(result)
        print()

    print("\n=== Итоги ===")
    if not results:
        print("Ни одно устройство не заработало.")
        return

    # Сортируем по RMS
    results.sort(key=lambda x: x["rms"], reverse=True)

    for i, r in enumerate(results, 1):
        dev = r["device"]
        marker = " [РЕКОМЕНДУЕТСЯ]" if i == 1 else ""
        print(f"{i}. Устройство {dev['index']}: {dev['name']}")
        print(f"   RMS: {r['rms']:.1f}, Peak: {r['peak']:.1f}{marker}")

    best = results[0]
    best_dev = best["device"]
    print(f"\nЛучшее устройство: {best_dev['index']} — {best_dev['name']}")
    print(f"Запускайте с ним: python main.py --device {best_dev['index']}")

    # Сохраняем лучшую запись
    save_test_wav(best["audio"], "best_mic_test.wav")
    print("Лучшая запись сохранена как best_mic_test.wav")

    # Пробуем распознать лучшую запись
    print(f"\nРаспознавание лучшей записи: '{recognize_with_device(best['audio'])}'")


if __name__ == "__main__":
    main()
