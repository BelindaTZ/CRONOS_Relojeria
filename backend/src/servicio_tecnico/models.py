"""Modelos ORM del módulo `servicio_tecnico` (feature 008).

Esquema físico creado a mano por la migración `0020_servicio_tecnico`. Reutiliza
`reloj`, `pieza` (003); `tecnico` (005); `cliente`, `autorizacion_margen_minimo`
(006); `cita` (007); `usuario` (001) solo por FK.
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
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class OrdenTrabajo(_PK, Base):
    __tablename__ = "orden_trabajo"

    numero: Mapped[str] = mapped_column(String(20))
    reloj_id: Mapped[int] = mapped_column(ForeignKey("reloj.id", ondelete="RESTRICT"))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="RESTRICT"))
    tecnico_id: Mapped[int | None] = mapped_column(ForeignKey("tecnico.id", ondelete="SET NULL"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    cita_id: Mapped[int | None] = mapped_column(ForeignKey("cita.id", ondelete="SET NULL"))
    ot_original_id: Mapped[int | None] = mapped_column(ForeignKey("orden_trabajo.id", ondelete="SET NULL"))

    motivo: Mapped[str] = mapped_column(Text)
    diagnostico: Mapped[str | None] = mapped_column(Text)
    trabajo_realizado: Mapped[str | None] = mapped_column(Text)
    tipo_reparacion: Mapped[str] = mapped_column(String(40))
    horas_trabajadas: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    fecha_ingreso: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_estimada_entrega: Mapped[date | None] = mapped_column(Date)
    fecha_real_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    costo_interno: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    precio_cobrado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    margen_real: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    descuento_aplicado: Mapped[dict | None] = mapped_column(JSONB)

    garantia_periodo_dias: Mapped[int | None] = mapped_column(Integer)
    garantia_cobertura: Mapped[str | None] = mapped_column(String(255))

    estado: Mapped[str] = mapped_column(String(16), server_default="recibido")
    autorizacion_credito_id: Mapped[int | None] = mapped_column(
        ForeignKey("autorizacion_margen_minimo.id", ondelete="SET NULL")
    )
    adquirido_en_tienda_ok: Mapped[bool] = mapped_column(Boolean, server_default="false")
    override_adquisicion_motivo: Mapped[str | None] = mapped_column(String(255))
    reproceso: Mapped[bool] = mapped_column(Boolean, server_default="false")

    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    piezas: Mapped[list[PiezaUsadaOT]] = relationship(
        back_populates="orden", cascade="all, delete-orphan", lazy="selectin"
    )
    presupuestos: Mapped[list[Presupuesto]] = relationship(
        back_populates="orden", cascade="all, delete-orphan", lazy="selectin"
    )


class HistorialEstadoOT(_PK, Base):
    __tablename__ = "historial_estado_ot"
    orden_trabajo_id: Mapped[int] = mapped_column(ForeignKey("orden_trabajo.id", ondelete="CASCADE"))
    estado: Mapped[str] = mapped_column(String(16))
    actor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Presupuesto(_PK, Base):
    __tablename__ = "presupuesto"
    orden_trabajo_id: Mapped[int] = mapped_column(ForeignKey("orden_trabajo.id", ondelete="CASCADE"))
    precio_servicio: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    estado: Mapped[str] = mapped_column(String(12), server_default="borrador")
    confirmado_por: Mapped[str | None] = mapped_column(String(160))
    medio_confirmacion: Mapped[str | None] = mapped_column(String(40))
    fecha_confirmacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orden: Mapped[OrdenTrabajo] = relationship(back_populates="presupuestos")
    lineas: Mapped[list[PresupuestoLineaPieza]] = relationship(
        back_populates="presupuesto", cascade="all, delete-orphan", lazy="selectin"
    )


class PresupuestoLineaPieza(_PK, Base):
    __tablename__ = "presupuesto_linea_pieza"
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    pieza_original_id: Mapped[int] = mapped_column(ForeignKey("pieza.id", ondelete="RESTRICT"))
    pieza_no_original_id: Mapped[int | None] = mapped_column(ForeignKey("pieza.id", ondelete="RESTRICT"))
    precio_original: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    precio_no_original: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    preferencia_cliente: Mapped[str | None] = mapped_column(String(12))
    cantidad: Mapped[int] = mapped_column(Integer, server_default="1")

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="lineas")


class PiezaUsadaOT(_PK, Base):
    __tablename__ = "pieza_usada_ot"
    orden_trabajo_id: Mapped[int] = mapped_column(ForeignKey("orden_trabajo.id", ondelete="CASCADE"))
    pieza_id: Mapped[int] = mapped_column(ForeignKey("pieza.id", ondelete="RESTRICT"))
    tipo_elegido: Mapped[str] = mapped_column(String(12), server_default="original")
    cantidad: Mapped[int] = mapped_column(Integer, server_default="1")
    costo: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    lote_id: Mapped[int | None] = mapped_column(BigInteger)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orden: Mapped[OrdenTrabajo] = relationship(back_populates="piezas")


class DocumentoOT(_PK, Base):
    __tablename__ = "documento_ot"
    orden_trabajo_id: Mapped[int] = mapped_column(ForeignKey("orden_trabajo.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(24))
    objeto: Mapped[str] = mapped_column(String(255))
    generado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
