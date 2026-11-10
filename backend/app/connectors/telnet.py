import asyncio

import telnetlib3

from ..config import settings
from .base import Connector, ConnectorError


class TelnetConnector(Connector):
    """Telnet-сессия (telnetlib3).

    Логин и пароль не отправляются автоматически: приглашения у устройств различаются,
    их вводят в самой сессии. Telnet передаёт данные открытым текстом — использовать
    только в изолированных лабораторных сетях.
    """

    protocol = "telnet"
    default_port = 23
    line_ending = "\r\n"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._reader_stream = None
        self._writer = None
        self._task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> None:
        try:
            self._reader_stream, self._writer = await asyncio.wait_for(
                telnetlib3.open_connection(self.host, self.port),
                timeout=settings.connect_timeout,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            raise ConnectorError(
                f"Telnet: не удалось подключиться к {self.host}:{self.port}: {exc}"
            ) from exc
        self._password = None
        self._task = asyncio.create_task(self._pump())

    async def _pump(self) -> None:
        try:
            while True:
                data = await self._reader_stream.read(4096)
                if not data:
                    break
                self.buffer.append(data)
        except OSError:
            pass

    async def send(self, data: str) -> None:
        if not self.connected:
            raise ConnectorError("Telnet: сессия закрыта")
        self._writer.write(data)

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        if self._writer:
            self._writer.close()
            self._writer = None
