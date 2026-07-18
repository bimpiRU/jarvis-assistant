"""Шифрование временных аудио-файлов для защиты приватности."""

import os
import tempfile
from cryptography.fernet import Fernet


class AudioCrypto:
    """Шифрует и расшифровывает аудио-файлы в памяти."""

    def __init__(self):
        # Генерируем новый ключ при каждом запуске. После закрытия приложения
        # расшифровать старые файлы невозможно — они бесполезны для злоумышленников.
        self.key = Fernet.generate_key()
        self.fernet = Fernet(self.key)

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Шифрует байты аудио."""
        return self.fernet.encrypt(data)

    def decrypt_bytes(self, token: bytes) -> bytes:
        """Расшифровывает байты аудио."""
        return self.fernet.decrypt(token)

    def secure_tempfile(self, suffix=".wav"):
        """Создаёт временный файл для зашифрованного аудио."""
        fd, path = tempfile.mkstemp(suffix=suffix + ".enc")
        os.close(fd)
        return path

    def write_encrypted(self, data: bytes, path: str):
        """Записывает зашифрованные данные во временный файл."""
        with open(path, "wb") as f:
            f.write(self.encrypt_bytes(data))

    def read_encrypted(self, path: str) -> bytes:
        """Читает и расшифровывает данные из временного файла."""
        with open(path, "rb") as f:
            return self.decrypt_bytes(f.read())

    def delete(self, path: str):
        """Безопасно удаляет временный файл."""
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
