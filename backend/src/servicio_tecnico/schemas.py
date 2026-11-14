from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Estado = Literal[
    "recibido", "en_diagnostico", "presupuesto", "en_reparacion", "listo", "entregado", "cancelada"
]
# Binaria a propósito (feedback del usuario, 2026-09-11): una línea de presupuesto
# es original O no original, nunca las dos — "mixto" (Esp. FR-003c) describe el
# presupuesto EN CONJUNTO cuando sus líneas difieren entre sí, no la elección de
# una sola línea.
PreferenciaLinea = Literal["original", "no_original"]


# ---------------------------------------------------------------- entrada
class OrdenTrabajoIn(BaseModel):
    numero_serie: str = Field(min_length=1, max_length=80)
    cliente_id: int
    motivo: str = Field(min_length=3, max_length=4000)
    tipo_reparacion: str = Field(min_length=2, max_length=40)
    cita_id: int | None = None
    sucursal_id: int | None = None
    tecnico_id: int | None = None  # override del sugerido automáticamente; None = auto-sugerir
    override_adquisicion_motivo: str | None = Field(default=None, max_length=255)


class TecnicoSugeridoOut(BaseModel):
    tecnico_id: int | None = None
    tecnico_nombre: str | None = None


class RelojElegibleOut(BaseModel):
    """Unidad seleccionable para abrir una OT — nunca número de serie a mano (Ppio XI).
    `cliente_id` viene poblado cuando la unidad tiene una venta confirmada (caso normal);
    queda `None` en la ruta de excepción (unidad de alta manual sin venta registrada)."""

    id: int
    numero_serie: str
    marca: str
    referencia: str | None = None
    cliente_id: int | None = None
    cliente_nombre: str | None = None
    cliente_afiliado: str | None = None


class OrdenTrabajoPatch(BaseModel):
    tecnico_id: int | None = None
    motivo: str | None = Field(default=None, max_length=4000)
    tipo_reparacion: str | None = Field(default=None, max_length=40)


class DiagnosticoIn(BaseModel):
    diagnostico: str = Field(min_length=3, max_length=8000)


class TrabajoRealizadoIn(BaseModel):
    trabajo_realizado: str = Field(min_length=1, max_length=8000)


class LineaPresupuestoIn(BaseModel):
    pieza_original_id: int
    pieza_no_original_id: int | None = None
    precio_original: Decimal | None = None
    precio_no_original: Decimal | None = None
    cantidad: int = Field(default=1, ge=1)


class PresupuestoIn(BaseModel):
    precio_servicio: Decimal = Field(ge=0)
    lineas: list[LineaPresupuestoIn] = Field(default_factory=list)


class PreferenciaLineaIn(BaseModel):
    linea_id: int
    preferencia: PreferenciaLinea


class AprobarPresupuestoIn(BaseModel):
    confirmado_por: str = Field(min_length=2, max_length=160)
    medio_confirmacion: str | None = Field(default=None, max_length=40)
    preferencias: list[PreferenciaLineaIn] = Field(default_factory=list)
    fecha_estimada_entrega: date


class PiezaUsadaIn(BaseModel):
    pieza_id: int
    tipo_elegido: Literal["original", "no_original"] = "original"
    cantidad: int = Field(default=1, ge=1)


class SolicitarCompraUrgenteIn(BaseModel):
    pieza_id: int
    cantidad: int = Field(default=1, ge=1)
    nota: str | None = Field(default=None, max_length=500)


class LubricacionIn(BaseModel):
    punto_lubricacion_id: int | None = None
    punto_nombre: str | None = Field(default=None, max_length=120)
    producto_usado_codigo: str = Field(min_length=1, max_length=20)


class HorasIn(BaseModel):
    horas: Decimal = Field(gt=0, le=999)


class DescuentoOTIn(BaseModel):
    tipo: Literal["porcentaje", "monto"]
    valor: Decimal = Field(gt=0)
    es_cupon: bool = False
    codigo_cupon: str | None = None


class PagoOTIn(BaseModel):
    medio_pago: str = Field(min_length=1, max_length=20)
    monto: Decimal = Field(gt=0)
    referencia: str | None = Field(default=None, max_length=80)


class CambioEstadoIn(BaseModel):
    estado: Estado


