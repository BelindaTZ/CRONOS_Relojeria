"""Usuarios: autoservicio (email/foto propios) + administración (roles, sucursales,
excepciones, activación) con candado anti-lockout de Gerencia General (FR-026)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.correo import enviar
from shared.guard import CurrentUser, invalidar_cache, permisos_efectivos
from shared.models import Usuario
from shared.security import generar_password_temporal, hash_password
from shared.storage import get_object_url, put_object
from usuarios import repository
from usuarios.schemas import PerfilOut, UsuarioIn, UsuarioOut, UsuarioPatch

_BUCKET_PERFIL = "perfil-usuarios"


def _perfil_out(db: Session, u: Usuario, *, user: CurrentUser) -> PerfilOut:
    return PerfilOut(
        id=u.id,
        identificacion=u.identificacion,
        nombre=u.nombre,
        roles=repository.roles_de(db, u.id),
        sucursales=repository.sucursales_de(db, u.id),
        sucursal_ids=repository.sucursal_ids_de(db, u.id),
        email=u.email,
        foto_perfil_url=(
            get_object_url(_BUCKET_PERFIL, u.foto_perfil_objeto) if u.foto_perfil_objeto else None
        ),
        permisos=permisos_efectivos(db, user),
    )


def _usuario_out(db: Session, u: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=u.id,
        identificacion=u.identificacion,
        nombre=u.nombre,
        email=u.email,
        estado=u.estado,
        roles=repository.roles_de(db, u.id),
        sucursales=repository.sucursales_de(db, u.id),
    )


# ------------------------------------------------------------------- autoservicio
def get_perfil(db: Session, user: CurrentUser) -> PerfilOut:
    u = repository.obtener(db, user.id)
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    return _perfil_out(db, u, user=user)


def update_perfil(
    db: Session,
    user: CurrentUser,
    *,
    email: str | None,
    foto: tuple[bytes, str] | None,
) -> PerfilOut:
    """SOLO email y foto (FR-011). Cualquier otro campo se ignora."""
    usuario_id = user.id
    u = repository.obtener(db, usuario_id)
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    antes = {"email": u.email, "foto": u.foto_perfil_objeto}

    if email and email.lower() != u.email.lower():
        otro = repository.por_email(db, email)
        if otro and otro.id != u.id:
            raise ConflictError("Ese email ya está en uso", field="email")
        u.email = email

    if foto is not None:
        data, content_type = foto
        if not content_type.startswith("image/"):
            raise ValidationError("La foto debe ser una imagen", field="foto")
        clave = f"{u.id}/{uuid.uuid4().hex}"
        put_object(_BUCKET_PERFIL, clave, data, content_type=content_type)
        u.foto_perfil_objeto = clave

    db.flush()
    registrar_cambio(
        db, actor=usuario_id, accion="editar", entidad="usuario_autoservicio",
        entidad_id=usuario_id, antes=antes, despues={"email": u.email, "foto": u.foto_perfil_objeto},
    )
    return _perfil_out(db, u, user=user)


# ------------------------------------------------------------------- administración
def listar(db: Session, *, q: str | None, offset: int, limit: int) -> tuple[list[UsuarioOut], int]:
    filas, total = repository.buscar(db, q, offset, limit)
    return [_usuario_out(db, u) for u in filas], total


def crear(db: Session, datos: UsuarioIn, *, actor: int) -> UsuarioOut:
    if repository.por_identificacion(db, datos.identificacion):
        raise ConflictError("Ya existe un usuario con esa identificación", field="identificacion")
    if repository.por_email(db, datos.email):
        raise ConflictError("Ya existe un usuario con ese email", field="email")

    temporal = generar_password_temporal()
    u = repository.crear(
        db,
        identificacion=datos.identificacion,
        nombre=datos.nombre,
        email=datos.email,
        password_hash=hash_password(temporal),
        estado="activo",
        must_change_password=True,
    )
    if datos.rol_ids:
        repository.set_roles(db, u.id, datos.rol_ids)
    if datos.sucursal_ids:
        repository.set_sucursales(db, u.id, datos.sucursal_ids)
    registrar_cambio(db, actor=actor, accion="crear", entidad="usuario", entidad_id=u.id,
                     despues={"identificacion": datos.identificacion, "email": datos.email})
    try:
        enviar("usuario_bienvenida", u.email, {"nombre": u.nombre, "password_temporal": temporal})
    except Exception:  # noqa: BLE001
        pass  # el gerente igual ve la temporal en pantalla

    out = _usuario_out(db, u)
    out.password_temporal = temporal  # mostrar una sola vez
    return out


def actualizar(db: Session, usuario_id: int, datos: UsuarioPatch, *, actor: int) -> UsuarioOut:
    u = repository.obtener(db, usuario_id)
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    antes = {"nombre": u.nombre, "email": u.email, "estado": u.estado}

    if datos.estado == "inactivo" and u.estado == "activo":
        _exigir_no_ultimo_gerencia(db, usuario_id, "desactivar")
    if datos.nombre is not None:
        u.nombre = datos.nombre
    if datos.email is not None and datos.email.lower() != u.email.lower():
        if repository.por_email(db, datos.email):
            raise ConflictError("Ese email ya está en uso", field="email")
        u.email = datos.email
    if datos.estado is not None:
        u.estado = datos.estado
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="usuario", entidad_id=usuario_id,
                     antes=antes, despues={"nombre": u.nombre, "email": u.email, "estado": u.estado})
    return _usuario_out(db, u)


def set_roles(db: Session, usuario_id: int, rol_ids: list[int], *, actor: int) -> UsuarioOut:
    u = repository.obtener(db, usuario_id)
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    # anti-lockout: si el usuario ES el último Gerencia General activo y el nuevo
    # set de roles no incluye Gerencia General -> bloquear
    from rbac import repository as rbac_repo

    gerencia = rbac_repo.rol_por_nombre(db, repository.ROL_GERENCIA)
    if (
        gerencia is not None
        and repository.tiene_rol_gerencia(db, usuario_id)
        and gerencia.id not in rol_ids
    ):
        _exigir_no_ultimo_gerencia(db, usuario_id, "quitar el rol Gerencia General")

    antes = repository.roles_de(db, usuario_id)
    repository.set_roles(db, usuario_id, rol_ids)
    registrar_cambio(db, actor=actor, accion="editar", entidad="usuario_roles", entidad_id=usuario_id,
                     antes=antes, despues=repository.roles_de(db, usuario_id))
    return _usuario_out(db, u)


def set_sucursales(db: Session, usuario_id: int, sucursal_ids: list[int], *, actor: int) -> UsuarioOut:
    u = repository.obtener(db, usuario_id)
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    antes = repository.sucursales_de(db, usuario_id)
    repository.set_sucursales(db, usuario_id, sucursal_ids)
    registrar_cambio(db, actor=actor, accion="editar", entidad="usuario_sucursales", entidad_id=usuario_id,
                     antes=antes, despues=repository.sucursales_de(db, usuario_id))
    return _usuario_out(db, u)


def set_excepciones(db: Session, usuario_id: int, entradas: list[dict], *, actor: int) -> None:
    if repository.obtener(db, usuario_id) is None:
        raise NotFoundError("Usuario no encontrado")
    repository.set_excepciones(db, usuario_id, entradas)
    invalidar_cache()
    registrar_cambio(db, actor=actor, accion="editar", entidad="permiso_usuario",
                     entidad_id=usuario_id, despues=entradas)


def _exigir_no_ultimo_gerencia(db: Session, usuario_id: int, accion: str) -> None:
    if repository.contar_gerencia_activos(db, excluir_usuario=usuario_id) == 0:
        raise ConflictError(
            f"No se puede {accion}: es el único usuario Gerencia General activo",
        )
