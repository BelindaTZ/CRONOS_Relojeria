"""Anti fuerza bruta en proceso (FR-027). Ventana deslizante + bloqueo temporal.

Suficiente para el despliegue monositio de desarrollo; en producción multi-nodo
se sustituiría por un almacén compartido (Redis). No hay estado persistente.
"""

from __future__ import annotations

import time

from shared.config import get_settings
from shared.exceptions import DomainError

_intentos: dict[str, list[float]] = {}
_bloqueos: dict[str, float] = {}


class DemasiadosIntentosError(DomainError):
    status_code = 429
    code = "rate_limited"


def _limpiar(clave: str, ventana: float, ahora: float) -> None:
    _intentos[clave] = [t for t in _intentos.get(clave, []) if ahora - t < ventana]


def registrar_fallo(clave: str) -> None:
    s = get_settings()
    ahora = time.monotonic()
    _limpiar(clave, s.login_ventana_segundos, ahora)
    _intentos.setdefault(clave, []).append(ahora)
    if len(_intentos[clave]) >= s.login_max_intentos:
        _bloqueos[clave] = ahora + s.login_bloqueo_segundos
        _intentos[clave] = []


def limpiar_exito(clave: str) -> None:
    _intentos.pop(clave, None)
    _bloqueos.pop(clave, None)


def exigir_no_bloqueado(clave: str) -> None:
    fin = _bloqueos.get(clave)
    if fin is None:
        return
    if time.monotonic() < fin:
        raise DemasiadosIntentosError("Demasiados intentos. Inténtalo más tarde.")
    _bloqueos.pop(clave, None)
