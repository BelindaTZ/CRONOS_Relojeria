"""`GET /health`: 200 con dependencias arriba, 503 si alguna falla; forma del payload.

Conforme a `specs/000-bootstrap-infraestructura/contracts/health.openapi.yaml`.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from health import repository
from health.router import router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_health_ok_cuando_todas_las_dependencias_arriba(client, monkeypatch):
    monkeypatch.setattr(repository, "ping_db", lambda: True)
    monkeypatch.setattr(repository, "ping_storage", lambda: True)

    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "up"
    assert body["storage"] == "up"
    # forma conforme al contrato
    assert set(body) >= {"status", "db", "storage"}
    assert body["status"] in {"ok", "degraded"}


def test_health_503_cuando_db_caida(client, monkeypatch):
    monkeypatch.setattr(repository, "ping_db", lambda: False)
    monkeypatch.setattr(repository, "ping_storage", lambda: True)

    resp = client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["db"] == "down"
    assert body["storage"] == "up"


def test_health_503_cuando_storage_caido(client, monkeypatch):
    monkeypatch.setattr(repository, "ping_db", lambda: True)
    monkeypatch.setattr(repository, "ping_storage", lambda: False)

    resp = client.get("/health")

    assert resp.status_code == 503
    assert resp.json()["storage"] == "down"
