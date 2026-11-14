from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EstadoEnvio = Literal[
    "encolado", "enviando", "enviado", "entregado", "rebotado", "fallido", "sin_destinatario", "cancelado"
]


class EncolarIn(BaseModel):
    tipo: str
    disparo_origen_tipo: str
    disparo_origen_id: int
    hito: str
    contexto: dict[str, Any] = Field(default_factory=dict)
    cliente_id: int | None = None
    usuario_id: int | None = None
    destinatario_email: str | None = None
    programar_para: datetime | None = None


class EnvioOut(BaseModel):
    id: int
    tipo: str
    destinatario_email: str | None = None
    cliente_id: int | None = None
    usuario_id: int | None = None
    disparo_origen_tipo: str
    disparo_origen_id: int
    hito: str
    estado: EstadoEnvio
    motivo_estado: str | None = None
    intentos: int
    proxima_ejecucion: datetime
    creado_en: datetime
    actualizado_en: datetime


class PreferenciaIn(BaseModel):
    tipo_comunicacion: str
    opt_in: bool


class PreferenciaOut(BaseModel):
    tipo_comunicacion: str
    opt_in: bool


class PlantillaIn(BaseModel):
    asunto: str = Field(min_length=1, max_length=200)
    cuerpo: str = Field(min_length=1)


class PlantillaOut(BaseModel):
    tipo: str
    asunto: str | None = None
    cuerpo: str | None = None
    variables: dict | None = None
    version: int
    activa: bool
    actualizado_en: datetime | None = None


class PlantillaDetalleOut(BaseModel):
    actual: PlantillaOut | None = None
    historial: list[PlantillaOut] = []


class PreviewIn(BaseModel):
    contexto: dict[str, Any] = Field(default_factory=dict)


class PreviewOut(BaseModel):
    asunto: str
    html: str
    texto: str
