"""Guard RBAC de dos niveles + scoping de datos (Constitución, Principio IV — NON-NEGOTIABLE).

- `require_perm(modulo, operacion)` — dependencia FastAPI que autoriza un endpoint:
  401 sin token válido, 403 sin acceso a módulo o sin la operación.
  El acceso al módulo es prerrequisito de la operación.
- `get_current_user` — solo exige autenticación (para `/perfil`, cambio de contraseña).
- `scope_sucursal(stmt, user, campo)` / `scope_propiedad(stmt, user, campo)` — helpers
  reutilizables por las features 002+ para limitar el alcance de una consulta.

La autorización se evalúa SIEMPRE contra los permisos vigentes (FR-010). El JWT
solo transporta el `user_id`. La matriz rol→permiso se cachea en proceso con TTL
corto e invalidación explícita al guardar la matriz.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.exceptions import DomainError
from shared.models import (
    Modulo,
    Operacion,
    PermisoModulo,
    PermisoOperacion,
    PermisoUsuario,
    Rol,
    Usuario,
    UsuarioRol,
    UsuarioSucursal,
)
from shared.security import TokenInvalido, decodificar_access_token

ROL_GERENCIA = "Gerencia General"


class NoAutenticadoError(DomainError):
    status_code = 401
    code = "no_autenticado"


class NoAutorizadoError(DomainError):
    status_code = 403
    code = "no_autorizado"


@dataclass
class CurrentUser:
    id: int
    identificacion: str
    nombre: str
    email: str
    estado: str
    token_scope: str
    roles: list[str] = field(default_factory=list)
    rol_ids: list[int] = field(default_factory=list)
    sucursal_ids: list[int] = field(default_factory=list)

    @property
    def es_gerencia(self) -> bool:
        return ROL_GERENCIA in self.roles


# --------------------------------------------------------------- caché de la matriz
_TTL = 30.0  # segundos
_cache: dict[int, tuple[float, dict[str, set[str]], set[str]]] = {}


def invalidar_cache(rol_id: int | None = None) -> None:
    """Llamar al guardar `permiso_modulo`/`permiso_operacion` de un rol."""
    if rol_id is None:
        _cache.clear()
    else:
        _cache.pop(rol_id, None)


def _matriz_rol(db: Session, rol_id: int) -> tuple[dict[str, set[str]], set[str]]:
    """(operaciones_por_modulo, modulos_con_acceso) para un rol. Cacheado."""
    hit = _cache.get(rol_id)
    if hit and (time.monotonic() - hit[0]) < _TTL:
        return hit[1], hit[2]

    modulos_acceso: set[str] = set(
        db.scalars(
            select(Modulo.clave)
            .join(PermisoModulo, PermisoModulo.modulo_id == Modulo.id)
            .where(PermisoModulo.rol_id == rol_id)
        )
    )
    ops: dict[str, set[str]] = {}
    filas = db.execute(
        select(Modulo.clave, Operacion.clave)
        .join(PermisoOperacion, PermisoOperacion.modulo_id == Modulo.id)
        .join(Operacion, Operacion.id == PermisoOperacion.operacion_id)
        .where(PermisoOperacion.rol_id == rol_id)
    ).all()
    for mod_clave, op_clave in filas:
        ops.setdefault(mod_clave, set()).add(op_clave)

    _cache[rol_id] = (time.monotonic(), ops, modulos_acceso)
    return ops, modulos_acceso


def _overrides_usuario(db: Session, usuario_id: int) -> dict[tuple[str, str | None], str]:
    """{(modulo_clave, operacion_clave|None): 'conceder'|'revocar'}."""
    filas = db.execute(
        select(Modulo.clave, Operacion.clave, PermisoUsuario.efecto)
        .select_from(PermisoUsuario)
        .join(Modulo, Modulo.id == PermisoUsuario.modulo_id)
        .join(Operacion, Operacion.id == PermisoUsuario.operacion_id, isouter=True)
        .where(PermisoUsuario.usuario_id == usuario_id)
    ).all()
    return {(m, o): efecto for m, o, efecto in filas}


# ----------------------------------------------------------------- resolución
def _tiene_acceso_modulo(db: Session, user: CurrentUser, modulo: str, ov: dict) -> bool:
    if ov.get((modulo, None)) == "revocar":
        return False
    if ov.get((modulo, None)) == "conceder":
        return True
    for rid in user.rol_ids:
        _, modulos = _matriz_rol(db, rid)
        if modulo in modulos:
            return True
    return False


def _tiene_operacion(db: Session, user: CurrentUser, modulo: str, operacion: str, ov: dict) -> bool:
    if ov.get((modulo, operacion)) == "revocar":
        return False
    if ov.get((modulo, operacion)) == "conceder":
        return True
    for rid in user.rol_ids:
        ops, _ = _matriz_rol(db, rid)
        if operacion in ops.get(modulo, set()):
            return True
    return False


def permisos_efectivos(db: Session, user: CurrentUser) -> dict[str, list[str]]:
    """Módulos a los que `user` tiene acceso y, por cada uno, sus operaciones
    permitidas (roles + overrides individuales ya resueltos). Se expone en
    `/perfil` para que el FRONTEND pinte nav y rutas según el usuario real —
    la autorización de cada endpoint la sigue decidiendo `require_perm`, esto
    es solo el reflejo de esa misma resolución para la UI (Principio IV)."""
    if user.es_gerencia:
        # Atajo: Gerencia General ve/opera todo por construcción del sistema
        # (constitución §4/§9) — evita 15×4 checks para el rol más usado.
        modulos = list(db.scalars(select(Modulo.clave)))
        operaciones = list(db.scalars(select(Operacion.clave)))
        return {m: list(operaciones) for m in modulos}

    ov = _overrides_usuario(db, user.id)
    modulos = list(db.scalars(select(Modulo.clave)))
    operaciones = list(db.scalars(select(Operacion.clave)))
    out: dict[str, list[str]] = {}
    for modulo in modulos:
        if not _tiene_acceso_modulo(db, user, modulo, ov):
            continue
        out[modulo] = [op for op in operaciones if _tiene_operacion(db, user, modulo, op, ov)]
    return out


# --------------------------------------------------------------- dependencias
def _extraer_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise NoAutenticadoError("Falta el token de acceso")
    return auth[7:].strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    token = _extraer_bearer(request)
    try:
        payload = decodificar_access_token(token)
    except TokenInvalido as exc:
        raise NoAutenticadoError("Token inválido o expirado") from exc

    usuario_id = int(payload.get("sub", 0))
    u = db.get(Usuario, usuario_id)
    if u is None or u.estado != "activo":
        raise NoAutenticadoError("Usuario inexistente o inactivo")

    roles = db.execute(
        select(Rol.id, Rol.nombre)
        .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
        .where(UsuarioRol.usuario_id == usuario_id)
    ).all()
    sucursales = list(
        db.scalars(
            select(UsuarioSucursal.sucursal_id).where(UsuarioSucursal.usuario_id == usuario_id)
        )
    )
    return CurrentUser(
        id=u.id,
        identificacion=u.identificacion,
        nombre=u.nombre,
        email=u.email,
        estado=u.estado,
        token_scope=payload.get("scope", "full"),
        roles=[r.nombre for r in roles],
        rol_ids=[r.id for r in roles],
        sucursal_ids=sucursales,
    )


def get_current_user_full_scope(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Rechaza el token restringido de 'cambio de contraseña forzado'."""
    if user.token_scope != "full":
        raise NoAutorizadoError("Debes fijar una contraseña nueva antes de continuar")
    return user


