"""Modelos ORM del módulo `inventario` (feature 003): relojes, calibres, fotos,
documentos e historial inalterable por número de serie.

El esquema físico lo crea la migración `0009_inventario` a mano.
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


class Calibre(_PK, Base):
    __tablename__ = "calibre"
    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    marca: Mapped[str | None] = mapped_column(String(80))
    descripcion: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Reloj(_PK, Base):
    __tablename__ = "reloj"
    numero_serie: Mapped[str] = mapped_column(String(80), unique=True)
    marca: Mapped[str] = mapped_column(String(80))  # denormalizado desde marca_reloj (lo indexan las alertas)
    marca_id: Mapped[int | None] = mapped_column(ForeignKey("marca_reloj.id", ondelete="RESTRICT"))
    referencia: Mapped[str] = mapped_column(String(120))
    calibre_id: Mapped[int | None] = mapped_column(ForeignKey("calibre.id", ondelete="SET NULL"))
    anio_fabricacion: Mapped[int | None] = mapped_column(Integer)
    material_caja: Mapped[str | None] = mapped_column(String(120))  # legado
    material_brazalete: Mapped[str | None] = mapped_column(String(120))  # legado
    color_esfera: Mapped[str | None] = mapped_column(String(80))  # legado
    material_caja_id: Mapped[int | None] = mapped_column(ForeignKey("material.id", ondelete="SET NULL"))
    material_brazalete_id: Mapped[int | None] = mapped_column(ForeignKey("material.id", ondelete="SET NULL"))
    color_esfera_id: Mapped[int | None] = mapped_column(ForeignKey("color.id", ondelete="SET NULL"))
    tipo_cristal: Mapped[str | None] = mapped_column(String(40))
    resistencia_agua: Mapped[str | None] = mapped_column(String(40))
    estado_producto: Mapped[str] = mapped_column(String(10), server_default="nuevo")
    costo_adquisicion: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    precio_venta: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    fecha_ingreso: Mapped[date | None] = mapped_column(Date)
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id", ondelete="SET NULL"))
    recepcion_linea_id: Mapped[int | None] = mapped_column(
        ForeignKey("linea_orden_compra.id", ondelete="SET NULL")
    )
    full_set: Mapped[bool] = mapped_column(Boolean, server_default="false")
    full_set_detalle: Mapped[str | None] = mapped_column(String(255))
    sucursal_actual_id: Mapped[int | None] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    disponibilidad: Mapped[str] = mapped_column(String(14), server_default="disponible")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fotos: Mapped[list["FotoReloj"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="FotoReloj.orden"
    )
    documentos: Mapped[list["DocumentoReloj"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="DocumentoReloj.id"
    )


class FotoReloj(_PK, Base):
    __tablename__ = "foto_reloj"
    reloj_id: Mapped[int] = mapped_column(ForeignKey("reloj.id", ondelete="CASCADE"))
    objeto: Mapped[str] = mapped_column(String(255))
    orden: Mapped[int] = mapped_column(Integer, server_default="0")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentoReloj(_PK, Base):
    __tablename__ = "documento_reloj"
    reloj_id: Mapped[int] = mapped_column(ForeignKey("reloj.id", ondelete="CASCADE"))
    objeto: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(20), server_default="otro")
    nombre: Mapped[str | None] = mapped_column(String(200))
    subido_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventoSerie(_PK, Base):
    """Historial INALTERABLE por número de serie. Solo INSERT (trigger en DB)."""

    __tablename__ = "evento_serie"
    numero_serie: Mapped[str] = mapped_column(String(80))
    reloj_id: Mapped[int | None] = mapped_column(ForeignKey("reloj.id", ondelete="SET NULL"))
    tipo: Mapped[str] = mapped_column(String(14))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    documento_tipo: Mapped[str | None] = mapped_column(String(30))
    documento_id: Mapped[int | None] = mapped_column(BigInteger)
    detalle: Mapped[dict | None] = mapped_column(JSONB)
    actor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertaStock(_PK, Base):
    """Alerta materializada de stock (relojes de un modelo / pieza / lote).
    Recalculada tras cada movimiento; NO bloquea operaciones (FR-012)."""

    __tablename__ = "alerta_stock"
    ambito: Mapped[str] = mapped_column(String(10))  # modelo | pieza
    ref: Mapped[str] = mapped_column(String(200))  # "marca|referencia" o str(pieza_id)
    sucursal_id: Mapped[int | None] = mapped_column(ForeignKey("sucursal.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(10), server_default="abierta")
    detalle: Mapped[dict | None] = mapped_column(JSONB)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resuelto_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
