"""Modelos ORM del módulo `contabilidad` (feature 010).

Esquema físico creado a mano por la migración `0023_contabilidad`. Reutiliza
`sucursal`, `categoria_gasto`, `medio_pago`, `usuario` (001); `cuenta_por_cobrar`
(009, por FK cruzada sin import); `orden_compra`, `proveedor` (002).
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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class CuentaContable(_PK, Base):
    __tablename__ = "cuenta_contable"
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(160))
    tipo: Mapped[str] = mapped_column(String(12))
    cuenta_padre_id: Mapped[int | None] = mapped_column(ForeignKey("cuenta_contable.id", ondelete="SET NULL"))
    imputable: Mapped[bool] = mapped_column(Boolean, server_default="true")
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")


class PeriodoContable(_PK, Base):
    __tablename__ = "periodo_contable"
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(10), server_default="abierto")
    cerrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Asiento(_PK, Base):
    __tablename__ = "asiento"
    fecha: Mapped[date] = mapped_column(Date)
    glosa: Mapped[str] = mapped_column(String(255))
    origen: Mapped[str] = mapped_column(String(24), server_default="manual")
    origen_id: Mapped[int | None] = mapped_column(BigInteger)
    ajuste_de_asiento_id: Mapped[int | None] = mapped_column(ForeignKey("asiento.id", ondelete="SET NULL"))
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lineas: Mapped[list["LineaAsiento"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="LineaAsiento.id"
    )


class LineaAsiento(_PK, Base):
    __tablename__ = "linea_asiento"
    asiento_id: Mapped[int] = mapped_column(ForeignKey("asiento.id", ondelete="CASCADE"))
    cuenta_contable_id: Mapped[int] = mapped_column(ForeignKey("cuenta_contable.id", ondelete="RESTRICT"))
    debe: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    haber: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")


class Caja(_PK, Base):
    __tablename__ = "caja"
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="CASCADE"), unique=True)
    nombre: Mapped[str] = mapped_column(String(80), server_default="Caja principal")


class SesionCaja(_PK, Base):
    __tablename__ = "sesion_caja"
    caja_id: Mapped[int] = mapped_column(ForeignKey("caja.id", ondelete="CASCADE"))
    abierta_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    abierta_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cerrada_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    efectivo_contado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    efectivo_esperado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    diferencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(10), server_default="abierta")


class MovimientoCaja(_PK, Base):
    __tablename__ = "movimiento_caja"
    sesion_caja_id: Mapped[int] = mapped_column(ForeignKey("sesion_caja.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(10))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    medio_pago_id: Mapped[int | None] = mapped_column(ForeignKey("medio_pago.id", ondelete="SET NULL"))
    documento_tipo: Mapped[str | None] = mapped_column(String(24))
    documento_id: Mapped[int | None] = mapped_column(BigInteger)
    nota: Mapped[str | None] = mapped_column(String(255))
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Beneficiario(_PK, Base):
    __tablename__ = "beneficiario"
    nombre: Mapped[str] = mapped_column(String(160), unique=True)
    identificacion: Mapped[str | None] = mapped_column(String(20))
    tipo_servicio: Mapped[str | None] = mapped_column(String(60))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CuentaPorPagar(_PK, Base):
    __tablename__ = "cuenta_por_pagar"
    origen_tipo: Mapped[str] = mapped_column(String(12))
    orden_compra_id: Mapped[int | None] = mapped_column(ForeignKey("orden_compra.id", ondelete="RESTRICT"))
    gasto_id: Mapped[int | None] = mapped_column(ForeignKey("gasto.id", ondelete="RESTRICT"))
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id", ondelete="RESTRICT"))
    beneficiario_id: Mapped[int | None] = mapped_column(ForeignKey("beneficiario.id", ondelete="RESTRICT"))
    monto_original: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estado: Mapped[str] = mapped_column(String(10), server_default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cheque(_PK, Base):
    __tablename__ = "cheque"
    tipo: Mapped[str] = mapped_column(String(10))
    banco: Mapped[str | None] = mapped_column(String(80))
    numero: Mapped[str | None] = mapped_column(String(40))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    fecha: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(14), server_default="en_cartera")
    cliente_id: Mapped[int | None] = mapped_column(BigInteger)
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id", ondelete="SET NULL"))
    beneficiario_id: Mapped[int | None] = mapped_column(ForeignKey("beneficiario.id", ondelete="SET NULL"))
    documento_origen_tipo: Mapped[str | None] = mapped_column(String(12))
    documento_origen_id: Mapped[int | None] = mapped_column(BigInteger)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CobroCxc(_PK, Base):
    __tablename__ = "cobro_cxc"
    cxc_id: Mapped[int] = mapped_column(BigInteger)  # FK cruzada a cuenta_por_cobrar (ventas, 009)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    medio_pago_id: Mapped[int] = mapped_column(ForeignKey("medio_pago.id", ondelete="RESTRICT"))
    fecha: Mapped[date] = mapped_column(Date)
    cheque_id: Mapped[int | None] = mapped_column(ForeignKey("cheque.id", ondelete="SET NULL"))
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PagoCxp(_PK, Base):
    __tablename__ = "pago_cxp"
    cxp_id: Mapped[int] = mapped_column(ForeignKey("cuenta_por_pagar.id", ondelete="RESTRICT"))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    medio_pago_id: Mapped[int] = mapped_column(ForeignKey("medio_pago.id", ondelete="RESTRICT"))
    fecha: Mapped[date] = mapped_column(Date)
    cheque_id: Mapped[int | None] = mapped_column(ForeignKey("cheque.id", ondelete="SET NULL"))
    retencion_fuente: Mapped[dict | None] = mapped_column(JSONB)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GastoRecurrente(_PK, Base):
    __tablename__ = "gasto_recurrente"
    categoria_gasto_id: Mapped[int] = mapped_column(ForeignKey("categoria_gasto.id", ondelete="RESTRICT"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id", ondelete="SET NULL"))
    beneficiario_id: Mapped[int | None] = mapped_column(ForeignKey("beneficiario.id", ondelete="SET NULL"))
    descripcion: Mapped[str] = mapped_column(String(160))
    monto_estimado: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    frecuencia: Mapped[str] = mapped_column(String(12))
    proxima_generacion: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(10), server_default="activo")
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Gasto(_PK, Base):
    __tablename__ = "gasto"
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    categoria_gasto_id: Mapped[int] = mapped_column(ForeignKey("categoria_gasto.id", ondelete="RESTRICT"))
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id", ondelete="SET NULL"))
    beneficiario_id: Mapped[int | None] = mapped_column(ForeignKey("beneficiario.id", ondelete="SET NULL"))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    fecha: Mapped[date] = mapped_column(Date)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    documento_soporte_objeto: Mapped[str | None] = mapped_column(String(255))
    estado_pago: Mapped[str | None] = mapped_column(String(10))
    medio_pago_id: Mapped[int | None] = mapped_column(ForeignKey("medio_pago.id", ondelete="SET NULL"))
    movimiento_caja_id: Mapped[int | None] = mapped_column(ForeignKey("movimiento_caja.id", ondelete="SET NULL"))
    cuenta_por_pagar_id: Mapped[int | None] = mapped_column(ForeignKey("cuenta_por_pagar.id", ondelete="SET NULL"))
    gasto_recurrente_id: Mapped[int | None] = mapped_column(ForeignKey("gasto_recurrente.id", ondelete="SET NULL"))
    estado: Mapped[str] = mapped_column(String(10), server_default="confirmado")
    asiento_id: Mapped[int | None] = mapped_column(ForeignKey("asiento.id", ondelete="SET NULL"))
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReglaAsientoAutomatico(_PK, Base):
    __tablename__ = "regla_asiento_automatico"
    evento: Mapped[str] = mapped_column(String(24))
    cuenta_debe_id: Mapped[int] = mapped_column(ForeignKey("cuenta_contable.id", ondelete="RESTRICT"))
    cuenta_haber_id: Mapped[int] = mapped_column(ForeignKey("cuenta_contable.id", ondelete="RESTRICT"))
    condicion: Mapped[dict | None] = mapped_column(JSONB)
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
