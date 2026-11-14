"""Modelos ORM del módulo `piezas` (feature 003): repuestos e insumos, stock por
sucursal (invariante ≥ 0), lotes/caducidad y libro de movimientos append-only.

El esquema físico lo crea la migración `0009_inventario` a mano. `calibre` es del
módulo `inventario`; aquí solo se referencia por FK (tabla `pieza_calibre`).
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class Pieza(_PK, Base):
    __tablename__ = "pieza"
    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    descripcion: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(24), server_default="original")
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id", ondelete="SET NULL"))
    costo_adquisicion: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    precio_venta_suelta: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    stock_minimo: Mapped[int] = mapped_column(Integer, server_default="0")
    unidad_medida: Mapped[str] = mapped_column(String(16), server_default="unidad")
    marca_compatible: Mapped[str | None] = mapped_column(String(255))
    perecedera: Mapped[bool] = mapped_column(Boolean, server_default="false")
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    calibres: Mapped[list["PiezaCalibre"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class PiezaCalibre(_PK, Base):
    __tablename__ = "pieza_calibre"
    pieza_id: Mapped[int] = mapped_column(ForeignKey("pieza.id", ondelete="CASCADE"))
    calibre_id: Mapped[int] = mapped_column(ForeignKey("calibre.id", ondelete="CASCADE"))


class StockPieza(_PK, Base):
    __tablename__ = "stock_pieza"
    pieza_id: Mapped[int] = mapped_column(ForeignKey("pieza.id", ondelete="CASCADE"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    stock_actual: Mapped[int] = mapped_column(Integer, server_default="0")


class LotePieza(_PK, Base):
    __tablename__ = "lote_pieza"
    pieza_id: Mapped[int] = mapped_column(ForeignKey("pieza.id", ondelete="CASCADE"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    numero_lote: Mapped[str] = mapped_column(String(60))
    fecha_caducidad: Mapped[date] = mapped_column(Date)
    cantidad: Mapped[int] = mapped_column(Integer, server_default="0")
    estado: Mapped[str] = mapped_column(String(16), server_default="vigente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MovimientoStockPieza(_PK, Base):
    """Libro de movimientos APPEND-ONLY (trigger en DB)."""

    __tablename__ = "movimiento_stock_pieza"
    pieza_id: Mapped[int] = mapped_column(ForeignKey("pieza.id", ondelete="CASCADE"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    tipo: Mapped[str] = mapped_column(String(24))
    cantidad: Mapped[int] = mapped_column(Integer)
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote_pieza.id", ondelete="SET NULL"))
    documento_tipo: Mapped[str | None] = mapped_column(String(30))
    documento_id: Mapped[int | None] = mapped_column(BigInteger)
    nota: Mapped[str | None] = mapped_column(String(255))
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
