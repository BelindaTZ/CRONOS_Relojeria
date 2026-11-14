"""Router del módulo `health`. Solo HTTP — sin lógica de negocio (Principio X)."""

from __future__ import annotations

from fastapi import APIRouter, Response

from health.schemas import Health
from health.service import get_health

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=Health,
    summary="Estado de salud del backend y sus dependencias críticas",
    responses={503: {"model": Health, "description": "Alguna dependencia crítica no responde"}},
)
def read_health(response: Response) -> Health:
    result = get_health()
    if result.status != "ok":
        response.status_code = 503
    return result
