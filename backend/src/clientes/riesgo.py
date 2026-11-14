"""Análisis de riesgo de abandono de un cliente (feature 006, ampliación 2026-09-10).

Detecta clientes de niveles con valor (Plata/Oro — todo nivel no base) cuyo
**patrón propio de compra** indica un silencio anómalo, para emitirles un cupón de
reactivación (§4.8.2 "cupón de reactivación para clientes inactivos").

Método (confirmado por el usuario):
- Se toma la cadencia **mediana** entre transacciones (compras 009 + servicios 008)
  del cliente dentro de una ventana (`churn_ventana_analisis_meses`, def. 24).
- Se exige un historial mínimo (`churn_min_transacciones`, def. 3) para que exista
  un patrón.
- El cliente está **en riesgo** si su silencio actual (días desde la última
  transacción) supera `churn_factor_cadencia` × su cadencia **y** además supera un
  piso mínimo de días (`churn_piso_dias`, def. 90) — así un cliente que compra cada
  15 días y lleva 40 en silencio no se marca todavía.

Función pura, testeable con fixtures antes de que existan 008/009.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from clientes.nivel import _restar_meses


@dataclass(frozen=True)
class RiesgoAbandono:
    cadencia_dias: float
    dias_silencio: int
    ratio: float               # dias_silencio / cadencia_dias
    severidad: str             # "atencion" | "critico"
    ultima_fecha: date
    n_transacciones: int


@dataclass(frozen=True)
class TransaccionRiesgo:
    fecha: date


def analizar(
    transacciones: list[TransaccionRiesgo],
    *,
    hoy: date,
    piso_dias: int = 90,
    factor_cadencia: float = 2.0,
    min_transacciones: int = 3,
    ventana_meses: int = 24,
) -> RiesgoAbandono | None:
    """Devuelve `RiesgoAbandono` si el cliente está en riesgo; `None` en caso contrario."""
    desde = _restar_meses(hoy, ventana_meses)
    txs = sorted(
        (t.fecha for t in transacciones if desde <= t.fecha <= hoy)
    )
    if len(txs) < min_transacciones:
        return None

    intervalos = [(txs[i + 1] - txs[i]).days for i in range(len(txs) - 1)]
    intervalos = [d for d in intervalos if d > 0]
    if not intervalos:
        return None
    cadencia = float(statistics.median(intervalos)) or 1.0

    ultima = txs[-1]
    silencio = (hoy - ultima).days
    if silencio < piso_dias:
        return None
    if silencio < factor_cadencia * cadencia:
        return None

    ratio = silencio / cadencia
    severidad = "critico" if ratio >= 2 * factor_cadencia else "atencion"
    return RiesgoAbandono(
        cadencia_dias=round(cadencia, 1),
        dias_silencio=silencio,
        ratio=round(ratio, 2),
        severidad=severidad,
        ultima_fecha=ultima,
        n_transacciones=len(txs),
    )
