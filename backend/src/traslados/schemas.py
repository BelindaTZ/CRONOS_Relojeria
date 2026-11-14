from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

ItemTipo = Literal["reloj", "pieza"]
EstadoTransferencia = Literal["en_preparacion", "en_transito", "recibida", "parcial", "cancelada"]


class LineaTransferenciaIn(BaseModel):
    item_tipo: ItemTipo
    reloj_id: int | None = None
    pieza_id: int | None = None
    cantidad_enviada: int = Field(default=1, gt=0)


class TransferenciaIn(BaseModel):
    sucursal_origen_id: int
    sucursal_destino_id: int
    motivo: str = Field(min_length=3, max_length=500)
    lineas: list[LineaTransferenciaIn] = Field(min_length=1)
    enviar_ahora: bool = False


class EnviarIn(BaseModel):
    responsable_envio_id: int | None = None


class RecibirLineaIn(BaseModel):
    linea_transferencia_id: int
    cantidad_recibida: int = Field(ge=0)


class RecibirIn(BaseModel):
    responsable_recepcion_id: int | None = None
    lineas: list[RecibirLineaIn] = Field(min_length=1)


class CancelarIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)


class LineaTransferenciaOut(BaseModel):
    id: int
    item_tipo: str
    reloj_id: int | None = None
    pieza_id: int | None = None
    etiqueta: str
    cantidad_enviada: int
    cantidad_recibida: int | None = None


class TransferenciaOut(BaseModel):
    id: int
    sucursal_origen_id: int
    sucursal_destino_id: int
    estado: str
    motivo: str
    motivo_cancelacion: str | None = None
    fecha_envio: datetime | None = None
    fecha_recepcion: datetime | None = None
    responsable_envio_id: int | None = None
    responsable_recepcion_id: int | None = None
    creado_en: datetime
    lineas: list[LineaTransferenciaOut] = Field(default_factory=list)
    tiene_discrepancias: bool = False


class AccionMerma(BaseModel):
    causa: str = "dano_transito"
    item_tipo: str
    reloj_id: int | None = None
    pieza_id: int | None = None
    cantidad: int
    referencia: str | None = None


class DiscrepanciaOut(BaseModel):
    id: int
    linea_transferencia_id: int
    item_tipo: str
    etiqueta: str
    cantidad_faltante: int
    resuelta: bool
    merma_id: int | None = None
    accion_merma: AccionMerma


class ItemDisponibleOut(BaseModel):
    id: int
    etiqueta: str
    detalle: str | None = None
    stock: int | None = None


class SucursalMiniOut(BaseModel):
    id: int
    nombre: str


class CostoReferencialOut(BaseModel):
    costo_traslado_venta: Decimal | None = None
