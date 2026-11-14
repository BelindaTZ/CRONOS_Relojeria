"""Acceso a datos del módulo `citas`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from citas.models import Cita, HistorialEstadoCita


def obtener(db: Session, cid: int, *, for_update: bool = False) -> Cita | None:
    stmt = select(Cita).where(Cita.id == cid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def crear(db: Session, **campos) -> Cita:
    c = Cita(**campos)
    db.add(c)
    db.flush()
    return c


def registrar_estado(db: Session, **campos) -> HistorialEstadoCita:
    h = HistorialEstadoCita(**campos)
    db.add(h)
    db.flush()
    return h


def historial(db: Session, cita_id: int) -> list[HistorialEstadoCita]:
    return list(
        db.scalars(
            select(HistorialEstadoCita)
            .where(HistorialEstadoCita.cita_id == cita_id)
            .order_by(HistorialEstadoCita.timestamp)
        )
    )


def buscar(
    db: Session, *, sucursales: list[int] | None, estado: str | None, canal_cita_id: int | None,
    sucursal_id: int | None, cliente_id: int | None, cliente_ids: list[int] | None,
    desde: datetime | None, hasta: datetime | None, offset: int, limit: int,
) -> tuple[list[Cita], int]:
    stmt = select(Cita)
    if sucursales is not None:
        stmt = stmt.where(Cita.sucursal_id.in_(sucursales or [-1]))
    if estado:
        stmt = stmt.where(Cita.estado == estado)
    if canal_cita_id:
        stmt = stmt.where(Cita.canal_cita_id == canal_cita_id)
    if sucursal_id:
        stmt = stmt.where(Cita.sucursal_id == sucursal_id)
    if cliente_id:
        stmt = stmt.where(Cita.cliente_id == cliente_id)
    if cliente_ids is not None:
        stmt = stmt.where(Cita.cliente_id.in_(cliente_ids or [-1]))
    if desde:
        stmt = stmt.where(func.coalesce(Cita.fecha_confirmada, Cita.fecha_preferida) >= desde)
    if hasta:
        stmt = stmt.where(func.coalesce(Cita.fecha_confirmada, Cita.fecha_preferida) <= hasta)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(
        db.scalars(
            stmt.order_by(func.coalesce(Cita.fecha_confirmada, Cita.fecha_preferida).desc())
            .offset(offset).limit(limit)
        )
    )
    return filas, int(total)


def agenda(
    db: Session, *, sucursales: list[int] | None, sucursal_id: int | None,
    desde: datetime, hasta: datetime,
) -> list[Cita]:
    hora = func.coalesce(Cita.fecha_confirmada, Cita.fecha_preferida)
    stmt = select(Cita).where(
        hora >= desde, hora <= hasta,
        Cita.estado.in_(("pendiente", "confirmada", "atendida")),
    )
    # El alcance por sucursal SIEMPRE se aplica: `sucursal_id` solo acota más
    # (nunca amplía). Un usuario no-Gerencia que pida otra sucursal ve 0 citas.
    if sucursales is not None:
        stmt = stmt.where(Cita.sucursal_id.in_(sucursales or [-1]))
    if sucursal_id:
        stmt = stmt.where(Cita.sucursal_id == sucursal_id)
    return list(db.scalars(stmt.order_by(hora)))


def solapadas(db: Session, *, sucursal_id: int, inicio: datetime, fin: datetime, excluir_id: int) -> list[Cita]:
    hora = func.coalesce(Cita.fecha_confirmada, Cita.fecha_preferida)
    return list(
        db.scalars(
            select(Cita).where(
                Cita.sucursal_id == sucursal_id,
                Cita.estado == "confirmada",
                Cita.id != excluir_id,
                hora >= inicio, hora <= fin,
            )
        )
    )


def contar_conversion(db: Session, *, desde: datetime | None, hasta: datetime | None) -> tuple[int, int]:
    stmt = select(Cita).where(Cita.estado == "atendida")
    if desde:
        stmt = stmt.where(func.coalesce(Cita.fecha_confirmada, Cita.fecha_preferida) >= desde)
    if hasta:
        stmt = stmt.where(func.coalesce(Cita.fecha_confirmada, Cita.fecha_preferida) <= hasta)
    filas = list(db.scalars(stmt))
    con_tx = sum(1 for c in filas if c.venta_id or c.orden_trabajo_id)
    return len(filas), con_tx


def confirmadas_en_ventana(db: Session, *, desde: datetime, hasta: datetime) -> list[Cita]:
    hora = func.coalesce(Cita.fecha_confirmada, Cita.fecha_preferida)
    return list(
        db.scalars(
            select(Cita).where(Cita.estado == "confirmada", hora >= desde, hora <= hasta).order_by(hora)
        )
    )
