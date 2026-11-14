from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Motivo = Literal["compra", "servicio_tecnico", "consulta"]
Estado = Literal["pendiente", "confirmada", "cancelada", "atendida"]
Rango = Literal["dia", "semana"]


class CitaIn(BaseModel):
    cliente_id: int
    sucursal_id: int
    canal_cita_id: int
    motivo: Motivo
    fecha_preferida: datetime
    observaciones: str | None = Field(default=None, max_length=2000)


class CitaPatch(BaseModel):
    canal_cita_id: int | None = None
    motivo: Motivo | None = None
    fecha_preferida: datetime | None = None
    observaciones: str | None = Field(default=None, max_length=2000)


class ConfirmarIn(BaseModel):
    fecha_confirmada: datetime | None = None


class CancelarIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


class AtenderIn(BaseModel):
    venta_id: int | None = None
    orden_trabajo_id: int | None = None


class VincularIn(BaseModel):
    venta_id: int | None = None
    orden_trabajo_id: int | None = None


class CitaOut(BaseModel):
    id: int
    cliente_id: int
    cliente_nombre: str | None = None
    cliente_afiliado: str | None = None
    sucursal_id: int
    sucursal_nombre: str | None = None
    canal_cita_id: int
    canal_nombre: str | None = None
    motivo: str
    fecha_preferida: datetime
    fecha_confirmada: datetime | None = None
    estado: str
    motivo_cancelacion: str | None = None
    observaciones: str | None = None
    venta_id: int | None = None
    orden_trabajo_id: int | None = None
    creado_en: datetime


class AccionCreacion(BaseModel):
    tipo: Literal["crear_venta", "crear_ot"]
    cliente_id: int
    cita_id: int


class ConfirmarOut(BaseModel):
    cita: CitaOut
    warning: str | None = None


class AtenderOut(BaseModel):
    cita: CitaOut
    accion: AccionCreacion | None = None


class ConversionOut(BaseModel):
    atendidas: int
    con_transaccion: int
    tasa: float


class AgendaItemOut(CitaOut):
    hora: datetime  # confirmada si existe, si no preferida
