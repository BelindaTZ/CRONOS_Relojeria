"""Modelos ORM del módulo `mermas` (feature 011). El esquema físico lo crea la
migración `0025_mermas` a mano. Reutiliza `reloj`/`pieza`/`lote_pieza` (003),
`sucursal`/`usuario` (001), `tecnico` (005) y `proveedor` (002) solo por FK;
`orden_trabajo` (008), `transferencia` (004) y `asiento` (010) se referencian
por id crudo (constraint de BD, no import Python — Principio X)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, DateTime, Date, ForeignKey, Identity, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class Merma(_PK, Base):
    __tablename__ = "merma"

    numero: Mapped[str] = mapped_column(String(20))
    bien_tipo: Mapped[str] = mapped_column(String(8))
    reloj_id: Mapped[int | None] = mapped_column(ForeignKey("reloj.id", ondelete="RESTRICT"))
    pieza_id: Mapped[int | None] = mapped_column(ForeignKey("pieza.id", ondelete="RESTRICT"))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote_pieza.id", ondelete="SET NULL"))
    cantidad: Mapped[int] = mapped_column(Integer, server_default="1")
    causa: Mapped[str] = mapped_column(String(20))
    categoria_merma_id: Mapped[int | None] = mapped_column(ForeignKey("categoria_merma.id", ondelete="SET NULL"))
    descripcion: Mapped[str | None] = mapped_column(String(500))
    fecha_evento: Mapped[date] = mapped_column(Date)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    responsable_usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    costo_perdida: Mapped[float] = mapped_column(Numeric(14, 2))
    estado: Mapped[str] = mapped_column(String(24), server_default="en_evaluacion")
    orden_trabajo_id: Mapped[int | None] = mapped_column(BigInteger)
    tecnico_id: Mapped[int | None] = mapped_column(ForeignKey("tecnico.id", ondelete="SET NULL"))
    transferencia_id: Mapped[int | None] = mapped_column(BigInteger)
    autorizacion_baja_id: Mapped[int | None] = mapped_column(ForeignKey("autorizacion_baja.id", ondelete="SET NULL"))
    asiento_id: Mapped[int | None] = mapped_column(BigInteger)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documentos: Mapped[list["DocumentoSoporteMerma"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="DocumentoSoporteMerma.id"
    )
    reclamos: Mapped[list["ReclamoMerma"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ReclamoMerma.id"
    )
    historial: Mapped[list["HistorialEstadoMerma"]] = relationship(
        lazy="selectin", order_by="HistorialEstadoMerma.creado_en"
    )


class AutorizacionBaja(_PK, Base):
    __tablename__ = "autorizacion_baja"

    merma_id: Mapped[int] = mapped_column(ForeignKey("merma.id", ondelete="CASCADE"))
    autorizador_usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    observacion: Mapped[str | None] = mapped_column(String(255))


class DocumentoSoporteMerma(_PK, Base):
    __tablename__ = "documento_soporte_merma"

    merma_id: Mapped[int] = mapped_column(ForeignKey("merma.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(12))
    objeto: Mapped[str] = mapped_column(String(255))
    nombre: Mapped[str] = mapped_column(String(200))
    subido_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReclamoMerma(_PK, Base):
    __tablename__ = "reclamo_merma"

    merma_id: Mapped[int] = mapped_column(ForeignKey("merma.id", ondelete="CASCADE"))
    destino: Mapped[str] = mapped_column(String(12))
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id", ondelete="SET NULL"))
    aseguradora: Mapped[str | None] = mapped_column(String(120))
    estado: Mapped[str] = mapped_column(String(24), server_default="abierto")
    monto_recuperado: Mapped[float] = mapped_column(Numeric(14, 2), server_default="0")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistorialEstadoMerma(_PK, Base):
    """Append-only (trigger `cronos_append_only`, migración 0025)."""

    __tablename__ = "historial_estado_merma"

    merma_id: Mapped[int] = mapped_column(ForeignKey("merma.id", ondelete="CASCADE"))
    estado: Mapped[str] = mapped_column(String(24))
    actor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
