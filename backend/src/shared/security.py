"""Primitivas de seguridad compartidas: hash de contraseñas y JWT de acceso.

Vive en `shared/` porque tanto `auth` (emite) como `guard` (verifica) lo usan.
Secretos y parámetros vienen de `shared.config` (Principio IX).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from shared.config import get_settings

# bcrypt opera sobre 72 bytes como máximo; normalizamos para no perder
# determinismo entre hash y verificación.
_BCRYPT_MAX = 72


def _prep(plano: str) -> bytes:
    return plano.encode("utf-8")[:_BCRYPT_MAX]


# --------------------------------------------------------------------- contraseñas
def hash_password(plano: str) -> str:
    return bcrypt.hashpw(_prep(plano), bcrypt.gensalt()).decode("ascii")


def verify_password(plano: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(_prep(plano), hash_.encode("ascii"))
    except (ValueError, TypeError):
        return False


def generar_password_temporal(longitud: int = 12) -> str:
    """Contraseña temporal legible (sin caracteres ambiguos)."""
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))


# ---------------------------------------------------------------- tokens opacos
def nuevo_token_opaco() -> str:
    return secrets.token_urlsafe(48)


def hash_token_opaco(token: str) -> str:
    """SHA-256 con clave (no reversible; suficiente para refresh/temporal en DB)."""
    s = get_settings()
    return hmac.new(s.jwt_secret.encode(), token.encode(), hashlib.sha256).hexdigest()


# ------------------------------------------------------------------------- JWT
class TokenInvalido(Exception):
    """El JWT de acceso es inválido, está expirado o mal formado."""


def emitir_access_token(usuario_id: int, *, scope: str = "full") -> str:
    """`scope='password_change'` restringe el token al cambio de contraseña forzado."""
    s = get_settings()
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "scope": scope,
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + timedelta(minutes=s.access_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decodificar_access_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError as exc:  # noqa: TRY003
        raise TokenInvalido(str(exc)) from exc
