"""Router del módulo `reportes_estado` (feature 012). Solo HTTP — la lógica
vive en `service.py` (Principio X)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from reportes_estado import service
from reportes_estado.schemas import ActualizarAhoraOut, EstadoFrescuraOut
from shared.guard import CurrentUser, require_perm

router = APIRouter(tags=["reportes-estado"])

_leer = require_perm("reportes", "consultar")


@router.get("/reportes/estado-frescura", response_model=EstadoFrescuraOut)
def estado_frescura(_: CurrentUser = Depends(_leer)) -> dict:
    return service.get_estado_frescura()


@router.post(
    "/reportes/actualizar-ahora",
    response_model=ActualizarAhoraOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {"description": "Ya hay una corrida en curso"}, 503: {"description": "Airflow no disponible"}},
)
def actualizar_ahora(_: CurrentUser = Depends(_leer)) -> dict:
    return service.disparar_actualizacion()
