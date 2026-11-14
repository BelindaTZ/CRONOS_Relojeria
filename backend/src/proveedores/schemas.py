from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TipoProveedor = Literal[
    "relojes", "piezas_originales", "piezas_no_originales", "lubricantes", "herramientas"
]
ItemTipo = Literal["reloj", "pieza"]
Frecuencia = Literal["semanal", "mensual", "trimestral"]


# --------------------------------------------------------------------- proveedor
class ProveedorIn(BaseModel):
    razon_social: str = Field(min_length=2, max_length=200)
    nombre_comercial: str | None = Field(default=None, max_length=200)
    contacto_nombre: str | None = Field(default=None, max_length=160)
    telefono: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)
    ruc_nit: str | None = Field(default=None, max_length=20)
    certificacion_autorizada: bool = False
    marcas_autorizadas: list[int] = Field(default_factory=list)  # ids de marca_reloj
    condicion_pago_id: int | None = None
    plazo_entrega_dias: int | None = Field(default=None, ge=0)  # legado — ya no se pide en el alta
    tipos: list[TipoProveedor] = Field(default_factory=list)


class ProveedorPatch(BaseModel):
    razon_social: str | None = Field(default=None, max_length=200)   # rol elevado
    ruc_nit: str | None = Field(default=None, max_length=20)         # rol elevado
    nombre_comercial: str | None = None
    contacto_nombre: str | None = None
    telefono: str | None = None
    email: str | None = None
    condicion_pago_id: int | None = None
    certificacion_autorizada: bool | None = None
    marcas_autorizadas: list[int] | None = None
    plazo_entrega_dias: int | None = Field(default=None, ge=0)
    tipos: list[TipoProveedor] | None = None


class CalificacionOut(BaseModel):
    nota_plazos: Decimal | None = None
    nota_calidad: Decimal | None = None
    nota_soporte: Decimal | None = None
    nota_agregada: Decimal | None = None
    creado_en: datetime


class ProveedorOut(BaseModel):
    id: int
    razon_social: str
    nombre_comercial: str | None = None
    contacto_nombre: str | None = None
    telefono: str | None = None
    email: str | None = None
    ruc_nit: str | None = None
    certificacion_autorizada: bool
    marcas_autorizadas: list[int] = Field(default_factory=list)
    marcas_autorizadas_nombres: list[str] = Field(default_factory=list)
    condicion_pago_id: int | None = None
    condicion_pago: str | None = None
    plazo_entrega_dias: int | None = None
    indicador_plazos_dias: Decimal | None = None
    estado: str
    tipos: list[str] = Field(default_factory=list)


class ProveedorDetalle(ProveedorOut):
    calificacion_vigente: CalificacionOut | None = None
    historial_compras: list["OrdenCompraOut"] = Field(default_factory=list)


class DocumentoOut(BaseModel):
    id: int
    tipo: str
    nombre: str | None = None
    url: str


class CalificacionIn(BaseModel):
    nota_calidad: Decimal | None = Field(default=None, ge=1, le=5)
    nota_soporte: Decimal | None = Field(default=None, ge=1, le=5)


# ---------------------------------------------------------------- órdenes de compra
UnidadMedida = Literal["unidad", "ml", "g", "mm", "par", "juego", "metro", "litro"]


class LineaIn(BaseModel):
    item_tipo: ItemTipo
    item_ref: str = Field(min_length=1, max_length=80, description="referencia/modelo (reloj) o código (pieza)")
    # --- reloj ---
    marca: str | None = Field(default=None, max_length=120)
    calibre_codigo: str | None = Field(default=None, max_length=60)
    anio: int | None = Field(default=None, ge=1900, le=2100)
    numero_serie: str | None = Field(default=None, max_length=80, description="reloj: si ya se conoce al pedir")
    # --- pieza ---
    pieza_id: int | None = Field(default=None, description="pieza existente del catálogo")
    pieza_tipo: Literal["original", "no_original_equivalente"] | None = None
    unidad_medida: UnidadMedida | None = None
    marca_compatible: str | None = Field(default=None, max_length=255)
    # --- común ---
    descripcion: str | None = Field(default=None, max_length=255, description="reloj: observaciones · pieza nueva: nombre de la pieza")
    observaciones: str | None = Field(default=None, max_length=255, description="nota libre del pedido")
    cantidad: int = Field(gt=0)
    costo_unitario: Decimal | None = Field(default=None, ge=0, description="costo estimado; el real se informa al recibir")
    es_perecedero: bool = False


class LineaOut(LineaIn):
    id: int
    cantidad_recibida: int = 0
    costo_unitario_real: Decimal | None = None
    ultimo_costo_conocido: Decimal | None = None


class UltimoPrecioOut(BaseModel):
    costo: Decimal | None = None
    fecha: date | None = None
    fuente: str | None = None  # "recepcion" | "orden"


class OrdenCompraIn(BaseModel):
    proveedor_id: int
    sucursal_destino_id: int
    fecha_pactada: date | None = None
    condiciones_pago: str | None = None
    retencion_aplicable: dict | None = None
    urgente: bool = False
    lineas: list[LineaIn] = Field(min_length=1)


class OrdenCompraOut(BaseModel):
    id: int
    proveedor_id: int
    sucursal_destino_id: int
    tipo: str
    urgente: bool = False
    estado: str
    fecha_emision: date | None = None
    fecha_confirmacion: datetime | None = None
    fecha_pactada: date | None = None
    importe_a_pagar: Decimal | None = None
    condiciones_pago: str | None = None
    retencion_aplicable: dict | None = None
    numero_factura: str | None = None
    numero_guia: str | None = None
    lineas: list[LineaOut] = Field(default_factory=list)


class CancelarIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)


class RecepcionLineaIn(BaseModel):
    linea_orden_compra_id: int
    cantidad_recibida: int = Field(gt=0)
    costo_unitario: Decimal | None = Field(default=None, ge=0, description="costo real informado por el proveedor")
    lote: str | None = Field(default=None, max_length=60)
    fecha_caducidad: date | None = None


class RecepcionIn(BaseModel):
    fecha_real: date
    numero_factura: str | None = Field(default=None, max_length=60)
    numero_guia: str | None = Field(default=None, max_length=60)
    lineas: list[RecepcionLineaIn] = Field(min_length=1)


class CorreccionLinea(BaseModel):
    id: int
    cantidad: int | None = Field(default=None, gt=0)
    costo_unitario: Decimal | None = Field(default=None, ge=0)
    item_ref: str | None = None


class CorreccionIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)
    lineas: list[CorreccionLinea] = Field(default_factory=list)


class PrellenarIn(BaseModel):
    proveedor_id: int | None = None
    item_tipo: ItemTipo
    item_ref: str
    cantidad_sugerida: int = Field(gt=0)


class PrellenarOut(BaseModel):
    proveedor_id: int | None = None
    requiere_elegir_proveedor: bool = False
    sucursal_destino_id: int | None = None
    lineas: list[LineaIn]


# ---------------------------------------------------------------- compras programadas
class CompraProgramadaIn(BaseModel):
    proveedor_id: int
    sucursal_destino_id: int
    frecuencia: Frecuencia
    plantilla_lineas: list[LineaIn] = Field(min_length=1)
    proxima_generacion: datetime | None = None


class CompraProgramadaOut(BaseModel):
    id: int
    proveedor_id: int
    sucursal_destino_id: int
    frecuencia: str
    estado: str
    proxima_generacion: datetime
    plantilla_lineas: list


class EstadoIn(BaseModel):
    estado: Literal["activa", "pausada", "cancelada"]


ProveedorDetalle.model_rebuild()
