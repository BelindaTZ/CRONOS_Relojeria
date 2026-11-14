"""Acceso a datos del módulo `ventas`."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ventas.models import (
    AnulacionVenta,
    ComprobanteVenta,
    ConfigFacturacion,
    CuentaPorCobrar,
    GarantiaVenta,
    LineaVenta,
    OrdenVenta,
    PuntoEmision,
)


def obtener(db: Session, vid: int, *, for_update: bool = False) -> OrdenVenta | None:
    stmt = select(OrdenVenta).where(OrdenVenta.id == vid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def siguiente_numero(db: Session) -> str:
    n = db.scalar(select(func.nextval("orden_venta_numero_seq")))
    return f"V-{int(n):06d}"


def crear(db: Session, **campos) -> OrdenVenta:
    o = OrdenVenta(**campos)
    db.add(o)
    db.flush()
    return o


def agregar_linea(db: Session, **campos) -> LineaVenta:
    ln = LineaVenta(**campos)
    db.add(ln)
    db.flush()
    return ln


def lineas_de(db: Session, vid: int) -> list[LineaVenta]:
    return list(db.scalars(
        select(LineaVenta).where(LineaVenta.orden_venta_id == vid).order_by(LineaVenta.id)
    ))


def agregar_garantia(db: Session, **campos) -> GarantiaVenta:
    g = GarantiaVenta(**campos)
    db.add(g)
    db.flush()
    return g


def garantias_de(db: Session, vid: int) -> list[GarantiaVenta]:
    return list(db.scalars(
        select(GarantiaVenta).where(GarantiaVenta.orden_venta_id == vid).order_by(GarantiaVenta.id)
    ))


def agregar_comprobante(db: Session, **campos) -> ComprobanteVenta:
    c = ComprobanteVenta(**campos)
    db.add(c)
    db.flush()
    return c


def comprobantes_de(db: Session, vid: int) -> list[ComprobanteVenta]:
    return list(db.scalars(
        select(ComprobanteVenta).where(ComprobanteVenta.orden_venta_id == vid).order_by(ComprobanteVenta.id)
    ))


def agregar_anulacion(db: Session, **campos) -> AnulacionVenta:
    a = AnulacionVenta(**campos)
    db.add(a)
    db.flush()
    return a


def buscar(
    db: Session, *, sucursales: list[int] | None, estado: str | None, cliente_id: int | None,
    cliente_ids: list[int] | None, sucursal_id: int | None, desde: date | None, hasta: date | None,
    offset: int, limit: int,
) -> tuple[list[OrdenVenta], int]:
    stmt = select(OrdenVenta)
    if sucursales is not None:
        stmt = stmt.where(OrdenVenta.sucursal_id.in_(sucursales or [-1]))
    if estado:
        stmt = stmt.where(OrdenVenta.estado == estado)
    if cliente_id:
        stmt = stmt.where(OrdenVenta.cliente_id == cliente_id)
    if cliente_ids is not None:
        stmt = stmt.where(OrdenVenta.cliente_id.in_(cliente_ids or [-1]))
    if sucursal_id:
        stmt = stmt.where(OrdenVenta.sucursal_id == sucursal_id)
    if desde:
        stmt = stmt.where(OrdenVenta.fecha >= datetime(desde.year, desde.month, desde.day))
    if hasta:
        stmt = stmt.where(OrdenVenta.fecha <= datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(OrdenVenta.fecha.desc()).offset(offset).limit(limit)))
    return filas, int(total)


def ventas_confirmadas_del_dia(
    db: Session, *, sucursales: list[int] | None, sucursal_id: int | None, dia: date,
) -> list[OrdenVenta]:
    ini = datetime(dia.year, dia.month, dia.day)
    fin = datetime(dia.year, dia.month, dia.day, 23, 59, 59)
    stmt = select(OrdenVenta).where(
        OrdenVenta.estado == "confirmada", OrdenVenta.fecha >= ini, OrdenVenta.fecha <= fin
    )
    if sucursales is not None:
        stmt = stmt.where(OrdenVenta.sucursal_id.in_(sucursales or [-1]))
    if sucursal_id:
        stmt = stmt.where(OrdenVenta.sucursal_id == sucursal_id)
    return list(db.scalars(stmt))


def ventas_borrador(db: Session) -> list[OrdenVenta]:
    return list(db.scalars(select(OrdenVenta).where(OrdenVenta.estado == "borrador")))


def ventas_confirmadas_de_cliente(db: Session, cliente_id: int) -> list[OrdenVenta]:
    return list(db.scalars(
        select(OrdenVenta).where(
            OrdenVenta.cliente_id == cliente_id, OrdenVenta.estado == "confirmada"
        )
    ))


# ------------------------------------------------------------ cuentas por cobrar
def crear_cxc(db: Session, **campos) -> CuentaPorCobrar:
    c = CuentaPorCobrar(**campos)
    db.add(c)
    db.flush()
    return c


def cxc_de_origen(db: Session, *, origen_tipo: str, origen_id: int) -> CuentaPorCobrar | None:
    return db.scalars(
        select(CuentaPorCobrar).where(
            CuentaPorCobrar.origen_tipo == origen_tipo, CuentaPorCobrar.origen_id == origen_id
        )
    ).first()


def listar_cxc(db: Session, *, cliente_id: int | None, estado: str | None) -> list[CuentaPorCobrar]:
    stmt = select(CuentaPorCobrar)
    if cliente_id:
        stmt = stmt.where(CuentaPorCobrar.cliente_id == cliente_id)
    if estado:
        stmt = stmt.where(CuentaPorCobrar.estado == estado)
    return list(db.scalars(stmt.order_by(CuentaPorCobrar.creado_en.desc())))


# ------------------------------------------------------------ facturación
def config_facturacion(db: Session) -> ConfigFacturacion:
    row = db.get(ConfigFacturacion, 1)
    if row is None:
        row = ConfigFacturacion(id=1, razon_social="CRONOS Relojería", ruc="0000000000001")
        db.add(row)
        db.flush()
    return row


def punto_emision(db: Session, sucursal_id: int, *, for_update: bool = False) -> PuntoEmision | None:
    stmt = select(PuntoEmision).where(PuntoEmision.sucursal_id == sucursal_id)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def puntos_emision(db: Session) -> list[PuntoEmision]:
    return list(db.scalars(select(PuntoEmision).order_by(PuntoEmision.sucursal_id)))


def crear_punto_emision(db: Session, **campos) -> PuntoEmision:
    p = PuntoEmision(**campos)
    db.add(p)
    db.flush()
    return p
