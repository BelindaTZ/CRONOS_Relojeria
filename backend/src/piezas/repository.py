"""Acceso a datos del módulo `piezas`."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from piezas.models import (
    LotePieza,
    MovimientoStockPieza,
    Pieza,
    PiezaCalibre,
    StockPieza,
)


def buscar_piezas(
    db: Session,
    *,
    q: str | None,
    calibre_id: int | None,
    bajo_minimo: bool,
    solo_activas: bool,
    offset: int,
    limit: int,
    sucursales: list[int] | None = None,
) -> tuple[list[Pieza], int, dict[int, int]]:
    _stock_q = select(
        StockPieza.pieza_id, func.coalesce(func.sum(StockPieza.stock_actual), 0).label("total")
    )
    if sucursales is not None:
        _stock_q = _stock_q.where(StockPieza.sucursal_id.in_(sucursales))
    stock_sub = _stock_q.group_by(StockPieza.pieza_id).subquery()
    stmt = select(Pieza).outerjoin(stock_sub, stock_sub.c.pieza_id == Pieza.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Pieza.codigo.ilike(like), Pieza.descripcion.ilike(like)))
    if solo_activas:
        stmt = stmt.where(Pieza.activo.is_(True))
    if calibre_id:
        stmt = stmt.where(
            Pieza.id.in_(select(PiezaCalibre.pieza_id).where(PiezaCalibre.calibre_id == calibre_id))
        )
    if bajo_minimo:
        stmt = stmt.where(func.coalesce(stock_sub.c.total, 0) <= Pieza.stock_minimo)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Pieza.codigo).offset(offset).limit(limit)))
    ids = [p.id for p in filas]
    totales = stock_total_por_pieza(db, ids, sucursales=sucursales)
    return filas, total, totales


def stock_total_por_pieza(
    db: Session, ids: list[int], *, sucursales: list[int] | None = None
) -> dict[int, int]:
    if not ids:
        return {}
    stmt = select(StockPieza.pieza_id, func.coalesce(func.sum(StockPieza.stock_actual), 0)).where(
        StockPieza.pieza_id.in_(ids)
    )
    if sucursales is not None:
        stmt = stmt.where(StockPieza.sucursal_id.in_(sucursales))
    filas = db.execute(stmt.group_by(StockPieza.pieza_id)).all()
    return {pid: int(total) for pid, total in filas}


def obtener(db: Session, pid: int) -> Pieza | None:
    return db.get(Pieza, pid)


def por_codigo(db: Session, codigo: str) -> Pieza | None:
    return db.scalars(select(Pieza).where(Pieza.codigo == codigo)).first()


def crear(db: Session, **campos) -> Pieza:
    p = Pieza(**campos)
    db.add(p)
    db.flush()
    return p


def set_calibres(db: Session, pieza_id: int, calibre_ids: list[int]) -> None:
    for pc in db.scalars(select(PiezaCalibre).where(PiezaCalibre.pieza_id == pieza_id)):
        db.delete(pc)
    db.flush()
    for cid in dict.fromkeys(calibre_ids):
        db.add(PiezaCalibre(pieza_id=pieza_id, calibre_id=cid))
    db.flush()


def calibres_de(db: Session, pieza_id: int) -> list[int]:
    return list(db.scalars(select(PiezaCalibre.calibre_id).where(PiezaCalibre.pieza_id == pieza_id)))


# --------------------------------------------------------------------- stock
def stock_row(db: Session, *, pieza_id: int, sucursal_id: int, for_update: bool = False) -> StockPieza | None:
    stmt = select(StockPieza).where(
        StockPieza.pieza_id == pieza_id, StockPieza.sucursal_id == sucursal_id
    )
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def crear_stock_row(db: Session, *, pieza_id: int, sucursal_id: int) -> StockPieza:
    row = StockPieza(pieza_id=pieza_id, sucursal_id=sucursal_id, stock_actual=0)
    db.add(row)
    db.flush()
    return row


def stock_por_sucursal(db: Session, pieza_id: int) -> list[StockPieza]:
    return list(
        db.scalars(
            select(StockPieza).where(StockPieza.pieza_id == pieza_id).order_by(StockPieza.sucursal_id)
        )
    )


# --------------------------------------------------------------------- lotes
def lotes_de(db: Session, pieza_id: int, *, solo_con_saldo: bool = False) -> list[LotePieza]:
    stmt = select(LotePieza).where(LotePieza.pieza_id == pieza_id)
    if solo_con_saldo:
        stmt = stmt.where(LotePieza.cantidad > 0)
    return list(db.scalars(stmt.order_by(LotePieza.fecha_caducidad, LotePieza.id)))


def lotes_fefo(db: Session, *, pieza_id: int, sucursal_id: int) -> list[LotePieza]:
    return list(
        db.scalars(
            select(LotePieza)
            .where(
                LotePieza.pieza_id == pieza_id,
                LotePieza.sucursal_id == sucursal_id,
                LotePieza.cantidad > 0,
            )
            .order_by(LotePieza.fecha_caducidad, LotePieza.id)
            .with_for_update()
        )
    )


def lote_por_numero(db: Session, *, pieza_id: int, sucursal_id: int, numero: str) -> LotePieza | None:
    return db.scalars(
        select(LotePieza).where(
            LotePieza.pieza_id == pieza_id,
            LotePieza.sucursal_id == sucursal_id,
            LotePieza.numero_lote == numero,
        )
    ).first()


def crear_lote(
    db: Session, *, pieza_id: int, sucursal_id: int, numero: str, caducidad: date, cantidad: int
) -> LotePieza:
    lote = LotePieza(
        pieza_id=pieza_id,
        sucursal_id=sucursal_id,
        numero_lote=numero,
        fecha_caducidad=caducidad,
        cantidad=cantidad,
    )
    db.add(lote)
    db.flush()
    return lote


def todos_los_lotes(
    db: Session, *, estado: str | None, sucursal_id: int | None
) -> list[tuple[LotePieza, Pieza]]:
    stmt = select(LotePieza, Pieza).join(Pieza, Pieza.id == LotePieza.pieza_id).where(LotePieza.cantidad > 0)
    if estado:
        stmt = stmt.where(LotePieza.estado == estado)
    if sucursal_id:
        stmt = stmt.where(LotePieza.sucursal_id == sucursal_id)
    return [(row[0], row[1]) for row in db.execute(stmt.order_by(LotePieza.fecha_caducidad)).all()]


# --------------------------------------------------------------------- movimientos
def registrar_movimiento(db: Session, **campos) -> MovimientoStockPieza:
    m = MovimientoStockPieza(**campos)
    db.add(m)
    db.flush()
    return m


def movimientos_de(db: Session, pieza_id: int, *, offset: int, limit: int) -> tuple[list[MovimientoStockPieza], int]:
    base = select(MovimientoStockPieza).where(MovimientoStockPieza.pieza_id == pieza_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    filas = list(
        db.scalars(base.order_by(MovimientoStockPieza.creado_en.desc(), MovimientoStockPieza.id.desc()).offset(offset).limit(limit))
    )
    return filas, total


def valor_piezas(db: Session, *, sucursales: list[int] | None = None) -> tuple[int, float, float]:
    refs = db.scalar(select(func.count(Pieza.id)).where(Pieza.activo.is_(True))) or 0
    stmt = (
        select(
            func.coalesce(func.sum(StockPieza.stock_actual * func.coalesce(Pieza.precio_venta_suelta, 0)), 0),
            func.coalesce(func.sum(StockPieza.stock_actual * func.coalesce(Pieza.costo_adquisicion, 0)), 0),
        )
        .select_from(StockPieza)
        .join(Pieza, Pieza.id == StockPieza.pieza_id)
        .where(Pieza.activo.is_(True))
    )
    if sucursales is not None:
        stmt = stmt.where(StockPieza.sucursal_id.in_(sucursales))
    row = db.execute(stmt).one()
    return int(refs), float(row[0]), float(row[1])
