"""Conexiones del pipeline ELT (feature 012). Todas las credenciales vienen de
variables de entorno (`.env` vía el compose), nunca hardcodeadas (Ppio IX).
"""
from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg


def pg_readonly_dsn() -> str:
    """DSN de PostgreSQL con el rol de SOLO LECTURA del pipeline (migración
    `0029_rol_elt_readonly`) — nunca el usuario de la app (checklist DP002)."""
    host = os.environ["ELT_PG_HOST"]
    port = os.environ.get("ELT_PG_PORT", "5432")
    db = os.environ["ELT_PG_DB"]
    user = os.environ["ELT_PG_USER"]
    password = os.environ["ELT_PG_PASSWORD"]
    return f"host={host} port={port} dbname={db} user={user} password={password}"


@contextmanager
def pg_readonly_connection():
    """Conexión de solo lectura: `READ ONLY` a nivel de transacción, además del
    rol sin privilegios de escritura (defensa en profundidad — Spec §FR-006)."""
    conn = psycopg.connect(pg_readonly_dsn())
    try:
        conn.read_only = True
        yield conn
    finally:
        conn.close()


def clickhouse_client():
    """Cliente HTTP de ClickHouse (`clickhouse-connect`). Import perezoso para que
    `data/lib` no obligue a instalar la librería a quien solo usa `extract.py`."""
    import clickhouse_connect

    return clickhouse_connect.get_client(
        host=os.environ["ELT_CLICKHOUSE_HOST"],
        port=int(os.environ.get("ELT_CLICKHOUSE_PORT", "8123")),
        username=os.environ["ELT_CLICKHOUSE_USER"],
        password=os.environ["ELT_CLICKHOUSE_PASSWORD"],
        database=os.environ.get("ELT_CLICKHOUSE_DB", "wh"),
    )


def minio_client():
    """Cliente MinIO para `landing-zone` (import perezoso, mismo motivo)."""
    from minio import Minio

    endpoint = os.environ["ELT_MINIO_ENDPOINT"]
    return Minio(
        endpoint,
        access_key=os.environ["ELT_MINIO_USER"],
        secret_key=os.environ["ELT_MINIO_PASSWORD"],
        secure=os.environ.get("ELT_MINIO_SECURE", "false").lower() == "true",
    )


def landing_bucket() -> str:
    return os.environ.get("ELT_LANDING_ZONE_BUCKET", "landing-zone")
