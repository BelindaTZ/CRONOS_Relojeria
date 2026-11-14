"""Arranque: el backend no acepta tráfico hasta que PostgreSQL responde (FR-006).

Se simula el engine: falla unos intentos y luego responde. También se verifica
el fallo explícito al agotar el timeout.
"""

from __future__ import annotations

import pytest

import main


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, *_a, **_k):
        return None


class _FlakyEngine:
    """Falla `fallos` veces y luego conecta correctamente."""

    def __init__(self, fallos: int):
        self.fallos = fallos
        self.intentos = 0

    def connect(self):
        self.intentos += 1
        if self.intentos <= self.fallos:
            raise RuntimeError("connection refused")
        return _FakeConn()


class _DeadEngine:
    def connect(self):
        raise RuntimeError("connection refused")


def test_espera_y_arranca_cuando_db_disponible(monkeypatch):
    engine = _FlakyEngine(fallos=3)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main.time, "sleep", lambda _s: None)

    main._wait_for_database(timeout_seconds=30)

    assert engine.intentos == 4  # 3 fallos + 1 éxito


def test_falla_explicito_al_agotar_timeout(monkeypatch):
    monkeypatch.setattr(main, "engine", _DeadEngine())
    monkeypatch.setattr(main.time, "sleep", lambda _s: None)

    # monotonic avanza de golpe para agotar el deadline sin esperar de verdad
    valores = iter([0.0, 0.0, 100.0, 100.0, 100.0, 100.0])
    monkeypatch.setattr(main.time, "monotonic", lambda: next(valores, 100.0))

    with pytest.raises(RuntimeError, match="no respondió"):
        main._wait_for_database(timeout_seconds=1)
