import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .connectors.base import Connector
from .connectors.ssh import SSHConnector
from .connectors.telnet import TelnetConnector


@dataclass
class Session:
    id: str
    connector: Connector
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def info(self) -> dict[str, object]:
        c = self.connector
        return {
            "id": self.id,
            "protocol": c.protocol,
            "host": c.host,
            "port": c.port,
            "username": c.username,
            "connected": c.connected,
            "created_at": self.created_at.isoformat(),
        }


class SessionRegistry:
    """Связывает идентификатор сессии (вкладки терминала) с живым коннектором."""

    def __init__(self) -> None:
        # Фабрики подменяются в тестах.
        self.factories: dict[str, type[Connector]] = {
            "ssh": SSHConnector,
            "telnet": TelnetConnector,
        }
        self._sessions: dict[str, Session] = {}

    async def create(
        self,
        protocol: str,
        host: str,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> Session:
        factory = self.factories.get(protocol)
        if factory is None:
            raise ValueError(f"Неизвестный протокол: {protocol}")
        connector = factory(host, port or factory.default_port, username, password)
        await connector.connect()
        session = Session(id=uuid.uuid4().hex, connector=connector)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def list(self) -> list[Session]:
        return list(self._sessions.values())

    async def close(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        await session.connector.close()
        return True

    async def close_all(self) -> None:
        for session_id in list(self._sessions):
            await self.close(session_id)


registry = SessionRegistry()
