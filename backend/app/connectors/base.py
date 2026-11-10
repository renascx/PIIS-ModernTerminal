from abc import ABC, abstractmethod

from ..config import settings
from .buffer import OutputBuffer


class ConnectorError(Exception):
    """Ошибка подключения или передачи данных."""


class Connector(ABC):
    """Интерактивное подключение к сетевому устройству."""

    protocol: str = ""
    default_port: int = 0
    line_ending: str = "\n"

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self._password = password  # хранится только до подключения
        self.buffer = OutputBuffer(settings.output_buffer_chars)

    @property
    @abstractmethod
    def connected(self) -> bool: ...

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def send(self, data: str) -> None:
        """Отправляет сырые данные в сессию."""

    @abstractmethod
    async def close(self) -> None: ...

    async def send_line(self, command: str) -> None:
        await self.send(command + self.line_ending)
