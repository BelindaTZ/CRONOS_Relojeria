"""Cálculo puro del nivel de fidelización (feature 006, §4.8.1).

Función determinista y testeable con fixtures antes de que existan 008/009.
El nivel del cliente = el nivel de mayor `orden` cuya regla se cumple con su
histórico (compras 009 + servicios 008) dentro de la ventana. Si no cumple
ninguno, queda en el nivel base.

**Base de las transacciones (BR002)**: montos ya netos de anulaciones/devoluciones
(009 envía el reverso). Cuentan las compras confirmadas y los servicios entregados.
**Descenso de nivel (BR004)**: permitido e inmediato — el nivel siempre refleja la
ventana actual; no hay periodo de gracia (decisión del negocio, recálculo automático).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


def _restar_meses(d: date, meses: int) -> date:
    """`d` menos `meses` meses, sin dependencias externas (ajusta el día al fin de mes)."""
    total = (d.year * 12 + (d.month - 1)) - meses
    anio, mes = divmod(total, 12)
    mes += 1
    dia = min(d.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


@dataclass(frozen=True)
class TransaccionInfo:
    fecha: date
    monto: Decimal
    tipo: str  # "venta" | "servicio"


@dataclass(frozen=True)
class NivelRegla:
    nivel_id: int
    orden: int
    es_base: bool
    criterio: str | None            # None => el nivel no tiene regla (nunca se alcanza salvo base)
    ventana_meses: int
    umbral_monto: Decimal | None
    umbral_frecuencia: int | None


def _cumple(regla: NivelRegla, txs: list[TransaccionInfo], hoy: date) -> bool:
    if regla.criterio is None:
        return False
    desde = _restar_meses(hoy, regla.ventana_meses)
    en_ventana = [t for t in txs if desde <= t.fecha <= hoy]
    monto = sum((Decimal(str(t.monto)) for t in en_ventana), Decimal("0"))
    freq = len(en_ventana)

    cumple_monto = regla.umbral_monto is not None and monto >= Decimal(str(regla.umbral_monto))
    cumple_freq = regla.umbral_frecuencia is not None and freq >= regla.umbral_frecuencia

    if regla.criterio == "monto_acumulado":
        return cumple_monto
    if regla.criterio == "frecuencia":
        return cumple_freq
    if regla.criterio == "combinacion":
        return cumple_monto and cumple_freq
    return False


def calcular_nivel(
    transacciones: list[TransaccionInfo],
    niveles: list[NivelRegla],
    *,
    hoy: date | None = None,
) -> int | None:
    """Devuelve el `nivel_id` que le corresponde al cliente. `None` si no hay niveles."""
    if not niveles:
        return None
    hoy = hoy or date.today()
    ordenados = sorted(niveles, key=lambda n: n.orden, reverse=True)
    for regla in ordenados:
        if not regla.es_base and _cumple(regla, transacciones, hoy):
            return regla.nivel_id
    base = next((n for n in niveles if n.es_base), None)
    if base is not None:
        return base.nivel_id
    # sin base explícito: el de menor orden
    return min(niveles, key=lambda n: n.orden).nivel_id
