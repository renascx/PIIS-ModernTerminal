import sqlite3
import threading
from datetime import datetime, timezone

from .config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    session_id TEXT NOT NULL,
    command TEXT NOT NULL,
    risk TEXT NOT NULL,
    decision TEXT NOT NULL,
    source TEXT NOT NULL
)
"""


class AuditLog:
    """Журнал команд: что выполнили, что отклонили и кто это запустил."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute(_SCHEMA)
        return conn

    def add(self, session_id: str, command: str, risk: str, decision: str, source: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO audit (time, session_id, command, risk, decision, source)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (now, session_id, command, risk, decision, source),
                )
                conn.commit()
            finally:
                conn.close()

    def list(self, limit: int = 100) -> list[dict[str, object]]:
        with self._lock:
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            finally:
                conn.close()
        return [dict(r) for r in rows]


audit_log = AuditLog(settings.audit_db)
