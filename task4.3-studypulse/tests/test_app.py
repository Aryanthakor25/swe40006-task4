"""Unit tests for StudyPulse. Run with:  pip install -r requirements-dev.txt && pytest -q"""
import importlib

import fakeredis
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("REDIS_HOST", raising=False)
    import app.main as main
    importlib.reload(main)  # fresh in-memory store per test
    return TestClient(main.app)


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "backend": "memory"}


def test_add_and_list_session(client):
    r = client.post("/api/sessions", json={"unit_code": "swe40006", "minutes": 45, "note": "Dockerfile"})
    assert r.status_code == 201
    assert r.json()["unit_code"] == "SWE40006"
    sessions = client.get("/api/sessions").json()
    assert len(sessions) == 1 and sessions[0]["minutes"] == 45


@pytest.mark.parametrize("payload", [
    {"unit_code": "SWE4", "minutes": 30},
    {"unit_code": "SWE40006", "minutes": 0},
    {"unit_code": "SWE40006", "minutes": 601},
])
def test_validation_rejects_bad_input(client, payload):
    assert client.post("/api/sessions", json=payload).status_code == 422


def test_stats_totals_per_unit(client):
    for unit, mins in [("SWE40006", 30), ("SWE40006", 20), ("COS40005", 60)]:
        client.post("/api/sessions", json={"unit_code": unit, "minutes": mins})
    stats = client.get("/api/stats").json()
    assert stats["total_minutes"] == 110
    assert stats["minutes_per_unit"] == {"COS40005": 60, "SWE40006": 50}


def test_info_reads_env(monkeypatch):
    monkeypatch.delenv("REDIS_HOST", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    import app.main as main
    importlib.reload(main)
    body = TestClient(main.app).get("/api/info").json()
    assert body["environment"] == "staging" and body["version"] == "9.9.9"


def test_redis_store_round_trip():
    from app.store import RedisStore
    s = RedisStore(fakeredis.FakeRedis(decode_responses=True))
    s.add_session({"unit_code": "SWE40006", "minutes": 10, "note": "", "logged_at": "x"})
    assert s.list_sessions()[0]["minutes"] == 10
    assert s.incr_visits() == 1 and s.incr_visits() == 2
    assert s.ping()


def test_index_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200 and "StudyPulse" in r.text
