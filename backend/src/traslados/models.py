"""Modelos ORM del módulo `traslados` (feature 004): transferencias de relojes y
piezas entre sucursales.

El esquema físico lo crea la migración `0010_traslados` a mano. Reutiliza
`sucursal`/`usuario` (001) y `reloj`/`pieza` (003) solo por FK.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Identity, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class Transferencia(_PK, Base):
    __tablename__ = "transferencia"
    sucursal_origen_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    sucursal_destino_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    estado: Mapped[str] = mapped_column(String(16), server_default="en_preparacion")
    motivo: Mapped[str] = mapped_column(String(500))
    fecha_envio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_recepcion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responsable_envio_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    responsable_recepcion_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(500))
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lineas: Mapped[list["LineaTransferencia"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="LineaTransferencia.id"
    )


class LineaTransferencia(_PK, Base):
    __tablename__ = "linea_transferencia"
    transferencia_id: Mapped[int] = mapped_column(ForeignKey("transferencia.id", ondelete="CASCADE"))
    item_tipo: Mapped[str] = mapped_column(String(8))
    reloj_id: Mapped[int | None] = mapped_column(ForeignKey("reloj.id", ondelete="RESTRICT"))
    pieza_id: Mapped[int | None] = mapped_column(ForeignKey("pieza.id", ondelete="RESTRICT"))
    cantidad_enviada: Mapped[int] = mapped_column(Integer, server_default="1")
    cantidad_recibida: Mapped[int | None] = mapped_column(Integer)


class DiscrepanciaTransferencia(_PK, Base):
    __tablename__ = "discrepancia_transferencia"
    linea_transferencia_id: Mapped[int] = mapped_column(
        ForeignKey("linea_transferencia.id", ondelete="CASCADE")
    )
    cantidad_faltante: Mapped[int] = mapped_column(Integer)
    merma_id: Mapped[int | None] = mapped_column(BigInteger)
    resuelta: Mapped[bool] = mapped_column(Boolean, server_default="false")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
