import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.main import app
from app.static import mount_static


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def sample(name, labels=None):
    return REGISTRY.get_sample_value(name, labels or {}) or 0


def test_metrics_endpoint_is_exposed(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "piis_sessions_active" in resp.text
    assert "piis_commands_total" in resp.text


def test_http_requests_are_counted(client):
    labels = {"method": "GET", "path": "/api/health", "status": "200"}
    before = sample("piis_http_request_seconds_count", labels)
    client.get("/api/health")
    assert sample("piis_http_request_seconds_count", labels) == before + 1


def test_unknown_path_uses_one_label(client):
    labels = {"method": "GET", "path": "unmatched", "status": "404"}
    before = sample("piis_http_request_seconds_count", labels)
    client.get("/api/nope-1")
    client.get("/api/nope-2")
    assert sample("piis_http_request_seconds_count", labels) == before + 2


def test_sessions_gauge_and_command_counter(client):
    sid = client.post("/api/sessions", json={"protocol": "ssh", "host": "sw1"}).json()["id"]
    assert sample("piis_sessions_active") == 1
    labels = {"risk": "config", "decision": "confirmed", "source": "manual"}
    before = sample("piis_commands_total", labels)
    client.post(f"/api/sessions/{sid}/commands", json={"command": "vlan 20", "confirmed": True})
    assert sample("piis_commands_total", labels) == before + 1
    client.delete(f"/api/sessions/{sid}")
    assert sample("piis_sessions_active") == 0


def test_static_files_are_served(tmp_path):
    (tmp_path / "index.html").write_text("<h1>PIIS</h1>", encoding="utf-8")
    web = FastAPI()

    @web.get("/api/ping")
    def ping():
        return {"ok": True}

    assert mount_static(web, str(tmp_path))
    c = TestClient(web)
    assert "PIIS" in c.get("/").text
    assert c.get("/api/ping").json() == {"ok": True}


def test_static_is_skipped_without_build(tmp_path):
    assert not mount_static(FastAPI(), "")
    assert not mount_static(FastAPI(), str(tmp_path))
