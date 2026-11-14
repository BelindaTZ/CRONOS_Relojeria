"""Acceso a datos del módulo `servicio_tecnico`."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from servicio_tecnico.models import (
    DocumentoOT,
    HistorialEstadoOT,
    OrdenTrabajo,
    PiezaUsadaOT,
    Presupuesto,
    PresupuestoLineaPieza,
)


def obtener(db: Session, oid: int, *, for_update: bool = False) -> OrdenTrabajo | None:
    stmt = select(OrdenTrabajo).where(OrdenTrabajo.id == oid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def siguiente_numero(db: Session) -> str:
    n = db.scalar(select(func.nextval("orden_trabajo_numero_seq")))
    return f"OT-{int(n):06d}"


def crear(db: Session, **campos) -> OrdenTrabajo:
    o = OrdenTrabajo(**campos)
    db.add(o)
    db.flush()
    return o


def registrar_estado(db: Session, *, orden_trabajo_id: int, estado: str, actor_usuario_id: int | None) -> None:
    db.add(HistorialEstadoOT(
        orden_trabajo_id=orden_trabajo_id, estado=estado, actor_usuario_id=actor_usuario_id
    ))
    db.flush()


def historial(db: Session, oid: int) -> list[HistorialEstadoOT]:
    return list(db.scalars(
        select(HistorialEstadoOT).where(HistorialEstadoOT.orden_trabajo_id == oid)
        .order_by(HistorialEstadoOT.timestamp, HistorialEstadoOT.id)
    ))


def buscar(
    db: Session, *, sucursales: list[int] | None, solo_tecnico_id: int | None,
    estado: str | None, tecnico_id: int | None, sucursal_id: int | None,
    reloj_ids: list[int] | None, offset: int, limit: int,
) -> tuple[list[OrdenTrabajo], int]:
    stmt = select(OrdenTrabajo)
    if sucursales is not None:
        stmt = stmt.where(OrdenTrabajo.sucursal_id.in_(sucursales or [-1]))
    if solo_tecnico_id is not None:
        stmt = stmt.where(OrdenTrabajo.tecnico_id == solo_tecnico_id)
    if estado:
        stmt = stmt.where(OrdenTrabajo.estado == estado)
    if tecnico_id:
        stmt = stmt.where(OrdenTrabajo.tecnico_id == tecnico_id)
    if sucursal_id:
        stmt = stmt.where(OrdenTrabajo.sucursal_id == sucursal_id)
    if reloj_ids is not None:
        stmt = stmt.where(OrdenTrabajo.reloj_id.in_(reloj_ids or [-1]))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(
        stmt.order_by(OrdenTrabajo.fecha_ingreso.desc()).offset(offset).limit(limit)
    ))
    return filas, int(total)


def en_curso(db: Session, *, sucursales: list[int] | None) -> list[OrdenTrabajo]:
    stmt = select(OrdenTrabajo).where(
        OrdenTrabajo.estado.notin_(("entregado", "cancelada"))
    ).order_by(OrdenTrabajo.fecha_ingreso)
    if sucursales is not None:
        stmt = stmt.where(OrdenTrabajo.sucursal_id.in_(sucursales or [-1]))
    return list(db.scalars(stmt))


def cerradas_entre(
    db: Session, *, desde: date | None, hasta: date | None, tecnico_id: int | None,
    cliente_id: int | None, reloj_ids: list[int] | None,
) -> list[OrdenTrabajo]:
    stmt = select(OrdenTrabajo).where(OrdenTrabajo.estado == "entregado")
    if desde:
        stmt = stmt.where(OrdenTrabajo.fecha_real_entrega >= datetime(desde.year, desde.month, desde.day))
    if hasta:
        stmt = stmt.where(OrdenTrabajo.fecha_real_entrega <= datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59))
    if tecnico_id:
        stmt = stmt.where(OrdenTrabajo.tecnico_id == tecnico_id)
    if cliente_id:
        stmt = stmt.where(OrdenTrabajo.cliente_id == cliente_id)
    if reloj_ids is not None:
        stmt = stmt.where(OrdenTrabajo.reloj_id.in_(reloj_ids or [-1]))
    return list(db.scalars(stmt.order_by(OrdenTrabajo.fecha_real_entrega)))


def ots_de_tecnico_cerradas(db: Session, *, tecnico_id: int | None, inicio: date, fin: date) -> list[OrdenTrabajo]:
    stmt = select(OrdenTrabajo).where(
        OrdenTrabajo.estado == "entregado",
        OrdenTrabajo.fecha_real_entrega >= datetime(inicio.year, inicio.month, inicio.day),
        OrdenTrabajo.fecha_real_entrega <= datetime(fin.year, fin.month, fin.day, 23, 59, 59),
    )
    if tecnico_id is not None:
        stmt = stmt.where(OrdenTrabajo.tecnico_id == tecnico_id)
    return list(db.scalars(stmt))


def ots_no_entregadas(db: Session) -> list[OrdenTrabajo]:
    return list(db.scalars(
        select(OrdenTrabajo).where(OrdenTrabajo.estado.notin_(("entregado", "cancelada")))
    ))


def reprocesos_sobre_reloj(db: Session, reloj_id: int, *, excluir_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(OrdenTrabajo).where(
            OrdenTrabajo.reloj_id == reloj_id, OrdenTrabajo.id != excluir_id
        )
    ) or 0


# ------------------------------------------------------------ presupuesto
def presupuesto_activo(db: Session, oid: int) -> Presupuesto | None:
    return db.scalars(
        select(Presupuesto).where(Presupuesto.orden_trabajo_id == oid)
        .order_by(Presupuesto.creado_en.desc())
    ).first()


def crear_presupuesto(db: Session, **campos) -> Presupuesto:
    p = Presupuesto(**campos)
    db.add(p)
    db.flush()
    return p


def agregar_linea_presupuesto(db: Session, **campos) -> PresupuestoLineaPieza:
    linea = PresupuestoLineaPieza(**campos)
    db.add(linea)
    db.flush()
    return linea


def linea_presupuesto(db: Session, linea_id: int) -> PresupuestoLineaPieza | None:
    return db.get(PresupuestoLineaPieza, linea_id)


# ------------------------------------------------------------ piezas / lubricación
def agregar_pieza(db: Session, **campos) -> PiezaUsadaOT:
    pu = PiezaUsadaOT(**campos)
    db.add(pu)
    db.flush()
    return pu


def piezas_de(db: Session, oid: int) -> list[PiezaUsadaOT]:
    return list(db.scalars(
        select(PiezaUsadaOT).where(PiezaUsadaOT.orden_trabajo_id == oid).order_by(PiezaUsadaOT.id)
    ))


# ------------------------------------------------------------ documentos
def agregar_documento(db: Session, *, orden_trabajo_id: int, tipo: str, objeto: str) -> DocumentoOT:
    d = DocumentoOT(orden_trabajo_id=orden_trabajo_id, tipo=tipo, objeto=objeto)
    db.add(d)
    db.flush()
    return d


def documentos_de(db: Session, oid: int) -> list[DocumentoOT]:
    return list(db.scalars(
        select(DocumentoOT).where(DocumentoOT.orden_trabajo_id == oid).order_by(DocumentoOT.id)
    ))
