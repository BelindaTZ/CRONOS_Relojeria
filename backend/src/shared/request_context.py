"""Contexto de la petición HTTP en curso, accesible desde capas que no reciben
el `Request` (p. ej. la auditoría llamada desde un service).

`main.py` instala un middleware que fija `ip_origen` por petición; `registrar_cambio`
lo lee sin cambiar su firma ni la de las decenas de llamadas existentes.
"""

from __future__ import annotations

from contextvars import ContextVar

_ip_origen: ContextVar[str | None] = ContextVar("cronos_ip_origen", default=None)


def set_ip_origen(ip: str | None) -> None:
    _ip_origen.set(ip)


def get_ip_origen() -> str | None:
    return _ip_origen.get()
