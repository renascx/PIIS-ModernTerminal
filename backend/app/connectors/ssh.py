import asyncio

import asyncssh

from ..config import settings
from .base import Connector, ConnectorError


class SSHConnector(Connector):
    """SSH-сессия с интерактивной оболочкой (asyncssh).

    Отпечаток ключа сервера запоминается при первом подключении (trust on first use)
    и сверяется при следующих. Ограничение: сверка выполняется после аутентификации,
    поэтому при первом подключении защиты от MITM нет.
    """

    protocol = "ssh"
    default_port = 22
    line_ending = "\n"

    _pinned: dict[str, str] = {}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._conn: asyncssh.SSHClientConnection | None = None
        self._proc: asyncssh.SSHClientProcess | None = None
        self._reader: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self._proc is not None and not self._proc.is_closing()

    async def connect(self) -> None:
        try:
            self._conn = await asyncssh.connect(
                self.host,
                self.port,
                username=self.username,
                password=self._password,
                known_hosts=None,
                connect_timeout=settings.connect_timeout,
            )
            self._password = None
            self._check_host_key()
            self._proc = await self._conn.create_process(term_type="vt100", encoding="utf-8")
        except (OSError, asyncssh.Error, asyncio.TimeoutError) as exc:
            await self.close()
            raise ConnectorError(f"SSH: не удалось подключиться к {self.host}:{self.port}: {exc}") from exc
        self._reader = asyncio.create_task(self._pump())

    def _check_host_key(self) -> None:
        assert self._conn is not None
        fingerprint = self._conn.get_server_host_key().get_fingerprint()
        known = self._pinned.setdefault(f"{self.host}:{self.port}", fingerprint)
        if known != fingerprint:
            raise ConnectorError("SSH: ключ сервера изменился, подключение отклонено")

    async def _pump(self) -> None:
        assert self._proc is not None
        try:
            while True:
                data = await self._proc.stdout.read(4096)
                if not data:
                    break
                self.buffer.append(data)
        except (asyncssh.Error, OSError):
            pass

    async def send(self, data: str) -> None:
        if not self.connected:
            raise ConnectorError("SSH: сессия закрыта")
        self._proc.stdin.write(data)

    async def close(self) -> None:
        if self._reader:
            self._reader.cancel()
            self._reader = None
        if self._conn:
            self._conn.close()
            self._conn = None
        self._proc = None
