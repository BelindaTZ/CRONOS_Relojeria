"""Lógica del módulo `health`: compone el estado agregado de la plataforma."""

from __future__ import annotations

from shared.config import get_settings
from health import repository
from health.schemas import Health


def get_health() -> Health:
    """Estado agregado. `status` es 'ok' solo si todas las dependencias están arriba."""
    db_up = repository.ping_db()
    storage_up = repository.ping_storage()
    healthy = db_up and storage_up
    return Health(
        status="ok" if healthy else "degraded",
        db="up" if db_up else "down",
        storage="up" if storage_up else "down",
        version=get_settings().app_version,
    )
