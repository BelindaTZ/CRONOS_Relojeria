"""Lógica del módulo RBAC: roles y la matriz de permisos de dos niveles."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from rbac import repository
from rbac.schemas import ModuloOut, PermisoModuloIn, PermisoModuloOut, RolIn, RolOut
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import invalidar_cache
from shared.models import Operacion


def listar_roles(db: Session) -> list[RolOut]:
    return [RolOut(id=r.id, nombre=r.nombre, descripcion=r.descripcion) for r in repository.listar_roles(db)]


def crear_rol(db: Session, datos: RolIn, *, actor: int) -> RolOut:
    if repository.rol_por_nombre(db, datos.nombre):
        raise ConflictError(f"Ya existe un rol '{datos.nombre}'", field="nombre")
    rol = repository.crear_rol(db, nombre=datos.nombre, descripcion=datos.descripcion)
    registrar_cambio(db, actor=actor, accion="crear", entidad="rol", entidad_id=rol.id, despues=datos.model_dump())
    return RolOut(id=rol.id, nombre=rol.nombre, descripcion=rol.descripcion)


def listar_modulos(db: Session) -> list[ModuloOut]:
    return [ModuloOut(id=m.id, clave=m.clave, nombre=m.nombre) for m in repository.listar_modulos(db)]


def get_permisos_rol(db: Session, rol_id: int) -> list[PermisoModuloOut]:
    if repository.obtener_rol(db, rol_id) is None:
        raise NotFoundError("Rol no encontrado")
    mods = repository.listar_modulos(db)
    ops = {o.id: o.clave for o in db.scalars(select(Operacion))}
    modulos_acceso, op_pairs = repository.matriz_rol(db, rol_id)
    by_mod: dict[int, set[str]] = {}
    for m_id, o_id in op_pairs:
        by_mod.setdefault(m_id, set()).add(ops.get(o_id, ""))
    salida = []
    for m in mods:
        if m.id in modulos_acceso or m.id in by_mod:
            salida.append(
                PermisoModuloOut(
                    modulo=m.clave,
                    acceso=m.id in modulos_acceso,
                    operaciones=sorted(x for x in by_mod.get(m.id, set()) if x),
                )
            )
    return salida


def set_permisos_rol(
    db: Session, rol_id: int, entradas: list[PermisoModuloIn], *, actor: int
) -> list[PermisoModuloOut]:
    rol = repository.obtener_rol(db, rol_id)
    if rol is None:
        raise NotFoundError("Rol no encontrado")

    mapa_mod = repository.mapa_modulos(db)
    mapa_op = repository.mapa_operaciones(db)

    modulos_acceso: set[int] = set()
    operaciones: set[tuple[int, int]] = set()

    for e in entradas:
        if e.modulo not in mapa_mod:
            raise ValidationError(f"Módulo desconocido: {e.modulo}", field="modulo")
        m_id = mapa_mod[e.modulo]
        if e.acceso:
            modulos_acceso.add(m_id)
        # el acceso al módulo es prerrequisito de cualquier operación (FR-005)
        if e.operaciones and not e.acceso:
            raise ValidationError(
                f"'{e.modulo}': marcaste operaciones sin habilitar el acceso al módulo",
                field="acceso",
            )
        for op in e.operaciones:
            operaciones.add((m_id, mapa_op[op]))

    antes = get_permisos_rol(db, rol_id)
    repository.reemplazar_matriz(
        db, rol_id, modulos_acceso=modulos_acceso, operaciones=operaciones
    )
    invalidar_cache(rol_id)
    registrar_cambio(
        db,
        actor=actor,
        accion="editar",
        entidad="permisos_rol",
        entidad_id=rol_id,
        antes=[a.model_dump() for a in antes],
        despues=[e.model_dump() for e in entradas],
    )
    return get_permisos_rol(db, rol_id)
