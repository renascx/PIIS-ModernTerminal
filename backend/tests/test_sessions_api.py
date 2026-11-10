import pytest
from fastapi.testclient import TestClient

from app.config import ai_settings
from app.connectors.base import Connector, ConnectorError
from app.main import app
from app.session_registry import registry


class FakeConnector(Connector):
    protocol = "ssh"
    default_port = 22
    sent: list[str] = []

    def __init__(self, host, port, username=None, password=None):
        super().__init__(host, port, username, password)
        self._connected = False

    @property
    def connected(self):
        return self._connected

    async def connect(self):
        if self.host == "bad":
            raise ConnectorError("unreachable")
        self._connected = True
        self.buffer.append("Switch#")

    async def send(self, data):
        FakeConnector.sent.append(data)

    async def close(self):
        self._connected = False


@pytest.fixture
def client():
    registry.factories = {"ssh": FakeConnector, "telnet": FakeConnector}
    registry._sessions.clear()
    FakeConnector.sent = []
    ai_settings.approval_mode = "confirm"
    with TestClient(app) as c:
        yield c


def _create(client, host="sw1"):
    resp = client.post("/api/sessions", json={"protocol": "ssh", "host": host})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_list_output_close(client):
    sid = _create(client)
    assert client.get("/api/sessions").json()[0]["port"] == 22
    assert client.get(f"/api/sessions/{sid}/output").json()["output"] == "Switch#"
    assert client.delete(f"/api/sessions/{sid}").status_code == 204
    assert client.get(f"/api/sessions/{sid}/output").status_code == 404


def test_connect_error_is_502(client):
    resp = client.post("/api/sessions", json={"protocol": "ssh", "host": "bad"})
    assert resp.status_code == 502


def test_invalid_protocol_rejected(client):
    assert client.post("/api/sessions", json={"protocol": "ftp", "host": "x"}).status_code == 422


def test_command_requires_confirmation(client):
    sid = _create(client)
    resp = client.post(f"/api/sessions/{sid}/commands", json={"command": "vlan 20"})
    assert resp.status_code == 409
    assert FakeConnector.sent == []
    resp = client.post(
        f"/api/sessions/{sid}/commands", json={"command": "vlan 20", "confirmed": True}
    )
    assert resp.status_code == 200
    assert FakeConnector.sent == ["vlan 20\n"]


def test_readonly_auto_mode_skips_confirmation_for_show(client):
    sid = _create(client)
    ai_settings.approval_mode = "readonly_auto"
    ok = client.post(f"/api/sessions/{sid}/commands", json={"command": "show vlan brief"})
    assert ok.status_code == 200
    blocked = client.post(f"/api/sessions/{sid}/commands", json={"command": "reload"})
    assert blocked.status_code == 409
