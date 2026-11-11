import pytest

from app.ai.agent import agent
from app.audit import audit_log
from app.config import ai_settings, settings
from app.session_registry import registry

from .fakes import FakeConnector


@pytest.fixture(autouse=True)
def clean_state(monkeypatch, tmp_path):
    monkeypatch.setattr(audit_log, "path", str(tmp_path / "audit.db"))
    monkeypatch.setattr(settings, "command_wait", 0)
    monkeypatch.setattr(ai_settings, "approval_mode", "confirm")
    monkeypatch.setattr(registry, "factories", {"ssh": FakeConnector, "telnet": FakeConnector})
    registry._sessions.clear()
    agent.history.clear()
    agent.pending.clear()
    FakeConnector.sent = []
    yield
