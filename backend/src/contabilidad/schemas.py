from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TipoCuenta = Literal["activo", "pasivo", "patrimonio", "ingreso", "gasto"]
EstadoPago = Literal["pagado", "por_pagar"]
Frecuencia = Literal["mensual", "bimestral", "trimestral"]


# ---------------------------------------------------------------- plan de cuentas
class CuentaContableIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=2, max_length=160)
    tipo: TipoCuenta
    cuenta_padre_codigo: str | None = None
    imputable: bool = True


class CuentaContableOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    tipo: str
    cuenta_padre_id: int | None = None
    imputable: bool
    activa: bool


# ---------------------------------------------------------------- diario / mayor / balance
class LineaAsientoIn(BaseModel):
    cuenta: str  # código de cuenta_contable
    debe: Decimal = Field(default=Decimal("0"), ge=0)
    haber: Decimal = Field(default=Decimal("0"), ge=0)


class AsientoIn(BaseModel):
    fecha: date
    glosa: str = Field(min_length=2, max_length=255)
    ajuste_de_asiento_id: int | None = None
    lineas: list[LineaAsientoIn] = Field(min_length=2)


class LineaAsientoOut(BaseModel):
    id: int
    cuenta_id: int
    cuenta_codigo: str
    cuenta_nombre: str
    debe: Decimal
    haber: Decimal


class AsientoOut(BaseModel):
    id: int
    fecha: date
    glosa: str
    origen: str
    origen_id: int | None = None
    ajuste_de_asiento_id: int | None = None
    lineas: list[LineaAsientoOut] = Field(default_factory=list)
    total_debe: Decimal
    total_haber: Decimal
    creado_en: datetime


class MovimientoMayorOut(BaseModel):
    asiento_id: int
    fecha: date
    glosa: str
    debe: Decimal
    haber: Decimal


class MayorOut(BaseModel):
    cuenta_codigo: str
    cuenta_nombre: str
    movimientos: list[MovimientoMayorOut]
    saldo: Decimal


class FilaBalanceOut(BaseModel):
    cuenta_codigo: str
    cuenta_nombre: str
    tipo: str
    debe: Decimal
    haber: Decimal


class BalanceComprobacionOut(BaseModel):
    periodo: str | None = None
    filas: list[FilaBalanceOut]
    total_debe: Decimal
    total_haber: Decimal
    cuadrado: bool


class EstadoResultadosOut(BaseModel):
    periodo: str | None = None
    sucursal_id: int | None = None
    ingresos: Decimal
    costos: Decimal
    gastos: Decimal
    utilidad_neta: Decimal
    detalle: list[FilaBalanceOut] = Field(default_factory=list)


# ---------------------------------------------------------------- caja
class MovimientoCajaIn(BaseModel):
    tipo: Literal["entrada", "salida"]
    monto: Decimal = Field(gt=0)
    medio_pago: str | None = None
    documento_tipo: str | None = None
    documento_id: int | None = None
    nota: str | None = Field(default=None, max_length=255)


class CerrarCajaIn(BaseModel):
    efectivo_contado: Decimal = Field(ge=0)


class MovimientoCajaOut(BaseModel):
    id: int
    tipo: str
    monto: Decimal
    medio_pago: str | None = None
    documento_tipo: str | None = None
    documento_id: int | None = None
    nota: str | None = None
    creado_en: datetime


class SesionCajaOut(BaseModel):
    id: int
    sucursal_id: int
    sucursal_nombre: str | None = None
    saldo_inicial: Decimal
    abierta_en: datetime
    estado: str
    efectivo_contado: Decimal | None = None
    efectivo_esperado: Decimal | None = None
    diferencia: Decimal | None = None
    cerrada_en: datetime | None = None
    movimientos: list[MovimientoCajaOut] = Field(default_factory=list)


# ---------------------------------------------------------------- cheques
class ChequeIn(BaseModel):
    tipo: Literal["emitido", "recibido"]
    banco: str | None = Field(default=None, max_length=80)
    numero: str | None = Field(default=None, max_length=40)
    monto: Decimal = Field(gt=0)
    fecha: date
    cliente_id: int | None = None       # recibido
    proveedor_id: int | None = None     # emitido
    beneficiario_id: int | None = None  # emitido
    documento_origen_tipo: Literal["venta", "orden_trabajo", "cobro_cxc"] | None = None
    documento_origen_id: int | None = None


class ChequeOut(BaseModel):
    id: int
    tipo: str
    banco: str | None = None
    numero: str | None = None
    monto: Decimal
    fecha: date
    estado: str
    cliente_id: int | None = None
    proveedor_id: int | None = None
    beneficiario_id: int | None = None
    documento_origen_tipo: str | None = None
    documento_origen_id: int | None = None


# ---------------------------------------------------------------- CxC
class CobroCxcIn(BaseModel):
    monto: Decimal = Field(gt=0)
    medio_pago: str = Field(min_length=1, max_length=20)
    fecha: date | None = None
    cheque: ChequeIn | None = None


