"""Capa de acceso a datos del módulo `health`: pings a las dependencias críticas.

Módulo PLANTILLA — las features 001+ replican esta estructura
(router -> service -> repository).
"""

from __future__ import annotations

from sqlalchemy import text

from shared.database import engine
from shared.storage import get_client


def ping_db() -> bool:
    """True si PostgreSQL responde a un `SELECT 1`."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def ping_storage() -> bool:
    """True si MinIO responde (se lista buckets, operación barata)."""
    try:
        client = get_client()
        # list_buckets() devuelve un iterable perezoso; forzamos la llamada.
        list(client.list_buckets())
        return True
    except Exception:
        return False
