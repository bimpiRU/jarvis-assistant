"""Диагностика микрофона и аудио-устройств."""

import sounddevice as sd
import numpy as np
import time


def list_microphones():
    """Возвращает список доступных микрофонов."""
    devices = sd.query_devices()
    mics = []
    for i, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0:
            mics.append({
                "index": i,
                "name": dev.get("name", "Unknown"),
                "channels": dev.get("max_input_channels"),
                "sample_rate": dev.get("default_samplerate"),
            })
    return mics


def get_default_microphone():
    """Возвращает индекс микрофона по умолчанию."""
    try:
        return sd.default.device[0]
    except Exception:
        return None


def test_microphone(duration=3, device=None):
    """Записывает N секунд с микрофона и возвращает статистику уровня звука."""
    sample_rate = 16000
    block_size = 1024
    audio_queue = []

    def callback(indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        audio_queue.append(indata.copy())

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
        return {"error": str(e)}

    if not audio_queue:
        return {"error": "Нет аудио-данных"}

    audio = np.concatenate(audio_queue, axis=0)
    audio_float = audio.astype(np.float32)

    rms = np.sqrt(np.mean(audio_float ** 2))
    peak = np.max(np.abs(audio_float))
    db = 20 * np.log10(rms + 1e-10)

    return {
        "duration": duration,
        "samples": len(audio),
        "rms": float(rms),
        "peak": float(peak),
        "db": float(db),
        "status": "хороший" if rms > 500 else "слабый" if rms > 100 else "очень слабый или тишина",
    }


def print_diagnostics():
    """Печатает полную диагностику микрофонов."""
    print("=== Диагностика микрофона ===")
    mics = list_microphones()
    if not mics:
        print("Микрофоны не найдены!")
        return

    print("Доступные микрофоны:")
    for mic in mics:
        marker = " [ПО УМОЛЧАНИЮ]" if mic["index"] == get_default_microphone() else ""
        print(f"  {mic['index']}: {mic['name']} | {mic['channels']} ch | {mic['sample_rate']} Hz{marker}")

    default = get_default_microphone()
    if default is not None:
        print(f"\nТестируем микрофон по умолчанию ({default})...")
        result = test_microphone(duration=3, device=default)
        if "error" in result:
            print(f"Ошибка: {result['error']}")
        else:
            print(f"  RMS: {result['rms']:.1f}")
            print(f"  Peak: {result['peak']:.1f}")
            print(f"  Уровень: {result['db']:.1f} dB")
            print(f"  Статус: {result['status']}")


if __name__ == "__main__":
    print_diagnostics()
