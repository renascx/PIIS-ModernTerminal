"""Оценка риска команд сетевого оборудования до их выполнения."""

import re
from dataclasses import dataclass
from enum import Enum


class Risk(str, Enum):
    READ_ONLY = "read_only"  # show/ping/traceroute — безопасно
    CONFIG = "config"  # обычное изменение конфигурации
    DANGEROUS = "dangerous"  # всегда требует явного подтверждения


@dataclass(frozen=True)
class Assessment:
    command: str
    risk: Risk
    reason: str

    @property
    def needs_confirmation(self) -> bool:
        return self.risk is not Risk.READ_ONLY


# Шаблоны опасных команд (Cisco IOS-подобный синтаксис, регистр не важен).
_DANGEROUS = [
    (r"^reload\b", "перезагрузка устройства"),
    (r"^(write\s+erase|erase\b)", "стирание конфигурации/памяти"),
    (r"^format\b", "форматирование файловой системы"),
    (r"^delete\b", "удаление файлов"),
    (r"^(no\s+)?shutdown\b", "изменение состояния интерфейса"),
    (r"^no\s+vlan\b", "удаление VLAN"),
    (r"^no\s+ip\s+address\b", "удаление IP-адреса"),
    (r"^default\s+interface\b", "сброс интерфейса к настройкам по умолчанию"),
    (r"^copy\s+\S+\s+(startup-config|running-config)\b", "перезапись конфигурации"),
    (r"^(enable\s+secret|username)\b.*\b(password|secret)\b", "изменение учётных данных"),
]

_READ_ONLY = re.compile(r"^(show|ping|traceroute|tracert|display|\?)\b", re.IGNORECASE)


def assess(command: str) -> Assessment:
    """Классифицирует одну команду."""
    cmd = " ".join(command.strip().split())
    if not cmd:
        return Assessment(command, Risk.CONFIG, "пустая команда")
    # Несколько команд в одной строке — не пропускаем как read-only.
    if re.search(r"[;&|\n`$]", command):
        return Assessment(command, Risk.DANGEROUS, "составная команда или управляющие символы")
    for pattern, reason in _DANGEROUS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return Assessment(command, Risk.DANGEROUS, reason)
    if _READ_ONLY.search(cmd):
        return Assessment(command, Risk.READ_ONLY, "команда только читает состояние")
    return Assessment(command, Risk.CONFIG, "изменение конфигурации")


def assess_many(commands: list[str]) -> list[Assessment]:
    return [assess(c) for c in commands]
