"""Contrato interno de costeo de mano de obra (feature 005 → consumido por 008).

`costo_mo_ot` es el único punto por el que 008 obtiene el costo de mano de obra de
una orden de trabajo. Método (spec §FR-004, research D1):

    tarifa_hora = sueldo_mensual_vigente(tecnico) / parametro("horas_productivas_estandar_mes")
    costo_mo    = tarifa_hora × horas_registradas
                  (o × tiempo_estimado(tipo_reparacion) si no hay horas)

Nunca se expone al cliente (Const. Ppio V / spec §FR-009): 008 lo usa solo para el
cálculo interno de margen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from shared.exceptions import NotFoundError, ValidationError
from shared.parametros import get_parametro
from tecnicos import repository

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class CostoManoObraOT:
    costo_mo: Decimal
    tarifa_hora: Decimal
    horas: float
    base: str  # "horas_registradas" | "tiempo_estimado"


def _num(v, default: Decimal) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return default


def horas_estandar_mes(db: Session) -> Decimal:
    return _num(get_parametro(db, "horas_productivas_estandar_mes", default=160), Decimal("160")) or Decimal("160")


def tarifa_hora(db: Session, tecnico_id: int, *, en_fecha: date | None = None) -> Decimal:
    esquema = repository.costo_vigente(db, tecnico_id, en_fecha)
    if esquema is None:
        raise ValidationError(
            "El técnico no tiene un esquema de costo de mano de obra vigente", field="tecnico_id"
        )
    horas = horas_estandar_mes(db)
    return (Decimal(esquema.sueldo_mensual) / horas).quantize(_CENT, rounding=ROUND_HALF_UP)


def tiempo_estimado_horas(db: Session, tipo_reparacion: str | None) -> Decimal:
    """Horas estimadas del tipo de reparación. Parámetro por tipo (`tiempo_estimado_horas__<tipo>`)
    con fallback a `tiempo_estimado_horas_default` (§9.2; el catálogo lo llena 008)."""
    por_defecto = _num(get_parametro(db, "tiempo_estimado_horas_default", default=2), Decimal("2"))
    if not tipo_reparacion:
        return por_defecto
    clave = f"tiempo_estimado_horas__{tipo_reparacion.strip().lower()}"
    return _num(get_parametro(db, clave, default=por_defecto), por_defecto)


def costo_mo_ot(
    db: Session,
    *,
    tecnico_id: int,
    horas: float | None = None,
    tipo_reparacion: str | None = None,
    en_fecha: date | None = None,
) -> CostoManoObraOT:
    if repository.obtener(db, tecnico_id) is None:
        raise NotFoundError("Técnico no encontrado")

    tarifa = tarifa_hora(db, tecnico_id, en_fecha=en_fecha)
    if horas is not None:
        base_horas = Decimal(str(horas))
        base = "horas_registradas"
    else:
        base_horas = tiempo_estimado_horas(db, tipo_reparacion)
        base = "tiempo_estimado"
    if base_horas < 0:
        raise ValidationError("Las horas no pueden ser negativas", field="horas")

    costo = (tarifa * base_horas).quantize(_CENT, rounding=ROUND_HALF_UP)
    return CostoManoObraOT(costo_mo=costo, tarifa_hora=tarifa, horas=float(base_horas), base=base)