class CxcOut(BaseModel):
    id: int
    origen_tipo: str
    origen_id: int
    cliente_id: int
    cliente_nombre: str | None = None
    monto_original: Decimal
    saldo: Decimal
    estado: str
    dias: int | None = None
    creado_en: datetime


class TramoAgingOut(BaseModel):
    tramo: str
    cantidad: int
    saldo: Decimal


class AgingOut(BaseModel):
    fecha_corte: date
    tramos: list[TramoAgingOut]
    total: Decimal


# ---------------------------------------------------------------- beneficiarios / CxP
class BeneficiarioIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=160)
    identificacion: str | None = Field(default=None, max_length=20)
    tipo_servicio: str | None = Field(default=None, max_length=60)


class BeneficiarioOut(BaseModel):
    id: int
    nombre: str
    identificacion: str | None = None
    tipo_servicio: str | None = None
    activo: bool


class RetencionIn(BaseModel):
    porcentaje: Decimal | None = None
    monto: Decimal = Field(ge=0)
    comprobante: str | None = None


class PagoCxpIn(BaseModel):
    monto: Decimal = Field(gt=0)
    medio_pago: str = Field(min_length=1, max_length=20)
    fecha: date | None = None
    retencion: RetencionIn | None = None
    cheque: ChequeIn | None = None


class CxpOut(BaseModel):
    id: int
    origen_tipo: str
    orden_compra_id: int | None = None
    gasto_id: int | None = None
    proveedor_id: int | None = None
    proveedor_nombre: str | None = None
    beneficiario_id: int | None = None
    beneficiario_nombre: str | None = None
    monto_original: Decimal
    saldo: Decimal
    estado: str
    dias: int | None = None
    creado_en: datetime


# ---------------------------------------------------------------- gastos
class GastoIn(BaseModel):
    sucursal_id: int
    categoria_gasto_id: int
    monto: Decimal = Field(gt=0)
    fecha: date
    descripcion: str | None = Field(default=None, max_length=255)
    estado_pago: EstadoPago
    medio_pago: str | None = None          # requerido si pagado
    proveedor_id: int | None = None        # si por_pagar
    beneficiario_id: int | None = None     # si por_pagar


class ConfirmarGastoIn(BaseModel):
    monto: Decimal | None = Field(default=None, gt=0)
    estado_pago: EstadoPago
    medio_pago: str | None = None
    proveedor_id: int | None = None
    beneficiario_id: int | None = None


class GastoOut(BaseModel):
    id: int
    sucursal_id: int
    sucursal_nombre: str | None = None
    categoria_gasto_id: int
    categoria_nombre: str | None = None
    categoria_tipo: str | None = None
    proveedor_id: int | None = None
    beneficiario_id: int | None = None
    contraparte_nombre: str | None = None
    monto: Decimal
    fecha: date
    descripcion: str | None = None
    documento_soporte_url: str | None = None
    estado_pago: str | None = None
    estado: str
    gasto_recurrente_id: int | None = None
    cuenta_por_pagar_id: int | None = None
    movimiento_caja_id: int | None = None
    asiento_id: int | None = None
    creado_en: datetime


class GastoRecurrenteIn(BaseModel):
    categoria_gasto_id: int
    sucursal_id: int
    proveedor_id: int | None = None
    beneficiario_id: int | None = None
    descripcion: str = Field(min_length=2, max_length=160)
    monto_estimado: Decimal = Field(gt=0)
    frecuencia: Frecuencia
    proxima_generacion: date | None = None


class EstadoGastoRecurrenteIn(BaseModel):
    estado: Literal["activo", "pausado", "cancelado"]


class GastoRecurrenteOut(BaseModel):
    id: int
    categoria_gasto_id: int
    categoria_nombre: str | None = None
    sucursal_id: int
    sucursal_nombre: str | None = None
    proveedor_id: int | None = None
    beneficiario_id: int | None = None
    contraparte_nombre: str | None = None
    descripcion: str
    monto_estimado: Decimal
    frecuencia: str
    proxima_generacion: date
    estado: str


# ---------------------------------------------------------------- reglas de asiento
class ReglaAsientoIn(BaseModel):
    evento: str
    cuenta_debe_codigo: str
    cuenta_haber_codigo: str
    condicion: dict | None = None
    activa: bool = True


class ReglaAsientoOut(BaseModel):
    id: int
    evento: str
    cuenta_debe_codigo: str
    cuenta_haber_codigo: str
    condicion: dict | None = None
    activa: bool


# ---------------------------------------------------------------- periodo / rentabilidad
class PeriodoIn(BaseModel):
    fecha_inicio: date
    fecha_fin: date


class PeriodoOut(BaseModel):
    id: int
    fecha_inicio: date
    fecha_fin: date
    estado: str
    cerrado_en: datetime | None = None


class RentabilidadSucursalOut(BaseModel):
    sucursal_id: int
    sucursal_nombre: str | None = None
    ingresos: Decimal
    costos: Decimal
    gastos_operativos: Decimal
    utilidad_neta: Decimal
