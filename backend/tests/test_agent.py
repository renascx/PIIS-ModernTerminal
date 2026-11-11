import pytest
from fastapi.testclient import TestClient

from app.ai.agent import agent, get_command
from app.config import ai_settings, settings
from app.main import app

from .fakes import FakeConnector, FakeProvider, call, say


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sid(client):
    return client.post("/api/sessions", json={"protocol": "ssh", "host": "sw1"}).json()["id"]


def use_provider(replies):
    provider = FakeProvider(replies)
    agent.provider_factory = lambda: provider
    return provider


def test_plain_answer_without_commands(client, sid):
    use_provider([say("Всё работает")])
    resp = client.post(f"/api/sessions/{sid}/assistant", json={"message": "как дела?"})
    assert resp.json() == {"text": "Всё работает", "pending": []}
    assert FakeConnector.sent == []


def test_show_runs_automatically_in_readonly_auto_mode(client, sid):
    ai_settings.approval_mode = "readonly_auto"
    provider = use_provider([call("show vlan brief"), say("VLAN 1 есть")])
    resp = client.post(f"/api/sessions/{sid}/assistant", json={"message": "покажи vlan"})
    assert resp.json()["text"] == "VLAN 1 есть"
    assert FakeConnector.sent == ["show vlan brief\n"]
    assert "show vlan brief -> ok" in provider.calls[1][-1]
    log = client.get("/api/audit").json()
    assert log[0]["decision"] == "auto" and log[0]["source"] == "assistant"


def test_config_command_waits_for_approval(client, sid):
    use_provider([call("vlan 20"), say("VLAN 20 создан")])
    resp = client.post(f"/api/sessions/{sid}/assistant", json={"message": "создай vlan 20"}).json()
    assert [p["command"] for p in resp["pending"]] == ["vlan 20"]
    assert FakeConnector.sent == []
    assert len(client.get(f"/api/sessions/{sid}/pending").json()) == 1

    done = client.post(f"/api/pending/{resp['pending'][0]['id']}/approve").json()
    assert done == {"text": "VLAN 20 создан", "pending": []}
    assert FakeConnector.sent == ["vlan 20\n"]
    assert client.get("/api/audit").json()[0]["decision"] == "approved"


def test_denied_command_is_not_sent(client, sid):
    provider = use_provider([call("reload"), say("Хорошо, не буду")])
    resp = client.post(f"/api/sessions/{sid}/assistant", json={"message": "перезагрузи"}).json()
    assert resp["pending"][0]["risk"] == "dangerous"
    done = client.post(f"/api/pending/{resp['pending'][0]['id']}/deny").json()
    assert done["text"] == "Хорошо, не буду"
    assert FakeConnector.sent == []
    assert "отклонил" in provider.calls[1][-1]
    assert client.get("/api/audit").json()[0]["decision"] == "denied"


def test_dangerous_command_waits_even_in_readonly_auto_mode(client, sid):
    ai_settings.approval_mode = "readonly_auto"
    use_provider([call("write erase")])
    resp = client.post(f"/api/sessions/{sid}/assistant", json={"message": "очисти"}).json()
    assert len(resp["pending"]) == 1
    assert FakeConnector.sent == []


def test_chat_blocked_while_commands_pending(client, sid):
    use_provider([call("vlan 30")])
    client.post(f"/api/sessions/{sid}/assistant", json={"message": "vlan 30"})
    resp = client.post(f"/api/sessions/{sid}/assistant", json={"message": "ещё"})
    assert resp.status_code == 409


def test_unknown_pending_and_session(client):
    assert client.post("/api/pending/nope/approve").status_code == 404
    assert client.post("/api/sessions/nope/assistant", json={"message": "hi"}).status_code == 404


def test_step_limit(client, sid, monkeypatch):
    ai_settings.approval_mode = "readonly_auto"
    monkeypatch.setattr(settings, "agent_max_steps", 3)
    use_provider([call("show clock")] * 5)
    resp = client.post(f"/api/sessions/{sid}/assistant", json={"message": "время"}).json()
    assert "лимит" in resp["text"]
    assert len(FakeConnector.sent) == 3


def test_broken_tool_call_gets_error_message(client, sid):
    bad = call("x")
    bad.tool_calls[0]["function"]["arguments"] = {}
    provider = use_provider([bad, say("понял")])
    resp = client.post(f"/api/sessions/{sid}/assistant", json={"message": "сделай что-нибудь"})
    assert resp.json()["text"] == "понял"
    assert "команда не указана" in provider.calls[1][-1]


def test_closing_session_clears_pending(client, sid):
    use_provider([call("vlan 40")])
    client.post(f"/api/sessions/{sid}/assistant", json={"message": "vlan 40"})
    client.delete(f"/api/sessions/{sid}")
    assert agent.pending == {}
    assert sid not in agent.history


@pytest.mark.parametrize(
    "arguments, expected",
    [
        ({"command": " show vlan "}, "show vlan"),
        ('{"command": "vlan 20"}', "vlan 20"),
        ("не json", None),
        ({"command": ""}, None),
        ({}, None),
    ],
)
def test_get_command(arguments, expected):
    assert get_command({"function": {"arguments": arguments}}) == expected
