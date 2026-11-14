"""Modelos ORM del módulo `citas` (feature 007).

Esquema físico creado a mano por la migración `0019_citas`. Reutiliza
`cliente` (006), `sucursal`, `canal_cita`, `usuario` (001) solo por FK.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class Cita(_PK, Base):
    __tablename__ = "cita"
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="RESTRICT"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    canal_cita_id: Mapped[int] = mapped_column(ForeignKey("canal_cita.id", ondelete="RESTRICT"))
    motivo: Mapped[str] = mapped_column(String(16))
    fecha_preferida: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_confirmada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(12), server_default="pendiente")
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(255))
    observaciones: Mapped[str | None] = mapped_column(Text)
    venta_id: Mapped[int | None] = mapped_column(BigInteger)             # 009
    orden_trabajo_id: Mapped[int | None] = mapped_column(BigInteger)     # 008
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistorialEstadoCita(_PK, Base):
    __tablename__ = "historial_estado_cita"
    cita_id: Mapped[int] = mapped_column(ForeignKey("cita.id", ondelete="CASCADE"))
    estado: Mapped[str] = mapped_column(String(12))
    actor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    motivo: Mapped[str | None] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
