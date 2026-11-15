import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.connectors.buffer import OutputBuffer
from app.main import app

from .fakes import FakeConnector


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sid(client):
    return client.post("/api/sessions", json={"protocol": "ssh", "host": "sw1"}).json()["id"]


def test_terminal_passes_input_and_output(client, sid):
    with client.websocket_connect(f"/api/sessions/{sid}/terminal") as ws:
        ws.send_text("show vlan\n")
        assert ws.receive_text() == "show vlan -> ok\n"
    assert FakeConnector.sent == ["show vlan\n"]


def test_terminal_sends_history_first(client, sid):
    import app.session_registry as reg

    reg.registry.get(sid).connector.buffer.append("Switch#")
    with client.websocket_connect(f"/api/sessions/{sid}/terminal") as ws:
        assert ws.receive_text() == "Switch#"


def test_terminal_removes_listener_on_disconnect(client, sid):
    import app.session_registry as reg

    buffer = reg.registry.get(sid).connector.buffer
    with client.websocket_connect(f"/api/sessions/{sid}/terminal") as ws:
        ws.send_text("x\n")
        ws.receive_text()
        assert len(buffer.listeners) == 1
    client.get("/api/health")
    assert buffer.listeners == []


def test_terminal_unknown_session_is_closed(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/sessions/nope/terminal"):
            pass


def test_buffer_listeners_get_clean_text():
    buf = OutputBuffer()
    got = []
    buf.listeners.append(got.append)
    buf.append("\x1b[1mhi\x1b[0m\r\n")
    buf.append("")
    assert got == ["hi\n"]