def require_perm(modulo: str, operacion: str):
    """Dependencia: exige (acceso a `modulo`) y (`operacion` en ese módulo)."""

    def _dep(
        user: CurrentUser = Depends(get_current_user_full_scope),
        db: Session = Depends(get_db),
    ) -> CurrentUser:
        ov = _overrides_usuario(db, user.id)
        if not _tiene_acceso_modulo(db, user, modulo, ov):
            raise NoAutorizadoError(f"Sin acceso al módulo '{modulo}'")
        if not _tiene_operacion(db, user, modulo, operacion, ov):
            raise NoAutorizadoError(f"Sin permiso para '{operacion}' en '{modulo}'")
        return user

    return _dep


def require_gerencia_o_delegado(
    user: CurrentUser = Depends(get_current_user_full_scope),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Configuración (FR-024): solo Gerencia General o quien tenga la delegación
    explícita (override `conceder` sobre el módulo `configuracion`)."""
    if user.es_gerencia:
        return user
    ov = _overrides_usuario(db, user.id)
    if ov.get(("configuracion", None)) == "conceder":
        return user
    raise NoAutorizadoError("Solo Gerencia General o un delegado explícito")


# ------------------------------------------------------------------- scoping
def scope_sucursal(stmt, user: CurrentUser, campo):
    """Limita `stmt` a las sucursales del usuario. Gerencia General ve consolidado."""
    if user.es_gerencia:
        return stmt
    if not user.sucursal_ids:
        raise NoAutorizadoError("El usuario no tiene ninguna sucursal asignada")
    return stmt.where(campo.in_(user.sucursal_ids))


def scope_propiedad(stmt, user: CurrentUser, campo):
    """Limita `stmt` a los registros cuyo `campo` (owner) es el usuario actual.
    Gerencia General ve todo."""
    if user.es_gerencia:
        return stmt
    return stmt.where(campo == user.id)
