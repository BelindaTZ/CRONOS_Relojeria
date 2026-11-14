"""Servicio de auditoría — API pública `registrar_cambio`.

Lo invocan los services de negocio en todo cambio de permisos, catálogos,
parámetros, inactivación de sucursal y autoservicio de usuario (data-model §5).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from shared.auditoria import repository
from shared.request_context import get_ip_origen


def _jsonable(v: Any) -> Any:
    """Normaliza valores a algo serializable en JSONB (fechas → ISO, etc.)."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def registrar_cambio(
    db: Session,
    *,
    actor: int | None,
    accion: str,
    entidad: str,
    entidad_id: str | int | None = None,
    antes: Any | None = None,
    despues: Any | None = None,
) -> None:
    repository.insertar(
        db,
        actor_usuario_id=actor,
        accion=accion,
        entidad=entidad,
        entidad_id=None if entidad_id is None else str(entidad_id),
        antes=_jsonable(antes),
        despues=_jsonable(despues),
        ip_origen=get_ip_origen(),
    )
