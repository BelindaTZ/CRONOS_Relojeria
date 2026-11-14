from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

CAUSAS = ("dano_tienda", "dano_transito", "robo_perdida", "defecto_fabrica", "dano_servicio", "insumo_caducado")
ESTADOS = ("en_evaluacion", "dado_de_baja", "en_reclamo_proveedor", "en_reclamo_seguro", "reparado_reingresado")


class MermaIn(BaseModel):
    bien_tipo: str = Field(pattern="^(reloj|pieza)$")
    reloj_id: int | None = None
    numero_serie: str | None = None  # alterno a reloj_id (008 devuelve la serie, no el id)
    pieza_id: int | None = None
    lote_id: int | None = None
    cantidad: int = Field(default=1, gt=0)
    causa: str = Field(pattern="^(" + "|".join(CAUSAS) + ")$")
    categoria_merma_id: int | None = None
    descripcion: str | None = Field(default=None, max_length=500)
    fecha_evento: date
    sucursal_id: int
    orden_trabajo_id: int | None = None
    tecnico_id: int | None = None
    transferencia_id: int | None = None


class EstadoIn(BaseModel):
    estado: str = Field(pattern="^(" + "|".join(ESTADOS) + ")$")


class AutorizarBajaIn(BaseModel):
    observacion: str | None = Field(default=None, max_length=255)


class ReclamoIn(BaseModel):
    destino: str = Field(pattern="^(proveedor|seguro)$")
    proveedor_id: int | None = None
    aseguradora: str | None = Field(default=None, max_length=120)


class ReclamoPatch(BaseModel):
    estado: str | None = Field(default=None, max_length=24)
    monto_recuperado: Decimal | None = None


class DocumentoSoporteOut(BaseModel):
    id: int
    tipo: str
    nombre: str
    url: str


class ReclamoOut(BaseModel):
    id: int
    destino: str
    proveedor_id: int | None
    proveedor_nombre: str | None = None
    aseguradora: str | None
    estado: str
    monto_recuperado: Decimal


class HistorialEstadoOut(BaseModel):
    estado: str
    actor_nombre: str | None
    creado_en: datetime


class AutorizacionBajaOut(BaseModel):
    autorizador_nombre: str
    fecha: datetime
    observacion: str | None


class MermaOut(BaseModel):
    id: int
    numero: str
    bien_tipo: str
    reloj_id: int | None
    reloj_serie: str | None = None
    pieza_id: int | None
    pieza_codigo: str | None = None
    lote_id: int | None
    cantidad: int
    causa: str
    categoria_merma_id: int | None
    categoria_merma_nombre: str | None = None
    descripcion: str | None
    fecha_evento: date
    sucursal_id: int
    sucursal_nombre: str | None = None
    responsable_nombre: str | None = None
    costo_perdida: Decimal | None = None  # None si el rol no ve costos
    costo_visible: bool = False
    estado: str
    orden_trabajo_id: int | None
    tecnico_id: int | None
    tecnico_nombre: str | None = None
    transferencia_id: int | None
    autorizacion: AutorizacionBajaOut | None = None
    asiento_id: int | None
    documentos: list[DocumentoSoporteOut] = Field(default_factory=list)
    reclamos: list[ReclamoOut] = Field(default_factory=list)
    historial: list[HistorialEstadoOut] = Field(default_factory=list)
    creado_en: datetime


class ReporteMermaItem(BaseModel):
    causa: str
    frecuencia: int
    monto_total: Decimal
