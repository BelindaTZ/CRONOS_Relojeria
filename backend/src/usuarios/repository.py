from __future__ import annotations

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from shared.models import (
    Modulo,
    Operacion,
    PermisoUsuario,
    Rol,
    Sucursal,
    Usuario,
    UsuarioRol,
    UsuarioSucursal,
)

ROL_GERENCIA = "Gerencia General"


def obtener(db: Session, usuario_id: int) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def por_email(db: Session, email: str) -> Usuario | None:
    return db.scalars(select(Usuario).where(func.lower(Usuario.email) == email.lower())).first()


def por_identificacion(db: Session, ident: str) -> Usuario | None:
    return db.scalars(select(Usuario).where(Usuario.identificacion == ident)).first()


def roles_de(db: Session, usuario_id: int) -> list[str]:
    return list(
        db.scalars(
            select(Rol.nombre)
            .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
            .where(UsuarioRol.usuario_id == usuario_id)
        )
    )


def sucursales_de(db: Session, usuario_id: int) -> list[str]:
    return list(
        db.scalars(
            select(Sucursal.nombre)
            .join(UsuarioSucursal, UsuarioSucursal.sucursal_id == Sucursal.id)
            .where(UsuarioSucursal.usuario_id == usuario_id)
        )
    )


def sucursal_ids_de(db: Session, usuario_id: int) -> list[int]:
    return list(
        db.scalars(
            select(UsuarioSucursal.sucursal_id).where(UsuarioSucursal.usuario_id == usuario_id)
        )
    )


def buscar(db: Session, q: str | None, offset: int, limit: int) -> tuple[list[Usuario], int]:
    filtros = []
    if q:
        like = f"%{q}%"
        filtros.append(
            or_(Usuario.nombre.ilike(like), Usuario.identificacion.ilike(like), Usuario.email.ilike(like))
        )
    total = db.scalar(select(func.count()).select_from(Usuario).where(*filtros)) or 0
    filas = list(
        db.scalars(select(Usuario).where(*filtros).order_by(Usuario.nombre).offset(offset).limit(limit))
    )
    return filas, int(total)


def crear(db: Session, **campos) -> Usuario:
    u = Usuario(**campos)
    db.add(u)
    db.flush()
    return u


def set_roles(db: Session, usuario_id: int, rol_ids: list[int]) -> None:
    db.execute(delete(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id))
    db.add_all(UsuarioRol(usuario_id=usuario_id, rol_id=r) for r in dict.fromkeys(rol_ids))
    db.flush()


def set_sucursales(db: Session, usuario_id: int, sucursal_ids: list[int]) -> None:
    db.execute(delete(UsuarioSucursal).where(UsuarioSucursal.usuario_id == usuario_id))
    db.add_all(UsuarioSucursal(usuario_id=usuario_id, sucursal_id=s) for s in dict.fromkeys(sucursal_ids))
    db.flush()


def set_excepciones(db: Session, usuario_id: int, entradas: list[dict]) -> None:
    db.execute(delete(PermisoUsuario).where(PermisoUsuario.usuario_id == usuario_id))
    mods = {m.clave: m.id for m in db.scalars(select(Modulo))}
    ops = {o.clave: o.id for o in db.scalars(select(Operacion))}
    for e in entradas:
        db.add(
            PermisoUsuario(
                usuario_id=usuario_id,
                modulo_id=mods[e["modulo"]],
                operacion_id=ops[e["operacion"]] if e.get("operacion") else None,
                efecto=e["efecto"],
            )
        )
    db.flush()


def contar_gerencia_activos(db: Session, excluir_usuario: int | None = None) -> int:
    stmt = (
        select(func.count(func.distinct(Usuario.id)))
        .select_from(Usuario)
        .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
        .join(Rol, Rol.id == UsuarioRol.rol_id)
        .where(Rol.nombre == ROL_GERENCIA, Usuario.estado == "activo")
    )
    if excluir_usuario is not None:
        stmt = stmt.where(Usuario.id != excluir_usuario)
    return int(db.scalar(stmt) or 0)


def tiene_rol_gerencia(db: Session, usuario_id: int) -> bool:
    return bool(
        db.scalar(
            select(func.count())
            .select_from(UsuarioRol)
            .join(Rol, Rol.id == UsuarioRol.rol_id)
            .where(UsuarioRol.usuario_id == usuario_id, Rol.nombre == ROL_GERENCIA)
        )
    )
