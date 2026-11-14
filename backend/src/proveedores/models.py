"""Modelos ORM del módulo `proveedores` (feature 002).

Modelos de dominio del módulo — no van en `shared/models.py` (eso es solo el
sustrato central identidad/RBAC/config/auditoría). El esquema físico lo crea la
migración `0007_proveedores` a mano.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class Proveedor(_PK, Base):
    __tablename__ = "proveedor"
    razon_social: Mapped[str] = mapped_column(String(200))
    nombre_comercial: Mapped[str | None] = mapped_column(String(200))
    contacto_nombre: Mapped[str | None] = mapped_column(String(160))
    telefono: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    ruc_nit: Mapped[str | None] = mapped_column(String(20), unique=True)
    certificacion_autorizada: Mapped[bool] = mapped_column(Boolean, server_default="false")
    condiciones_pago: Mapped[str | None] = mapped_column(String(255))  # legado (usar condicion_pago_id)
    condicion_pago_id: Mapped[int | None] = mapped_column(
        ForeignKey("condicion_pago.id", ondelete="SET NULL")
    )
    plazo_entrega_dias: Mapped[int | None] = mapped_column(Integer)
    indicador_plazos_dias: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    estado: Mapped[str] = mapped_column(String(12), server_default="activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tipos: Mapped[list["ProveedorTipo"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class ProveedorTipo(_PK, Base):
    __tablename__ = "proveedor_tipo"
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(24))


class ProveedorDocumento(_PK, Base):
    __tablename__ = "proveedor_documento"
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(16), server_default="otro")
    objeto: Mapped[str] = mapped_column(String(255))
    nombre: Mapped[str | None] = mapped_column(String(200))
    subido_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CalificacionProveedor(_PK, Base):
    __tablename__ = "calificacion_proveedor"
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id", ondelete="CASCADE"))
    nota_plazos: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    nota_calidad: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    nota_soporte: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    nota_agregada: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    autor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompraProgramada(_PK, Base):
    __tablename__ = "compra_programada"
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id", ondelete="CASCADE"))
    sucursal_destino_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    frecuencia: Mapped[str] = mapped_column(String(12))
    proxima_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(10), server_default="activa")
    plantilla_lineas: Mapped[list] = mapped_column(JSONB)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrdenCompra(_PK, Base):
    __tablename__ = "orden_compra"
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id", ondelete="RESTRICT"))
    sucursal_destino_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    tipo: Mapped[str] = mapped_column(String(12), server_default="puntual")
    urgente: Mapped[bool] = mapped_column(Boolean, server_default="false")
    compra_programada_id: Mapped[int | None] = mapped_column(
        ForeignKey("compra_programada.id", ondelete="SET NULL")
    )
    estado: Mapped[str] = mapped_column(String(14), server_default="borrador")
    fecha_emision: Mapped[date | None] = mapped_column(Date)
    fecha_confirmacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmada_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    fecha_pactada: Mapped[date | None] = mapped_column(Date)
    importe_a_pagar: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    condiciones_pago: Mapped[str | None] = mapped_column(String(255))
    retencion_aplicable: Mapped[dict | None] = mapped_column(JSONB)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lineas: Mapped[list["LineaOrdenCompra"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="LineaOrdenCompra.id"
    )


class LineaOrdenCompra(_PK, Base):
    __tablename__ = "linea_orden_compra"
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.id", ondelete="CASCADE"))
    item_tipo: Mapped[str] = mapped_column(String(8))
    item_ref: Mapped[str] = mapped_column(String(80))          # referencia/modelo (reloj) o código (pieza)
    marca: Mapped[str | None] = mapped_column(String(120))     # solo relojes: marca del reloj
    calibre_codigo: Mapped[str | None] = mapped_column(String(60))
    anio: Mapped[int | None] = mapped_column(Integer)
    numero_serie: Mapped[str | None] = mapped_column(String(80))  # reloj: si ya se conoce al pedir
    pieza_id: Mapped[int | None] = mapped_column(ForeignKey("pieza.id", ondelete="SET NULL"))  # pieza del catálogo
    pieza_tipo: Mapped[str | None] = mapped_column(String(24))    # pieza nueva: original | no_original_equivalente
    unidad_medida: Mapped[str | None] = mapped_column(String(16))  # unidad, ml, g, par…
    marca_compatible: Mapped[str | None] = mapped_column(String(255))  # pieza: marcas de reloj compatibles
    descripcion: Mapped[str | None] = mapped_column(String(255))  # reloj: observaciones · pieza nueva: nombre/descripción
    observaciones: Mapped[str | None] = mapped_column(String(255))  # nota libre del pedido (independiente de descripcion)
    cantidad: Mapped[int] = mapped_column(Integer)
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))  # estimado; el real va en la recepción
    es_perecedero: Mapped[bool] = mapped_column(Boolean, server_default="false")


class RecepcionCompra(_PK, Base):
    __tablename__ = "recepcion_compra"
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.id", ondelete="CASCADE"))
    fecha_real: Mapped[date] = mapped_column(Date)
    responsable_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL")
    )
    desfase_dias: Mapped[int | None] = mapped_column(Integer)
    numero_factura: Mapped[str | None] = mapped_column(String(60))
    numero_guia: Mapped[str | None] = mapped_column(String(60))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lineas: Mapped[list["RecepcionLinea"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class RecepcionLinea(_PK, Base):
    __tablename__ = "recepcion_linea"
    recepcion_compra_id: Mapped[int] = mapped_column(
        ForeignKey("recepcion_compra.id", ondelete="CASCADE")
    )
    linea_orden_compra_id: Mapped[int] = mapped_column(
        ForeignKey("linea_orden_compra.id", ondelete="RESTRICT")
    )
    cantidad_recibida: Mapped[int] = mapped_column(Integer)
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))  # costo real informado por el proveedor
    lote: Mapped[str | None] = mapped_column(String(60))
    fecha_caducidad: Mapped[date | None] = mapped_column(Date)
    sobre_entrega: Mapped[bool] = mapped_column(Boolean, server_default="false")


class ProveedorMarcaAutorizada(_PK, Base):
    __tablename__ = "proveedor_marca_autorizada"
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id", ondelete="CASCADE"))
    marca_id: Mapped[int] = mapped_column(ForeignKey("marca_reloj.id", ondelete="CASCADE"))
