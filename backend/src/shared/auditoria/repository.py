"""Acceso a datos de la auditoría. Append-only (la DB además lo fuerza por trigger)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.models import RegistroAuditoria, Usuario


def insertar(
    db: Session,
    *,
    actor_usuario_id: int | None,
    accion: str,
    entidad: str,
    entidad_id: str | None,
    antes: Any | None,
    despues: Any | None,
    ip_origen: str | None = None,
) -> RegistroAuditoria:
    reg = RegistroAuditoria(
        actor_usuario_id=actor_usuario_id,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        antes=antes,
        despues=despues,
        ip_origen=ip_origen,
    )
    db.add(reg)
    db.flush()
    return reg


def listar(
    db: Session,
    *,
    entidad: str | None = None,
    actor: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[RegistroAuditoria], int]:
    filtros = []
    if entidad:
        filtros.append(RegistroAuditoria.entidad == entidad)
    if actor:
        filtros.append(RegistroAuditoria.actor_usuario_id == actor)
    if desde:
        filtros.append(RegistroAuditoria.creado_en >= desde)
    if hasta:
        filtros.append(RegistroAuditoria.creado_en <= hasta)

    total = db.scalar(select(func.count()).select_from(RegistroAuditoria).where(*filtros)) or 0
    filas = list(
        db.execute(
            select(
                RegistroAuditoria,
                Usuario.nombre.label("actor_nombre"),
                Usuario.identificacion.label("actor_identificacion"),
            )
            .select_from(RegistroAuditoria)
            .join(Usuario, Usuario.id == RegistroAuditoria.actor_usuario_id, isouter=True)
            .where(*filtros)
            .order_by(RegistroAuditoria.creado_en.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return filas, int(total)
