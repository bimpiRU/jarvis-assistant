"""Тихое самообучение Джарвиса.

Сохраняет историю команд, нераспознанные фразы и статистику для будущего
дообучения модели. Все аудио-данные шифруются временным ключом.
"""

import json
import os
import time
import threading
from datetime import datetime

import numpy as np

from . import config as jarvis_config
from .audio_crypto import AudioCrypto
from .logger import logger


class SelfLearning:
    """Фоновый сбор данных для улучшения распознавания."""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.join(jarvis_config.BASE_DIR, "self_learning")
        self.commands_file = os.path.join(self.base_dir, "commands.jsonl")
        self.unknown_dir = os.path.join(self.base_dir, "unknown")
        self.stats_file = os.path.join(self.base_dir, "stats.json")
        self.crypto = AudioCrypto()
        self._lock = threading.Lock()

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.unknown_dir, exist_ok=True)

    def log_command(self, text, success=True, response=None, audio_level=None):
        """Сохраняет успешную или неуспешную команду."""
        if not text:
            return
        entry = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "success": success,
            "response": response,
            "audio_level": float(audio_level) if audio_level is not None else None,
        }
        with self._lock:
            with open(self.commands_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._update_stats(text, success)
        logger.debug(f"[SelfLearning] Команда записана: {text[:60]}")

    def log_unknown_audio(self, audio):
        """Сохраняет зашифрованное аудио нераспознанной фразы."""
        if audio is None or len(audio) == 0:
            return
        try:
            enc_path = self.crypto.secure_tempfile(suffix=".wav", dir=self.unknown_dir)
            wav_bytes = self._audio_to_wav_bytes(audio)
            self.crypto.write_encrypted(wav_bytes, enc_path)
            entry = {
                "timestamp": datetime.now().isoformat(),
                "path": enc_path,
                "rms": float(np.sqrt(np.mean(audio.astype(np.float32) ** 2))),
            }
            meta_file = os.path.join(self.unknown_dir, "meta.jsonl")
            with self._lock:
                with open(meta_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.info(f"[SelfLearning] Сохранено нераспознанное аудио: {enc_path}")
        except Exception as e:
            logger.exception(f"[SelfLearning] Ошибка сохранения аудио: {e}")

    def _audio_to_wav_bytes(self, audio):
        """Преобразует numpy array int16 в WAV bytes."""
        import io
        import wave
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(jarvis_config.SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return wav_io.getvalue()

    def _update_stats(self, text, success):
        """Обновляет статистику команд."""
        stats = self.load_stats()
        stats["total"] = stats.get("total", 0) + 1
        if success:
            stats["success"] = stats.get("success", 0) + 1
        else:
            stats["failed"] = stats.get("failed", 0) + 1

        commands = stats.get("commands", {})
        commands[text] = commands.get(text, 0) + 1
        stats["commands"] = commands

        # Топ-5 команд
        stats["top_commands"] = sorted(
            commands.items(), key=lambda x: x[1], reverse=True
        )[:5]

        with self._lock:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)

    def load_stats(self):
        """Загружает статистику."""
        if not os.path.exists(self.stats_file):
            return {"total": 0, "success": 0, "failed": 0, "commands": {}}
        with self._lock:
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"total": 0, "success": 0, "failed": 0, "commands": {}}

    def suggest_threshold_adjustment(self):
        """Анализирует историю и предлагает корректировку порога активации."""
        stats = self.load_stats()
        total = stats.get("total", 0)
        failed = stats.get("failed", 0)
        if total < 10:
            return None

        fail_rate = failed / total
        if fail_rate > 0.5:
            return "порог слишком высокий — снижаю чувствительность"
        if fail_rate < 0.1:
            return "порог низкий — повышаю чувствительность"
        return None

    def get_summary(self):
        """Возвращает краткую сводку для пользователя."""
        stats = self.load_stats()
        total = stats.get("total", 0)
        success = stats.get("success", 0)
        failed = stats.get("failed", 0)
        top = stats.get("top_commands", [])
        unknown_count = len([
            f for f in os.listdir(self.unknown_dir)
            if f.endswith(".enc")
        ]) if os.path.exists(self.unknown_dir) else 0

        lines = [
            f"Всего команд: {total}",
            f"Успешно: {success}",
            f"Не распознано: {failed}",
            f"Нераспознанных аудио сохранено: {unknown_count}",
        ]
        if top:
            lines.append("Топ команд:")
            for cmd, count in top:
                lines.append(f"  — {cmd}: {count}")
        return "\n".join(lines)
