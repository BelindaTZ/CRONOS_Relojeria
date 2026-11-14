"""Fixtures de los tests de `data/` (feature 012).

Estos tests son de INTEGRACIÓN contra el stack real (db, clickhouse, minio) —
se ejecutan dentro del contenedor `airflow-scheduler`, que ya trae las mismas
credenciales/host que usa el propio DAG:

    docker compose exec airflow-scheduler pytest /opt/airflow/tests -q

No corren en el pipeline de `backend/tests` (esa suite no tiene acceso a
ClickHouse/Airflow por diseño — Spec §FR-011). Si algún servicio no responde,
el test se salta en vez de fallar en rojo (para no romper un `pytest` corrido
sin el stack de 012 levantado).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # /opt/airflow

from lib import db as libdb  # noqa: E402


@pytest.fixture(scope="session")
def ch():
    try:
        cliente = libdb.clickhouse_client()
        cliente.command("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ClickHouse no disponible: {exc}")
    return cliente


@pytest.fixture(scope="session")
def pg():
    try:
        with libdb.pg_readonly_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL (rol de solo lectura) no disponible: {exc}")
    with libdb.pg_readonly_connection() as conn:
        yield conn
