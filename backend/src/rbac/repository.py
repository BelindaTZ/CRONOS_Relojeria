"""Acceso a datos del módulo RBAC."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shared.models import Modulo, Operacion, PermisoModulo, PermisoOperacion, Rol


def listar_roles(db: Session) -> list[Rol]:
    return list(db.scalars(select(Rol).order_by(Rol.nombre)))


def obtener_rol(db: Session, rol_id: int) -> Rol | None:
    return db.get(Rol, rol_id)


def rol_por_nombre(db: Session, nombre: str) -> Rol | None:
    return db.scalars(select(Rol).where(Rol.nombre == nombre)).first()


def crear_rol(db: Session, *, nombre: str, descripcion: str | None) -> Rol:
    rol = Rol(nombre=nombre, descripcion=descripcion)
    db.add(rol)
    db.flush()
    return rol


def listar_modulos(db: Session) -> list[Modulo]:
    return list(db.scalars(select(Modulo).order_by(Modulo.clave)))


def mapa_modulos(db: Session) -> dict[str, int]:
    return {m.clave: m.id for m in listar_modulos(db)}


def mapa_operaciones(db: Session) -> dict[str, int]:
    return {o.clave: o.id for o in db.scalars(select(Operacion))}


def matriz_rol(db: Session, rol_id: int) -> tuple[set[int], list[tuple[int, int]]]:
    """(modulo_ids con acceso, [(modulo_id, operacion_id)])."""
    modulos = set(
        db.scalars(select(PermisoModulo.modulo_id).where(PermisoModulo.rol_id == rol_id))
    )
    ops = [
        (r.modulo_id, r.operacion_id)
        for r in db.execute(
            select(PermisoOperacion.modulo_id, PermisoOperacion.operacion_id).where(
                PermisoOperacion.rol_id == rol_id
            )
        )
    ]
    return modulos, ops


def reemplazar_matriz(
    db: Session,
    rol_id: int,
    *,
    modulos_acceso: set[int],
    operaciones: set[tuple[int, int]],
) -> None:
    db.execute(delete(PermisoOperacion).where(PermisoOperacion.rol_id == rol_id))
    db.execute(delete(PermisoModulo).where(PermisoModulo.rol_id == rol_id))
    db.add_all(PermisoModulo(rol_id=rol_id, modulo_id=m) for m in modulos_acceso)
    db.add_all(
        PermisoOperacion(rol_id=rol_id, modulo_id=m, operacion_id=o) for m, o in operaciones
    )
    db.flush()
