from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class LineaVentaIn(BaseModel):
    # Solo relojes (feedback del usuario, 2026-09-11): las piezas nunca se venden
    # sueltas al mostrador — solo las consume el técnico al reparar (008). `pieza_id`
    # se conserva por compatibilidad de lectura con ventas históricas, pero ya no es
    # un valor aceptado de `item_tipo` en una venta nueva.
    item_tipo: Literal["reloj"] = "reloj"
    reloj_id: int | None = None
    pieza_id: int | None = None
    cantidad: int = Field(default=1, ge=1)
    precio_lista: Decimal | None = None  # por defecto el precio de catálogo


class VentaIn(BaseModel):
    cliente_id: int | None = None
    sucursal_id: int | None = None  # solo se usa como override si el vendedor no tiene una sola sucursal
    cita_id: int | None = None
    identificacion_fiscal: str | None = Field(default=None, max_length=20)
    lineas: list[LineaVentaIn] = Field(min_length=1)


class DescuentoVentaIn(BaseModel):
    descuento_id: int | None = None
    cupon_codigo: str | None = None


class PagoVentaIn(BaseModel):
    medio_pago: str = Field(min_length=1, max_length=20)
    monto: Decimal = Field(gt=0)
    referencia: str | None = Field(default=None, max_length=80)


class ConfirmarVentaIn(BaseModel):
    autorizacion_margen_minimo_id: int | None = None


class AnularVentaIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


# ---------------------------------------------------------------- salida
class LineaVentaOut(BaseModel):
    id: int
    item_tipo: str
    reloj_id: int | None = None
    pieza_id: int | None = None
    descripcion: str | None = None
    numero_serie: str | None = None
    cantidad: int
    precio_lista: Decimal
    precio_final: Decimal
    descuento_monto: Decimal | None = None
    base_imponible: Decimal | None = None
    iva_monto: Decimal | None = None
    tarifa_iva: Decimal | None = None
    costo: Decimal | None = None       # solo rol administrativo
    margen: Decimal | None = None      # solo rol administrativo


class GarantiaVentaOut(BaseModel):
    tipo: str
    periodo_dias: int
    fecha_inicio: date
    fecha_fin: date
    cobertura: str | None = None


class PagoVentaOut(BaseModel):
    pago_id: int
    medio_pago: str | None = None
    monto: Decimal
    referencia: str | None = None


class VentaOut(BaseModel):
    id: int
    numero: str
    numero_factura: str | None = None
    cliente_id: int
    cliente_nombre: str | None = None
    cliente_afiliado: str | None = None
    cliente_email: str | None = None
    sucursal_id: int
    sucursal_nombre: str | None = None
    vendedor_usuario_id: int | None = None
    vendedor_nombre: str | None = None
    cita_id: int | None = None
    estado: str
    fecha: datetime
    subtotal: Decimal
    total: Decimal
    subtotal_sin_impuestos: Decimal | None = None
    total_descuento: Decimal | None = None
    iva_porcentaje: Decimal | None = None
    iva_monto: Decimal | None = None
    pagado: Decimal | None = None
    saldo: Decimal | None = None
    descuento_aplicado: dict | None = None
    identificacion_fiscal: str | None = None
    margen_venta: Decimal | None = None  # solo rol administrativo
    costos_visibles: bool = False
    creado_en: datetime


class VentaDetalle(VentaOut):
    lineas: list[LineaVentaOut] = Field(default_factory=list)
    garantias: list[GarantiaVentaOut] = Field(default_factory=list)
    pagos: list[PagoVentaOut] = Field(default_factory=list)
    comprobantes: list[dict] = Field(default_factory=list)


class DescuentoAplicadoOut(BaseModel):
    precio_final: Decimal
    monto_descontado: Decimal
    margen_resultante: Decimal
    decision: str


class PagoRegistradoOut(BaseModel):
    pago_id: int
    medio_pago: str | None = None
    monto: Decimal
    saldo: Decimal


class CuentaPorCobrarOut(BaseModel):
    id: int
    origen_tipo: str
    origen_id: int
    cliente_id: int
    cliente_nombre: str | None = None
    monto_original: Decimal
    saldo: Decimal
    estado: str
    creado_en: datetime


class VentasDiaOut(BaseModel):
    fecha: date
    ventas: int
    total: Decimal
    margen: Decimal | None = None  # solo rol administrativo


# ---------------------------------------------------------------- facturación (config)
class ConfigFacturacionIn(BaseModel):
    razon_social: str = Field(min_length=2, max_length=200)
    nombre_comercial: str | None = Field(default=None, max_length=200)
    ruc: str = Field(min_length=10, max_length=13)
    direccion_matriz: str | None = Field(default=None, max_length=255)
    obligado_contabilidad: bool = True
    contribuyente_especial: str | None = Field(default=None, max_length=40)
    regimen: str | None = Field(default=None, max_length=40)
    leyenda_pie: str | None = Field(default=None, max_length=255)


class ConfigFacturacionOut(ConfigFacturacionIn):
    actualizado_en: datetime | None = None


class PuntoEmisionIn(BaseModel):
    establecimiento_codigo: str = Field(min_length=1, max_length=3)
    punto_emision_codigo: str = Field(min_length=1, max_length=3)
    direccion_establecimiento: str | None = Field(default=None, max_length=255)


class PuntoEmisionOut(PuntoEmisionIn):
    sucursal_id: int
    sucursal_nombre: str | None = None
    secuencial_actual: int


class EnviarFacturaOut(BaseModel):
    enviado: bool
    email: str | None = None
    detalle: str | None = None
