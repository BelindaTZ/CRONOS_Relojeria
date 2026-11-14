from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TipoCliente = Literal["natural", "juridica"]
EstadoCliente = Literal["activo", "inactivo"]
Criterio = Literal["monto_acumulado", "frecuencia", "combinacion"]
TipoValor = Literal["porcentaje", "monto"]
Alcance = Literal["producto", "marca", "tienda"]
Segmento = Literal["todos", "nivel", "cliente"]
LimiteUso = Literal["una_vez", "n_veces", "por_cliente", "global"]
Evento = Literal["cumpleanos", "aniversario_tienda"]
DocumentoTipo = Literal["venta", "orden_trabajo"]


# ---------------------------------------------------------------- consentimiento
class ConsentimientoIn(BaseModel):
    aceptado: bool
    version_texto: int


class TextoConsentimientoOut(BaseModel):
    version: int
    texto: str


# ------------------------------------------------------------------------ cliente
class ClienteIn(BaseModel):
    tipo: TipoCliente = "natural"
    identificacion: str = Field(min_length=3, max_length=20)
    nombre: str = Field(min_length=2, max_length=200)
    telefono: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)
    direccion: str | None = Field(default=None, max_length=255)
    fecha_nacimiento: date | None = None
    preferencias: dict | None = None
    notas: str | None = Field(default=None, max_length=4000)
    consentimiento: ConsentimientoIn


class ClientePatch(BaseModel):
    identificacion: str | None = Field(default=None, max_length=20)  # rol elevado
    tipo: TipoCliente | None = None
    nombre: str | None = Field(default=None, max_length=200)
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    fecha_nacimiento: date | None = None
    preferencias: dict | None = None
    notas: str | None = Field(default=None, max_length=4000)


class EstadoClienteIn(BaseModel):
    estado: EstadoCliente


class CuponMiniOut(BaseModel):
    id: int
    codigo: str
    tipo: str
    valor: Decimal
    alcance: str
    vigencia_fin: date | None = None
    estado: str


class ClienteOut(BaseModel):
    id: int
    tipo: str
    identificacion: str
    numero_afiliado: str
    nombre: str
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    fecha_nacimiento: date | None = None
    preferencias: dict | None = None
    notas: str | None = None
    nivel_fidelizacion_id: int | None = None
    nivel_nombre: str | None = None
    es_consumidor_final: bool = False
    estado: str
    creado_en: datetime


class ClienteDetalle(ClienteOut):
    cupones_activos: list[CuponMiniOut] = Field(default_factory=list)
    beneficios_nivel: dict | None = None
    consentimiento_vigente: ConsentimientoIn | None = None


# ------------------------------------------------------------------ historial
class MovimientoHistorialOut(BaseModel):
    tipo: str  # "compra" | "servicio" | "cita" | "cambio_nivel"
    fecha: datetime
    detalle: str
    monto: Decimal | None = None
    documento_id: int | None = None
    sucursal_id: int | None = None
    sucursal_nombre: str | None = None


class HistorialClienteOut(BaseModel):
    cliente_id: int
    total_compras: Decimal = Decimal("0")
    total_servicios: Decimal = Decimal("0")
    movimientos: list[MovimientoHistorialOut] = Field(default_factory=list)
    cambios_nivel: list[dict] = Field(default_factory=list)


# --------------------------------------------------------------- niveles
class ReglaNivelIn(BaseModel):
    criterio: Criterio = "monto_acumulado"
    ventana_meses: int = Field(default=12, ge=1, le=120)
    umbral_monto: Decimal | None = Field(default=None, ge=0)
    umbral_frecuencia: int | None = Field(default=None, ge=0)


class NivelIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    orden: int = Field(ge=1)
    beneficios: dict = Field(default_factory=dict)
    es_base: bool = False
    regla: ReglaNivelIn | None = None


class ReglaNivelOut(ReglaNivelIn):
    id: int
    vigente_desde: date


class NivelOut(BaseModel):
    id: int
    nombre: str
    orden: int
    beneficios: dict | None = None
    es_base: bool
    activo: bool
    regla_vigente: ReglaNivelOut | None = None
    clientes: int = 0


