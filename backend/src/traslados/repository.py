"""Acceso a datos del módulo `traslados`."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from traslados.models import DiscrepanciaTransferencia, LineaTransferencia, Transferencia


def obtener(db: Session, tid: int, *, for_update: bool = False) -> Transferencia | None:
    stmt = select(Transferencia).where(Transferencia.id == tid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def crear(db: Session, **campos) -> Transferencia:
    t = Transferencia(**campos)
    db.add(t)
    db.flush()
    return t


def agregar_linea(db: Session, **campos) -> LineaTransferencia:
    l = LineaTransferencia(**campos)
    db.add(l)
    db.flush()
    return l


def linea(db: Session, lid: int) -> LineaTransferencia | None:
    return db.get(LineaTransferencia, lid)


def buscar(
    db: Session,
    *,
    sucursales: list[int] | None,
    sucursal_id: int | None,
    estado: str | None,
    reloj_ids: list[int] | None,
    offset: int,
    limit: int,
) -> tuple[list[Transferencia], int]:
    stmt = select(Transferencia)
    if sucursales is not None:
        stmt = stmt.where(
            or_(
                Transferencia.sucursal_origen_id.in_(sucursales),
                Transferencia.sucursal_destino_id.in_(sucursales),
            )
        )
    if sucursal_id:
        stmt = stmt.where(
            or_(
                Transferencia.sucursal_origen_id == sucursal_id,
                Transferencia.sucursal_destino_id == sucursal_id,
            )
        )
    if estado:
        stmt = stmt.where(Transferencia.estado == estado)
    if reloj_ids is not None:
        stmt = stmt.where(
            Transferencia.id.in_(
                select(LineaTransferencia.transferencia_id).where(
                    LineaTransferencia.reloj_id.in_(reloj_ids or [-1])
                )
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Transferencia.creado_en.desc()).offset(offset).limit(limit)))
    return filas, int(total)


def crear_discrepancia(db: Session, *, linea_transferencia_id: int, cantidad_faltante: int) -> DiscrepanciaTransferencia:
    d = DiscrepanciaTransferencia(
        linea_transferencia_id=linea_transferencia_id, cantidad_faltante=cantidad_faltante
    )
    db.add(d)
    db.flush()
    return d


def discrepancias_de(db: Session, tid: int) -> list[tuple[DiscrepanciaTransferencia, LineaTransferencia]]:
    return [
        (row[0], row[1])
        for row in db.execute(
            select(DiscrepanciaTransferencia, LineaTransferencia)
            .join(LineaTransferencia, LineaTransferencia.id == DiscrepanciaTransferencia.linea_transferencia_id)
            .where(LineaTransferencia.transferencia_id == tid)
        ).all()
    ]


def discrepancia_por_id(
    db: Session, did: int,
) -> tuple[DiscrepanciaTransferencia, LineaTransferencia, Transferencia] | None:
    row = db.execute(
        select(DiscrepanciaTransferencia, LineaTransferencia, Transferencia)
        .join(LineaTransferencia, LineaTransferencia.id == DiscrepanciaTransferencia.linea_transferencia_id)
        .join(Transferencia, Transferencia.id == LineaTransferencia.transferencia_id)
        .where(DiscrepanciaTransferencia.id == did)
    ).first()
    return (row[0], row[1], row[2]) if row else None


def tiene_discrepancias(db: Session, tid: int) -> bool:
    return bool(
        db.scalar(
            select(func.count(DiscrepanciaTransferencia.id))
            .join(LineaTransferencia, LineaTransferencia.id == DiscrepanciaTransferencia.linea_transferencia_id)
            .where(LineaTransferencia.transferencia_id == tid)
        )
    )
