from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from indusmon.app import create_app
from indusmon.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db", tmp_path / "test.db")
    monkeypatch.setattr(settings, "seed_demo", True)
    monkeypatch.setattr(settings, "sim_port", 15020)  # avoid clash with live demo
    app = create_app(start_sim=False, start_collector=False)
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_devices_seeded(client):
    r = client.get("/api/v1/devices")
    assert r.status_code == 200
    ids = {d["id"] for d in r.json()}
    assert {"boiler-01", "line-02"} <= ids
    boiler = next(d for d in r.json() if d["id"] == "boiler-01")
    assert any(t["name"] == "steam_temp" for t in boiler["tags"])


def test_device_conflict_and_patch(client):
    body = {
        "id": "x-1",
        "name": "X",
        "host": "127.0.0.1",
        "port": 15020,
        "unit_id": 9,
        "tags": [{"name": "t", "register": 0}],
    }
    assert client.post("/api/v1/devices", json=body).status_code == 201
    assert client.post("/api/v1/devices", json=body).status_code == 409
    r = client.patch("/api/v1/devices/x-1", json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert client.patch("/api/v1/devices/nope", json={"enabled": True}).status_code == 404


def test_readings_empty_and_range(client):
    r = client.get("/api/v1/readings", params={"device_id": "boiler-01"})
    assert r.status_code == 200
    assert r.json() == []
    r = client.get(
        "/api/v1/readings",
        params={"device_id": "boiler-01", "from": 200, "to": 100},
    )
    assert r.status_code == 400


def test_alerts_empty_and_metrics(client):
    assert client.get("/api/v1/alerts").json() == []
    m = client.get("/api/v1/metrics").json()
    assert m["devices_enabled"] >= 2
    assert client.get("/").status_code == 200
