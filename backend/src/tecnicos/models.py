"""Modelos ORM del módulo `tecnicos` (feature 005).

El esquema físico lo crea la migración `0016_tecnicos` a mano. Reutiliza
`usuario`/`sucursal` (001) y `parametro_configuracion` (001) solo por FK / lectura.
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


class Especialidad(_PK, Base):
    __tablename__ = "especialidad"
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Tecnico(_PK, Base):
    __tablename__ = "tecnico"
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), unique=True)
    nombre: Mapped[str] = mapped_column(String(160))
    certificaciones: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), server_default="activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    especialidades: Mapped[list["TecnicoEspecialidad"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    sucursales: Mapped[list["TecnicoSucursal"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class TecnicoEspecialidad(_PK, Base):
    __tablename__ = "tecnico_especialidad"
    tecnico_id: Mapped[int] = mapped_column(ForeignKey("tecnico.id", ondelete="CASCADE"))
    especialidad_id: Mapped[int] = mapped_column(ForeignKey("especialidad.id", ondelete="RESTRICT"))


class TecnicoSucursal(_PK, Base):
    __tablename__ = "tecnico_sucursal"
    tecnico_id: Mapped[int] = mapped_column(ForeignKey("tecnico.id", ondelete="CASCADE"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))


class EsquemaCostoManoObra(_PK, Base):
    __tablename__ = "esquema_costo_mano_obra"
    tecnico_id: Mapped[int] = mapped_column(ForeignKey("tecnico.id", ondelete="CASCADE"))
    sueldo_mensual: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    vigente_desde: Mapped[date] = mapped_column(Date)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReglaBono(_PK, Base):
    __tablename__ = "regla_bono"
    nombre: Mapped[str] = mapped_column(String(120))
    periodicidad: Mapped[str] = mapped_column(String(10))
    vigente_desde: Mapped[date] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    componentes: Mapped[list["ComponenteBono"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ComponenteBono.id"
    )


class ComponenteBono(_PK, Base):
    __tablename__ = "componente_bono"
    regla_bono_id: Mapped[int] = mapped_column(ForeignKey("regla_bono.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(20))
    indicador: Mapped[str] = mapped_column(String(24))
    umbral: Mapped[Decimal] = mapped_column(Numeric(14, 4), server_default="0")
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 4))


class PeriodoLiquidacion(_PK, Base):
    __tablename__ = "periodo_liquidacion"
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(10), server_default="abierto")
    cerrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BonoAcumulado(_PK, Base):
    __tablename__ = "bono_acumulado"
    tecnico_id: Mapped[int] = mapped_column(ForeignKey("tecnico.id", ondelete="CASCADE"))
    periodo_liquidacion_id: Mapped[int] = mapped_column(
        ForeignKey("periodo_liquidacion.id", ondelete="CASCADE")
    )
    regla_bono_id: Mapped[int | None] = mapped_column(ForeignKey("regla_bono.id", ondelete="SET NULL"))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    desglose: Mapped[dict | None] = mapped_column(JSONB)
    estado: Mapped[str] = mapped_column(String(10), server_default="preliminar")
    calculado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ots: Mapped[list["BonoOt"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class BonoOt(_PK, Base):
    __tablename__ = "bono_ot"
    bono_acumulado_id: Mapped[int] = mapped_column(ForeignKey("bono_acumulado.id", ondelete="CASCADE"))
    orden_trabajo_id: Mapped[int] = mapped_column(BigInteger)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
