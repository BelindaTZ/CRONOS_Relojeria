"""Modelos ORM del módulo `ventas` (feature 009).

Esquema físico creado a mano por la migración `0021_ventas`. Reutiliza `reloj`,
`pieza` (003); `cliente`, `autorizacion_margen_minimo` (006); `cita` (007);
`usuario`, `sucursal` (001) solo por FK. Los pagos van en la tabla `pago` de
`shared/pagos` con `documento_tipo='venta'`.
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


class OrdenVenta(_PK, Base):
    __tablename__ = "orden_venta"

    numero: Mapped[str] = mapped_column(String(20))
    numero_factura: Mapped[str | None] = mapped_column(String(20))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="RESTRICT"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    vendedor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    cita_id: Mapped[int | None] = mapped_column(ForeignKey("cita.id", ondelete="SET NULL"))
    estado: Mapped[str] = mapped_column(String(10), server_default="borrador")
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    subtotal_sin_impuestos: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_descuento: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    iva_porcentaje: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    iva_monto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    margen_venta: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    descuento_aplicado: Mapped[dict | None] = mapped_column(JSONB)
    autorizacion_margen_minimo_id: Mapped[int | None] = mapped_column(
        ForeignKey("autorizacion_margen_minimo.id", ondelete="SET NULL")
    )
    identificacion_fiscal: Mapped[str | None] = mapped_column(String(20))
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lineas: Mapped[list[LineaVenta]] = relationship(
        back_populates="orden", cascade="all, delete-orphan", lazy="selectin", order_by="LineaVenta.id"
    )
    garantias: Mapped[list[GarantiaVenta]] = relationship(
        back_populates="orden", cascade="all, delete-orphan", lazy="selectin"
    )


class LineaVenta(_PK, Base):
    __tablename__ = "linea_venta"
    orden_venta_id: Mapped[int] = mapped_column(ForeignKey("orden_venta.id", ondelete="CASCADE"))
    item_tipo: Mapped[str] = mapped_column(String(8))
    reloj_id: Mapped[int | None] = mapped_column(ForeignKey("reloj.id", ondelete="RESTRICT"))
    pieza_id: Mapped[int | None] = mapped_column(ForeignKey("pieza.id", ondelete="RESTRICT"))
    cantidad: Mapped[int] = mapped_column(Integer, server_default="1")
    precio_lista: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    precio_final: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    costo: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    margen: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    descuento_monto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    base_imponible: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    iva_monto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    tarifa_iva: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))

    orden: Mapped[OrdenVenta] = relationship(back_populates="lineas")


class GarantiaVenta(_PK, Base):
    __tablename__ = "garantia_venta"
    orden_venta_id: Mapped[int] = mapped_column(ForeignKey("orden_venta.id", ondelete="CASCADE"))
    linea_venta_id: Mapped[int | None] = mapped_column(ForeignKey("linea_venta.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(8))
    periodo_dias: Mapped[int] = mapped_column(Integer, server_default="0")
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    cobertura: Mapped[str | None] = mapped_column(String(255))

    orden: Mapped[OrdenVenta] = relationship(back_populates="garantias")


class ComprobanteVenta(_PK, Base):
    __tablename__ = "comprobante_venta"
    orden_venta_id: Mapped[int] = mapped_column(ForeignKey("orden_venta.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(40))
    objeto: Mapped[str] = mapped_column(String(255))
    numero_serie_vinculado: Mapped[str | None] = mapped_column(String(80))
    generado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnulacionVenta(_PK, Base):
    __tablename__ = "anulacion_venta"
    orden_venta_id: Mapped[int] = mapped_column(ForeignKey("orden_venta.id", ondelete="CASCADE"))
    motivo: Mapped[str] = mapped_column(String(255))
    actor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reversas: Mapped[dict | None] = mapped_column(JSONB)


class ConfigFacturacion(Base):
    """Datos del emisor para la factura (fila única, id=1). Configurable por Gerencia."""

    __tablename__ = "config_facturacion"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200))
    nombre_comercial: Mapped[str | None] = mapped_column(String(200))
    ruc: Mapped[str] = mapped_column(String(13))
    direccion_matriz: Mapped[str | None] = mapped_column(String(255))
    obligado_contabilidad: Mapped[bool] = mapped_column(Boolean, server_default="true")
    contribuyente_especial: Mapped[str | None] = mapped_column(String(40))
    regimen: Mapped[str | None] = mapped_column(String(40))
    leyenda_pie: Mapped[str | None] = mapped_column(String(255))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PuntoEmision(_PK, Base):
    """Punto de emisión por sucursal: establecimiento + punto + secuencial propio
    (numeración tipo SRI `EEE-PPP-NNNNNNNNN`)."""

    __tablename__ = "punto_emision"
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="CASCADE"), unique=True)
    establecimiento_codigo: Mapped[str] = mapped_column(String(3), server_default="001")
    punto_emision_codigo: Mapped[str] = mapped_column(String(3), server_default="001")
    secuencial_actual: Mapped[int] = mapped_column(BigInteger, server_default="0")
    direccion_establecimiento: Mapped[str | None] = mapped_column(String(255))


class CuentaPorCobrar(_PK, Base):
    """Obligación creada por 009 al confirmar una venta a crédito (y por la entrega a
    crédito de una OT de 008). El subledger / aging lo maneja 010."""

    __tablename__ = "cuenta_por_cobrar"
    origen_tipo: Mapped[str] = mapped_column(String(16))
    origen_id: Mapped[int] = mapped_column(BigInteger)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="RESTRICT"))
    monto_original: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estado: Mapped[str] = mapped_column(String(10), server_default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
