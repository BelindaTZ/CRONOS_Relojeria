"""Motor de parámetros y recálculo en cascada.

Regla del negocio (Const. "Parámetros configurables"): al fijar un valor nuevo se
recalcula TODO lo *abierto* que depende de él (bonos de periodos no cerrados,
márgenes de operaciones no confirmadas/no entregadas, niveles de fidelización,
reportes). Los documentos legales emitidos y los periodos contables cerrados
conservan su valor histórico. Todo el efecto queda auditado por el llamador.

Cada feature consumidora (005/006/008/009/010) se registra con
`registrar_consumidor(clave, fn)`; `fn(db, clave) -> int` recalcula sus entidades
abiertas y devuelve cuántas tocó. En 001 no hay consumidores todavía.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from shared.exceptions import ValidationError
from shared.parametros import repository

Consumidor = Callable[[Session, str], int]
_CONSUMIDORES: dict[str, list[tuple[str, Consumidor]]] = {}

_TIPOS = {"numero", "porcentaje", "monto", "json", "texto"}
_AMBITOS = {"global", "sucursal", "marca", "producto", "tipo_servicio"}


@dataclass
class ResumenRecalculo:
    consumidores: list[str] = field(default_factory=list)
    entidades_abiertas_afectadas: int = 0
    documentos_emitidos_intactos: int = 0


def registrar_consumidor(clave: str, fn: Consumidor, *, nombre: str | None = None) -> None:
    _CONSUMIDORES.setdefault(clave, []).append((nombre or getattr(fn, "__name__", "consumidor"), fn))


_SIN_VALOR = object()


def get_parametro(
    db: Session,
    clave: str,
    *,
    ambito_tipo: str = "global",
    ambito_ref: str | None = None,
    en_fecha: datetime | None = None,
    default: Any = None,
    fallback_global: bool = True,
) -> Any:
    row = repository.vigente(
        db, clave, ambito_tipo=ambito_tipo, ambito_ref=ambito_ref, en_fecha=en_fecha
    )
    if row is None:
        # fallback al ámbito global si se pidió uno específico
        if ambito_tipo != "global" and fallback_global:
            return get_parametro(db, clave, en_fecha=en_fecha, default=default)
        return default
    return row.valor


def _recalcular(db: Session, clave: str) -> ResumenRecalculo:
    resumen = ResumenRecalculo()
    for nombre, fn in _CONSUMIDORES.get(clave, []):
        afectadas = fn(db, clave)
        resumen.consumidores.append(nombre)
        resumen.entidades_abiertas_afectadas += int(afectadas or 0)
    return resumen


def set_parametro(
    db: Session,
    *,
    clave: str,
    valor: Any,
    tipo: str = "numero",
    ambito_tipo: str = "global",
    ambito_ref: str | None = None,
    vigente_desde: datetime | None = None,
    actor: int | None = None,
) -> tuple[Any, ResumenRecalculo]:
    """Inserta un valor vigente nuevo (no destruye historial) y dispara el recálculo.

    Devuelve (valor_anterior, ResumenRecalculo). El llamador registra la auditoría.
    """
    if tipo not in _TIPOS:
        raise ValidationError(f"tipo de parámetro inválido: {tipo}", field="tipo")
    if ambito_tipo not in _AMBITOS:
        raise ValidationError(f"ámbito inválido: {ambito_tipo}", field="ambito_tipo")
    if (ambito_tipo == "global") != (ambito_ref is None):
        raise ValidationError(
            "ambito_ref debe ser nulo solo cuando ambito_tipo es 'global'", field="ambito_ref"
        )

    anterior_row = repository.vigente(db, clave, ambito_tipo=ambito_tipo, ambito_ref=ambito_ref)
    anterior = anterior_row.valor if anterior_row else None

    repository.insertar(
        db,
        clave=clave,
        tipo=tipo,
        valor=valor,
        ambito_tipo=ambito_tipo,
        ambito_ref=ambito_ref,
        vigente_desde=vigente_desde or datetime.now(timezone.utc),
        creado_por=actor,
    )

    resumen = _recalcular(db, clave)
    return anterior, resumen
