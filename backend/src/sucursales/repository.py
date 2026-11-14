from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from shared.models import HorarioSucursal, Sucursal, Usuario, UsuarioSucursal


def obtener(db: Session, sucursal_id: int) -> Sucursal | None:
    return db.get(Sucursal, sucursal_id)


def por_nombre(db: Session, nombre: str) -> Sucursal | None:
    return db.scalars(select(Sucursal).where(Sucursal.nombre == nombre)).first()


def buscar(db: Session, q: str | None, offset: int, limit: int) -> tuple[list[Sucursal], int]:
    filtros = []
    if q:
        like = f"%{q}%"
        filtros.append(or_(Sucursal.nombre.ilike(like), Sucursal.direccion.ilike(like)))
    total = db.scalar(select(func.count()).select_from(Sucursal).where(*filtros)) or 0
    filas = list(
        db.scalars(select(Sucursal).where(*filtros).order_by(Sucursal.nombre).offset(offset).limit(limit))
    )
    return filas, int(total)


def crear(db: Session, **campos) -> Sucursal:
    s = Sucursal(**campos)
    db.add(s)
    db.flush()
    return s


def personal_de(db: Session, sucursal_id: int) -> list[Usuario]:
    return list(
        db.scalars(
            select(Usuario)
            .join(UsuarioSucursal, UsuarioSucursal.usuario_id == Usuario.id)
            .where(UsuarioSucursal.sucursal_id == sucursal_id, Usuario.estado == "activo")
        )
    )


def horario_de(db: Session, sucursal_id: int) -> list[HorarioSucursal]:
    return list(
        db.scalars(
            select(HorarioSucursal)
            .where(HorarioSucursal.sucursal_id == sucursal_id)
            .order_by(HorarioSucursal.dia_semana)
        )
    )


def reemplazar_horario(db: Session, sucursal_id: int, dias: list[dict]) -> list[HorarioSucursal]:
    db.execute(
        HorarioSucursal.__table__.delete().where(HorarioSucursal.sucursal_id == sucursal_id)
    )
    filas = []
    for d in dias:
        h = HorarioSucursal(sucursal_id=sucursal_id, **d)
        db.add(h)
        filas.append(h)
    db.flush()
    return sorted(filas, key=lambda h: h.dia_semana)
