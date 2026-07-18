"""Опасные действия, требующие подтверждения."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class DangerousAction:
    """Представляет действие, которое требует подтверждения пользователя."""

    title: str
    description: str
    callback: Callable[[], str]

    def execute(self):
        """Выполняет действие и возвращает результат."""
        return self.callback()
