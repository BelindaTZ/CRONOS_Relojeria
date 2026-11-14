"""Autenticación: login, refresh, logout, cambio y restablecimiento de contraseña."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from auth import repository
from auth.schemas import AccessOut, TokenOut
from shared.auditoria import registrar_cambio
from shared.config import get_settings
from shared.correo import enviar
from shared.exceptions import DomainError, ValidationError
from shared.models import Usuario
from shared import ratelimit
from shared.security import (
    emitir_access_token,
    generar_password_temporal,
    hash_password,
    hash_token_opaco,
    nuevo_token_opaco,
    verify_password,
)


class CredencialesInvalidasError(DomainError):
    status_code = 401
    code = "credenciales_invalidas"


def _emitir_par(db: Session, usuario: Usuario) -> tuple[str, str]:
    s = get_settings()
    refresh = nuevo_token_opaco()
    repository.crear_refresh(
        db,
        usuario_id=usuario.id,
        token_hash=hash_token_opaco(refresh),
        expira_en=datetime.now(timezone.utc) + timedelta(days=s.refresh_token_ttl_days),
    )
    return emitir_access_token(usuario.id), refresh


def login(db: Session, *, identificacion: str, password: str, ip: str) -> TokenOut:
    clave_ident = f"login:{identificacion}"
    clave_ip = f"login-ip:{ip}"
    ratelimit.exigir_no_bloqueado(clave_ident)
    ratelimit.exigir_no_bloqueado(clave_ip)

    usuario = repository.usuario_por_identificacion(db, identificacion)
    if usuario is None or usuario.estado != "activo":
        ratelimit.registrar_fallo(clave_ident)
        ratelimit.registrar_fallo(clave_ip)
        raise CredencialesInvalidasError("Identificación o contraseña incorrectas")

    # ¿inicio de sesión con contraseña temporal vigente?
    solicitud = repository.solicitud_vigente(db, usuario.id)
    if solicitud and verify_password(password, solicitud.password_temporal_hash):
        solicitud.usada = True
        usuario.must_change_password = True
        # La temporal pasa a ser la contraseña "actual" hasta que el usuario fije
        # una nueva vía POST /auth/cambiar-contrasena (que exige la actual).
        usuario.password_hash = solicitud.password_temporal_hash
        repository.revocar_todos_refresh(db, usuario.id)
        db.flush()
        ratelimit.limpiar_exito(clave_ident)
        ratelimit.limpiar_exito(clave_ip)
        registrar_cambio(db, actor=usuario.id, accion="login", entidad="usuario", entidad_id=usuario.id, despues={"via": "password_temporal"})
        return TokenOut(
            access_token=emitir_access_token(usuario.id, scope="password_change"),
            refresh_token=None,
            must_change_password=True,
        )

    if not verify_password(password, usuario.password_hash):
        ratelimit.registrar_fallo(clave_ident)
        ratelimit.registrar_fallo(clave_ip)
        raise CredencialesInvalidasError("Identificación o contraseña incorrectas")

    ratelimit.limpiar_exito(clave_ident)
    ratelimit.limpiar_exito(clave_ip)

    if usuario.must_change_password:
        registrar_cambio(db, actor=usuario.id, accion="login", entidad="usuario", entidad_id=usuario.id, despues={"via": "forzado"})
        return TokenOut(
            access_token=emitir_access_token(usuario.id, scope="password_change"),
            refresh_token=None,
            must_change_password=True,
        )

    access, refresh = _emitir_par(db, usuario)
    registrar_cambio(db, actor=usuario.id, accion="login", entidad="usuario", entidad_id=usuario.id)
    return TokenOut(access_token=access, refresh_token=refresh, must_change_password=False)


def refresh(db: Session, *, refresh_token: str) -> AccessOut:
    row = repository.refresh_vigente(db, hash_token_opaco(refresh_token))
    if row is None:
        raise CredencialesInvalidasError("Refresh token inválido o revocado")
    return AccessOut(access_token=emitir_access_token(row.usuario_id))


def logout(db: Session, *, refresh_token: str | None, usuario_id: int) -> None:
    if refresh_token:
        repository.revocar_refresh(db, hash_token_opaco(refresh_token))
    else:
        repository.revocar_todos_refresh(db, usuario_id)


def cambiar_contrasena(db: Session, *, usuario_id: int, actual: str, nueva: str) -> None:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise CredencialesInvalidasError("Usuario inexistente")
    if not verify_password(actual, usuario.password_hash):
        raise ValidationError("La contraseña actual es incorrecta", field="actual")
    if verify_password(nueva, usuario.password_hash):
        raise ValidationError("La nueva contraseña debe ser distinta de la actual", field="nueva")
    usuario.password_hash = hash_password(nueva)
    usuario.must_change_password = False
    repository.revocar_todos_refresh(db, usuario_id)
    db.flush()
    registrar_cambio(db, actor=usuario_id, accion="cambiar_contrasena", entidad="usuario", entidad_id=usuario_id)


def solicitar_restablecimiento(db: Session, *, identificacion: str, ip: str) -> None:
    """Respuesta siempre neutra (no revela si el usuario existe). SEC003."""
    clave = f"reset:{identificacion}"
    ratelimit.exigir_no_bloqueado(clave)
    ratelimit.exigir_no_bloqueado(f"reset-ip:{ip}")
    ratelimit.registrar_fallo(clave)  # cada solicitud cuenta para el límite
    ratelimit.registrar_fallo(f"reset-ip:{ip}")

    usuario = repository.usuario_por_identificacion(db, identificacion)
    if usuario is None or usuario.estado != "activo" or not usuario.email:
        return

    s = get_settings()
    temporal = generar_password_temporal()
    expira = datetime.now(timezone.utc) + timedelta(hours=s.password_reset_ttl_hours)
    repository.crear_solicitud(
        db, usuario_id=usuario.id, hash_=hash_password(temporal), expira_en=expira
    )
    registrar_cambio(
        db, actor=usuario.id, accion="reset_password", entidad="usuario", entidad_id=usuario.id,
        despues={"expira_en": expira.isoformat()},
    )
    enviar(
        "password_temporal",
        usuario.email,
        {
            "nombre": usuario.nombre,
            "password_temporal": temporal,
            "expira_en": expira.strftime("%Y-%m-%d %H:%M UTC"),
        },
    )