class EntregarIn(BaseModel):
    autorizacion_credito_id: int | None = None


class ReabrirGarantiaIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=4000)
    tipo_reparacion: str | None = Field(default=None, max_length=40)


class ReportarDanoIn(BaseModel):
    descripcion: str = Field(min_length=3, max_length=2000)
    pieza_id: int | None = None
    reloj_serie: str | None = None


# ---------------------------------------------------------------- salida
class LineaPresupuestoOut(BaseModel):
    id: int
    pieza_original_id: int
    pieza_original: str | None = None
    pieza_no_original_id: int | None = None
    pieza_no_original: str | None = None
    precio_original: Decimal
    precio_no_original: Decimal | None = None
    diferencia: Decimal | None = None
    preferencia_cliente: str | None = None
    cantidad: int
    stock_original_suficiente: bool = True
    stock_no_original_suficiente: bool = True


class PresupuestoOut(BaseModel):
    id: int
    orden_trabajo_id: int
    precio_servicio: Decimal
    estado: str
    confirmado_por: str | None = None
    medio_confirmacion: str | None = None
    fecha_confirmacion: datetime | None = None
    lineas: list[LineaPresupuestoOut] = Field(default_factory=list)


class PiezaUsadaOut(BaseModel):
    id: int
    pieza_id: int
    pieza_codigo: str | None = None
    descripcion: str | None = None
    tipo_elegido: str
    cantidad: int
    costo: Decimal | None = None  # solo rol administrativo


class LubricacionOut(BaseModel):
    id: int
    punto_nombre: str
    producto_recomendado: str | None = None
    producto_usado: str
    desviacion: bool
    fecha: datetime


class OrdenTrabajoOut(BaseModel):
    id: int
    numero: str
    reloj_id: int
    reloj_serie: str | None = None
    reloj_marca: str | None = None
    reloj_referencia: str | None = None
    cliente_id: int
    cliente_nombre: str | None = None
    cliente_afiliado: str | None = None
    tecnico_id: int | None = None
    tecnico_nombre: str | None = None
    sucursal_id: int
    sucursal_nombre: str | None = None
    cita_id: int | None = None
    ot_original_id: int | None = None
    motivo: str
    diagnostico: str | None = None
    trabajo_realizado: str | None = None
    tipo_reparacion: str
    horas_trabajadas: Decimal | None = None
    fecha_ingreso: datetime
    fecha_estimada_entrega: date | None = None
    fecha_real_entrega: datetime | None = None
    estado: str
    garantia_periodo_dias: int | None = None
    garantia_cobertura: str | None = None
    reproceso: bool = False
    precio_cobrado: Decimal | None = None
    saldo: Decimal | None = None
    # solo rol administrativo:
    costo_interno: Decimal | None = None
    margen_real: Decimal | None = None
    costos_visibles: bool = False
    creado_en: datetime


class OrdenTrabajoDetalle(OrdenTrabajoOut):
    piezas: list[PiezaUsadaOut] = Field(default_factory=list)
    lubricacion: list[LubricacionOut] = Field(default_factory=list)
    presupuesto: PresupuestoOut | None = None
    pagos: list[dict] = Field(default_factory=list)
    historial: list[dict] = Field(default_factory=list)
    documentos: list[dict] = Field(default_factory=list)


class CosteoOut(BaseModel):
    costo_mano_obra: Decimal
    costo_piezas: Decimal
    costo_insumos: Decimal
    costo_interno: Decimal
    bono_prorrateado: Decimal
    margen_objetivo: Decimal
    precio_sugerido: Decimal
    precio_cobrado: Decimal | None = None
    margen_real: Decimal | None = None
    base_mano_obra: str


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


class DanoPayloadOut(BaseModel):
    orden_trabajo_id: int
    tecnico_id: int | None = None
    causa: str = "dano_servicio"
    descripcion: str
    pieza_id: int | None = None
    reloj_serie: str | None = None
    sancion_automatica: bool = False


class InformeServicioOut(BaseModel):
    orden_trabajo_id: int
    numero: str
    cliente: str | None = None
    tecnico: str | None = None
    fecha: date | None = None
    numero_serie: str | None = None
    trabajo_realizado: str | None = None
    repuestos: list[str] = Field(default_factory=list)
    precio_arreglo: Decimal | None = None