class RecalcularNivelIn(BaseModel):
    cliente_id: int
    hecho: Literal["venta", "servicio"]
    documento_id: int | None = None


class RecalcularNivelOut(BaseModel):
    cliente_id: int
    nivel_anterior: str | None = None
    nivel_nuevo: str | None = None
    cambio: bool = False


# --------------------------------------------------------------- descuentos
class DescuentoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    tipo: TipoValor
    valor: Decimal = Field(gt=0)
    alcance: Alcance = "tienda"
    alcance_ref: str | None = Field(default=None, max_length=80)
    segmento: Segmento = "todos"
    segmento_ref: str | None = Field(default=None, max_length=80)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None
    evento: Evento | None = None
    limite_uso: LimiteUso = "global"
    max_usos: int | None = Field(default=None, ge=1)


class DescuentoPatch(BaseModel):
    nombre: str | None = None
    valor: Decimal | None = Field(default=None, gt=0)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None
    estado: Literal["activo", "inactivo"] | None = None


class DescuentoOut(DescuentoIn):
    id: int
    usos: int = 0
    estado: str


# --------------------------------------------------------------- cupones
class CuponIn(BaseModel):
    codigo: str = Field(min_length=3, max_length=24)
    cliente_id: int
    tipo: TipoValor
    valor: Decimal = Field(gt=0)
    alcance: Alcance = "tienda"
    alcance_ref: str | None = Field(default=None, max_length=80)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None
    evento: Evento | None = None
    limite_uso: LimiteUso = "una_vez"
    max_usos: int | None = Field(default=None, ge=1)


class CuponOut(CuponIn):
    id: int
    usos: int = 0
    estado: str
    cliente_nombre: str | None = None


class ConsumirCuponIn(BaseModel):
    codigo: str
    documento_tipo: DocumentoTipo
    documento_id: int


# --------------------------------------------------------------- margen mínimo
class MargenMinimoIn(BaseModel):
    tipo: Literal["porcentaje_costo", "monto"] = "porcentaje_costo"
    valor: Decimal = Field(ge=0)
    ambito: Literal["global", "marca", "producto"] = "global"
    ref: str | None = Field(default=None, max_length=80)
    politica: Literal["bloquear", "autorizar"] | None = None


class MargenMinimoOut(BaseModel):
    tipo: str
    valor: Decimal
    ambito: str
    ref: str | None = None
    politica: str


class DescuentoAplicableIn(BaseModel):
    tipo: TipoValor
    valor: Decimal


class AplicarDescuentoIn(BaseModel):
    item_ref: str
    marca: str | None = None
    costo: Decimal = Field(ge=0)
    precio_lista: Decimal = Field(ge=0)
    cliente_id: int | None = None
    descuento: DescuentoAplicableIn | None = None
    cupon: DescuentoAplicableIn | None = None


class AplicarDescuentoOut(BaseModel):
    precio_final: Decimal
    monto_descontado: Decimal
    margen_resultante: Decimal
    decision: Literal["permitir", "bloquear", "requiere_autorizacion"]
    margen_minimo_aplicado: MargenMinimoOut


class AutorizarMargenIn(BaseModel):
    documento_tipo: DocumentoTipo
    documento_id: int
    motivo: str = Field(min_length=3, max_length=255)
    margen_resultante: Decimal | None = None


# --------------------------------------------------------------- reportes
class ClientesPorNivelOut(BaseModel):
    nivel_id: int | None = None
    nivel_nombre: str
    clientes: int


class MejorClienteOut(BaseModel):
    cliente_id: int
    nombre: str
    numero_afiliado: str
    total_compras: Decimal
    total_servicios: Decimal
    total: Decimal


class ClienteEnRiesgoOut(BaseModel):
    cliente_id: int
    nombre: str
    numero_afiliado: str
    nivel_nombre: str | None = None
    ultima_compra: date
    dias_silencio: int
    cadencia_dias: float
    ratio: float
    severidad: str  # "atencion" | "critico"
    transacciones: int


class CuponReactivacionIn(BaseModel):
    cliente_id: int
    codigo: str | None = None      # si no se da, se autogenera REACT-<afiliado>
    tipo: TipoValor = "porcentaje"
    valor: Decimal = Field(gt=0)
    vigencia_fin: date | None = None
