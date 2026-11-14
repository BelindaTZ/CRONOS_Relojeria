"""Schemas del módulo `reportes_estado` (feature 012).

Único punto de contacto entre el backend operativo y la plataforma de datos
(`contracts/pipeline-estado.openapi.yaml`). 013 lo consume para mostrar
"datos actualizados a HH:MM".
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DominioFrescuraOut(BaseModel):
    dominio: str
    ultima_carga_ts: datetime | None = None
    max_updated_at_origen: datetime | None = None
    ultimo_run_id: str | None = None
    estado_ultima_corrida: Literal["ok", "error", "sin_datos"] = "sin_datos"


class EstadoFrescuraOut(BaseModel):
    disponible: bool
    dominios: list[DominioFrescuraOut] = []


class ActualizarAhoraOut(BaseModel):
    run_id: str
    estado: str
