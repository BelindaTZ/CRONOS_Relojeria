"""Modelos ORM del módulo `lubricacion` (feature 008).

Esquema físico creado a mano por la migración `0020_servicio_tecnico`. Los
productos Moebius se vinculan opcionalmente a una `pieza` perecedera de 003 (el
insumo real en stock).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base

__all__ = [
    "ProductoMoebius",
    "FichaLubricacionCalibre",
    "PuntoLubricacion",
    "RegistroLubricacionOT",
]


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class ProductoMoebius(_PK, Base):
    __tablename__ = "producto_moebius"
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    uso_recomendado: Mapped[str | None] = mapped_column(String(255))
    pieza_id: Mapped[int | None] = mapped_column(ForeignKey("pieza.id", ondelete="SET NULL"))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class FichaLubricacionCalibre(_PK, Base):
    __tablename__ = "ficha_lubricacion_calibre"
    calibre_id: Mapped[int] = mapped_column(ForeignKey("calibre.id", ondelete="CASCADE"), unique=True)
    notas_generales: Mapped[str | None] = mapped_column(Text)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    puntos: Mapped[list[PuntoLubricacion]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan", lazy="selectin",
        order_by="PuntoLubricacion.orden",
    )


class PuntoLubricacion(_PK, Base):
    __tablename__ = "punto_lubricacion"
    ficha_lubricacion_calibre_id: Mapped[int] = mapped_column(
        ForeignKey("ficha_lubricacion_calibre.id", ondelete="CASCADE")
    )
    nombre: Mapped[str] = mapped_column(String(120))
    producto_moebius_id: Mapped[int | None] = mapped_column(
        ForeignKey("producto_moebius.id", ondelete="SET NULL")
    )
    notas: Mapped[str | None] = mapped_column(Text)
    orden: Mapped[int] = mapped_column(Integer, server_default="0")

    ficha: Mapped[FichaLubricacionCalibre] = relationship(back_populates="puntos")


class RegistroLubricacionOT(_PK, Base):
    """Registro por punto de la lubricación aplicada en una orden de trabajo (008).
    Append-only (trigger en DB): recomendado vs. realmente usado, con la marca de
    desviación. El consumo del insumo se descuenta del stock de piezas (003)."""

    __tablename__ = "registro_lubricacion_ot"
    orden_trabajo_id: Mapped[int] = mapped_column(ForeignKey("orden_trabajo.id", ondelete="CASCADE"))
    punto_lubricacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("punto_lubricacion.id", ondelete="SET NULL")
    )
    punto_nombre: Mapped[str] = mapped_column(String(120))
    producto_recomendado_id: Mapped[int | None] = mapped_column(
        ForeignKey("producto_moebius.id", ondelete="SET NULL")
    )
    producto_usado_id: Mapped[int] = mapped_column(ForeignKey("producto_moebius.id", ondelete="RESTRICT"))
    tecnico_id: Mapped[int | None] = mapped_column(ForeignKey("tecnico.id", ondelete="SET NULL"))
    desviacion: Mapped[bool] = mapped_column(Boolean, server_default="false")
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
