from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TipoCristal = Literal["zafiro", "mineral", "acrilico", "otro"]
EstadoProducto = Literal["nuevo", "usado"]
Disponibilidad = Literal[
    "disponible", "reservado", "en_transito", "vendido", "en_servicio", "dado_de_baja"
]
TipoEventoSerie = Literal[
    "ingreso", "venta", "servicio", "transferencia", "baja", "reingreso", "correccion"
]


# ------------------------------------------------------------------- calibre
class CalibreIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=60)
    marca: str | None = Field(default=None, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)


class CalibreOut(BaseModel):
    id: int
    codigo: str
    marca: str | None = None
    descripcion: str | None = None
    relojes: int = 0


# --------------------------------------------------------------------- reloj
class RelojIn(BaseModel):
    numero_serie: str = Field(min_length=1, max_length=80)
    # marca / materiales / color: envía el `_id` del catálogo, o el nombre en texto
    # (el backend lo busca-o-crea en el catálogo correspondiente).
    marca_id: int | None = None
    marca: str | None = Field(default=None, max_length=120)
    referencia: str = Field(min_length=1, max_length=120)
    calibre_id: int | None = None
    anio_fabricacion: int | None = Field(default=None, ge=1900, le=2100)
    material_caja_id: int | None = None
    material_caja: str | None = Field(default=None, max_length=120)
    material_brazalete_id: int | None = None
    material_brazalete: str | None = Field(default=None, max_length=120)
    color_esfera_id: int | None = None
    color_esfera: str | None = Field(default=None, max_length=80)
    tipo_cristal: TipoCristal | None = None
    resistencia_agua: str | None = Field(default=None, max_length=40)
    estado_producto: EstadoProducto = "nuevo"
    costo_adquisicion: Decimal | None = Field(default=None, ge=0)
    precio_venta: Decimal | None = Field(default=None, ge=0)
    fecha_ingreso: date | None = None
    proveedor_id: int | None = None
    recepcion_linea_id: int | None = None
    motivo_alta_manual: str | None = Field(default=None, max_length=255)
    full_set: bool = False
    full_set_detalle: str | None = Field(default=None, max_length=255)
    sucursal_actual_id: int | None = None


class RelojPatch(BaseModel):
    """Corrección de ficha (rol elevado). `motivo` obligatorio."""

    motivo: str = Field(min_length=5, max_length=500)
    numero_serie: str | None = Field(default=None, max_length=80)
    marca_id: int | None = None
    marca: str | None = Field(default=None, max_length=120)
    referencia: str | None = Field(default=None, max_length=120)
    calibre_id: int | None = None
    anio_fabricacion: int | None = None
    material_caja_id: int | None = None
    material_brazalete_id: int | None = None
    color_esfera_id: int | None = None
    tipo_cristal: TipoCristal | None = None
    resistencia_agua: str | None = None
    estado_producto: EstadoProducto | None = None
    costo_adquisicion: Decimal | None = Field(default=None, ge=0)
    precio_venta: Decimal | None = Field(default=None, ge=0)
    fecha_ingreso: date | None = None
    proveedor_id: int | None = None
    full_set: bool | None = None
    full_set_detalle: str | None = None
    sucursal_actual_id: int | None = None


class FotoOut(BaseModel):
    id: int
    orden: int
    url: str


class DocumentoRelojOut(BaseModel):
    id: int
    tipo: str
    nombre: str | None = None
    url: str


class DisponibilidadGlobalOut(BaseModel):
    id: int
    numero_serie: str
    marca: str
    referencia: str
    calibre_codigo: str | None = None
    tipo_cristal: str | None = None
    precio_venta: Decimal | None = None
    sucursal_id: int
    sucursal_nombre: str


class RelojOut(BaseModel):
    id: int
    numero_serie: str
    marca: str
    marca_id: int | None = None
    referencia: str
    calibre_id: int | None = None
    calibre_codigo: str | None = None
    anio_fabricacion: int | None = None
    material_caja: str | None = None  # etiqueta resuelta del catálogo
    material_caja_id: int | None = None
    material_brazalete: str | None = None
    material_brazalete_id: int | None = None
    color_esfera: str | None = None  # etiqueta resuelta del catálogo
    color_esfera_id: int | None = None
    color_esfera_hex: str | None = None
    tipo_cristal: str | None = None
    resistencia_agua: str | None = None
    estado_producto: str
    costos_visibles: bool = True  # False = el rol no puede ver costo/margen
    costo_adquisicion: Decimal | None = None
    precio_venta: Decimal | None = None
    margen: Decimal | None = None
    fecha_ingreso: date | None = None
    proveedor_id: int | None = None
    recepcion_linea_id: int | None = None
    full_set: bool
    full_set_detalle: str | None = None
    sucursal_actual_id: int | None = None
    disponibilidad: str
    creado_en: datetime
    foto_url: str | None = None  # primera foto (orden más bajo), si existe


class RelojDetalle(RelojOut):
    fotos: list[FotoOut] = Field(default_factory=list)
    documentos: list[DocumentoRelojOut] = Field(default_factory=list)


class EventoSerieOut(BaseModel):
    tipo: str
    fecha: datetime
    documento_tipo: str | None = None
    documento_id: int | None = None
    detalle: dict | None = None


# ------------------------------------------------------------- alertas / valor
class AccionReponer(BaseModel):
    item_tipo: Literal["reloj", "pieza"]
    item_ref: str
    marca: str | None = None
    cantidad_sugerida: int
    proveedor_id: int | None = None


class AlertaStockOut(BaseModel):
    id: int
    ambito: str
    ref: str
    etiqueta: str
    sucursal_id: int | None = None
    tipo: str
    detalle: dict | None = None
    creado_en: datetime
    accion_reponer: AccionReponer | None = None


class ValorInventarioOut(BaseModel):
    unidades: int
    a_precio_venta: Decimal
    a_costo: Decimal | None = None  # solo con ver_costos
    por_sucursal: list[dict] = Field(default_factory=list)


class LineaRecepcionPendienteOut(BaseModel):
    """Línea de recepción de compra (002) de tipo reloj con unidades aún sin fichar."""

    recepcion_linea_id: int
    orden_compra_id: int
    proveedor_id: int
    sucursal_destino_id: int
    item_ref: str
    marca: str | None = None
    calibre_codigo: str | None = None
    anio: int | None = None
    numero_serie: str | None = None
    descripcion: str | None = None
    recibidas: int
    fichadas: int
    pendientes: int
    costo_unitario: Decimal | None = None
