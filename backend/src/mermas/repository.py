"""Acceso a datos del módulo `mermas`."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mermas.models import AutorizacionBaja, DocumentoSoporteMerma, HistorialEstadoMerma, Merma, ReclamoMerma


def siguiente_numero(db: Session) -> str:
    n = db.scalar(select(func.nextval("merma_numero_seq")))
    return f"M-{int(n):06d}"


def crear(db: Session, **campos) -> Merma:
    m = Merma(**campos)
    db.add(m)
    db.flush()
    return m


def obtener(db: Session, mid: int, *, for_update: bool = False) -> Merma | None:
    stmt = select(Merma).where(Merma.id == mid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def buscar(
    db: Session, *, sucursales: list[int] | None, sucursal_id: int | None, causa: str | None,
    estado: str | None, desde: date | None, hasta: date | None, offset: int, limit: int,
) -> tuple[list[Merma], int]:
    stmt = select(Merma)
    if sucursales is not None:
        stmt = stmt.where(Merma.sucursal_id.in_(sucursales or [-1]))
    if sucursal_id:
        stmt = stmt.where(Merma.sucursal_id == sucursal_id)
    if causa:
        stmt = stmt.where(Merma.causa == causa)
    if estado:
        stmt = stmt.where(Merma.estado == estado)
    if desde:
        stmt = stmt.where(Merma.fecha_evento >= desde)
    if hasta:
        stmt = stmt.where(Merma.fecha_evento <= hasta)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Merma.creado_en.desc()).offset(offset).limit(limit)))
    return filas, int(total)


def para_reporte(
    db: Session, *, sucursales: list[int] | None, causa: str | None, desde: date | None, hasta: date | None,
) -> list[Merma]:
    stmt = select(Merma)
    if sucursales is not None:
        stmt = stmt.where(Merma.sucursal_id.in_(sucursales or [-1]))
    if causa:
        stmt = stmt.where(Merma.causa == causa)
    if desde:
        stmt = stmt.where(Merma.fecha_evento >= desde)
    if hasta:
        stmt = stmt.where(Merma.fecha_evento <= hasta)
    return list(db.scalars(stmt))


def bien_ya_reportado_activo(db: Session, *, reloj_id: int | None, pieza_id: int | None) -> bool:
    """¿Existe ya una merma de este bien que no esté cerrada (dado_de_baja/reingresada)?"""
    stmt = select(func.count(Merma.id)).where(Merma.estado == "en_evaluacion")
    if reloj_id:
        stmt = stmt.where(Merma.reloj_id == reloj_id)
    elif pieza_id:
        stmt = stmt.where(Merma.pieza_id == pieza_id)
    else:
        return False
    return bool(db.scalar(stmt))


def crear_autorizacion(db: Session, **campos) -> AutorizacionBaja:
    a = AutorizacionBaja(**campos)
    db.add(a)
    db.flush()
    return a


def agregar_documento(db: Session, **campos) -> DocumentoSoporteMerma:
    d = DocumentoSoporteMerma(**campos)
    db.add(d)
    db.flush()
    return d


def crear_reclamo(db: Session, **campos) -> ReclamoMerma:
    r = ReclamoMerma(**campos)
    db.add(r)
    db.flush()
    return r


def reclamo_de_merma(db: Session, mid: int) -> ReclamoMerma | None:
    return db.scalars(
        select(ReclamoMerma).where(ReclamoMerma.merma_id == mid).order_by(ReclamoMerma.id.desc())
    ).first()


def agregar_historial(db: Session, **campos) -> HistorialEstadoMerma:
    h = HistorialEstadoMerma(**campos)
    db.add(h)
    db.flush()
    return h
