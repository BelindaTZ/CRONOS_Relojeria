from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TipoPieza = Literal["original", "no_original_equivalente"]
TipoMovimiento = Literal[
    "ingreso",
    "consumo_ot",
    "venta_suelta",
    "ajuste",
    "merma",
    "transferencia_salida",
    "transferencia_entrada",
]
EstadoLote = Literal["vigente", "proximo_vencer", "vencido"]


UnidadMedida = Literal["unidad", "ml", "g", "mm", "par", "juego", "metro", "litro"]


class PiezaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=60)
    descripcion: str = Field(min_length=1, max_length=255)
    tipo: TipoPieza = "original"
    proveedor_id: int | None = None
    costo_adquisicion: Decimal | None = Field(default=None, ge=0)
    precio_venta_suelta: Decimal | None = Field(default=None, ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    unidad_medida: UnidadMedida = "unidad"
    marca_compatible: str | None = Field(default=None, max_length=255)
    perecedera: bool = False
    calibres_compatibles: list[int] = Field(default_factory=list)


class PiezaPatch(BaseModel):
    descripcion: str | None = Field(default=None, max_length=255)
    tipo: TipoPieza | None = None
    proveedor_id: int | None = None
    costo_adquisicion: Decimal | None = Field(default=None, ge=0)
    precio_venta_suelta: Decimal | None = Field(default=None, ge=0)
    stock_minimo: int | None = Field(default=None, ge=0)
    unidad_medida: UnidadMedida | None = None
    marca_compatible: str | None = Field(default=None, max_length=255)
    perecedera: bool | None = None
    activo: bool | None = None
    calibres_compatibles: list[int] | None = None


class StockSucursalOut(BaseModel):
    sucursal_id: int
    stock_actual: int
    bajo_minimo: bool


class LoteOut(BaseModel):
    id: int
    sucursal_id: int
    numero_lote: str
    fecha_caducidad: date
    cantidad: int
    estado: str
    dias_restantes: int


class PiezaOut(BaseModel):
    id: int
    codigo: str
    descripcion: str
    tipo: str
    proveedor_id: int | None = None
    costos_visibles: bool = True
    costo_adquisicion: Decimal | None = None
    precio_venta_suelta: Decimal | None = None
    stock_minimo: int
    unidad_medida: str = "unidad"
    marca_compatible: str | None = None
    perecedera: bool
    activo: bool
    calibres_compatibles: list[int] = Field(default_factory=list)
    stock_total: int = 0
    bajo_minimo: bool = False


class PiezaDetalle(PiezaOut):
    stock_por_sucursal: list[StockSucursalOut] = Field(default_factory=list)
    lotes: list[LoteOut] = Field(default_factory=list)


class MovimientoIn(BaseModel):
    sucursal_id: int
    tipo: TipoMovimiento
    cantidad: int = Field(
        description="magnitud (>0) para todos los tipos salvo 'ajuste', que acepta signo"
    )
    lote: str | None = Field(default=None, max_length=60)
    fecha_caducidad: date | None = None
    documento_tipo: str | None = Field(default=None, max_length=30)
    documento_id: int | None = None
    nota: str | None = Field(default=None, max_length=255)


class MovimientoOut(BaseModel):
    id: int
    pieza_id: int
    sucursal_id: int
    tipo: str
    cantidad: int
    lote_id: int | None = None
    documento_tipo: str | None = None
    documento_id: int | None = None
    nota: str | None = None
    creado_por: int | None = None
    creado_en: datetime


class LoteCaducidadOut(LoteOut):
    pieza_id: int
    pieza_codigo: str
    pieza_descripcion: str


class ValorPiezasOut(BaseModel):
    referencias: int
    a_precio_venta: Decimal
    a_costo: Decimal | None = None
