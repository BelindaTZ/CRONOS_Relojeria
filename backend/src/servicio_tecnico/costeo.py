"""Costeo y margen del servicio (feature 008, spec §FR-010..FR-013, research D3).

    costo_interno   = costo_mano_obra + costo_piezas + costo_insumos
    costo_mano_obra = tecnicos.costo_mo_ot(horas registradas | tiempo estimado)   (005)
    costo_piezas    = Σ pieza_usada_ot.costo
    costo_insumos   = Σ consumo de lubricación valorado a costo (003, vía `lubricacion`)
    precio_sugerido = costo_interno × (1 + margen_objetivo_servicio)
    margen_real     = precio_cobrado − costo_interno

`margen_objetivo_servicio` es un parámetro con ámbito global / tipo_servicio /
sucursal (§9.1, §9.4). El costo de mano de obra y el margen NUNCA se exponen al
cliente (Const. Ppio V / §FR-026).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from servicio_tecnico import repository
from shared.parametros import get_parametro

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class CosteoServicio:
    costo_mano_obra: Decimal
    costo_piezas: Decimal
    costo_insumos: Decimal
    costo_interno: Decimal
    bono_prorrateado: Decimal
    margen_objetivo: Decimal
    precio_sugerido: Decimal
    margen_real: Decimal | None
    base_mano_obra: str


def _num(v, default: Decimal) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return default


def margen_objetivo(db: Session, *, tipo_reparacion: str | None, sucursal_id: int | None) -> Decimal:
    """Precedencia: sucursal → tipo de servicio → global (§9.4)."""
    if sucursal_id is not None:
        v = get_parametro(db, "margen_objetivo_servicio", ambito_tipo="sucursal",
                          ambito_ref=str(sucursal_id), default=None, fallback_global=False)
        if v is not None:
            return _num(v, Decimal("0.5"))
    if tipo_reparacion:
        v = get_parametro(db, "margen_objetivo_servicio", ambito_tipo="tipo_servicio",
                          ambito_ref=tipo_reparacion.strip().lower(), default=None, fallback_global=False)
        if v is not None:
            return _num(v, Decimal("0.5"))
    return _num(get_parametro(db, "margen_objetivo_servicio", default=0.5), Decimal("0.5"))


def costo_mano_obra(db: Session, ot) -> tuple[Decimal, Decimal, str]:
    """Devuelve (costo_mo, bono_prorrateado, base)."""
    if ot.tecnico_id is None:
        return Decimal("0"), Decimal("0"), "sin_tecnico"
    from tecnicos import bono_ot_de_orden, costo_mo_ot

    horas = float(ot.horas_trabajadas) if ot.horas_trabajadas is not None else None
    try:
        r = costo_mo_ot(db, tecnico_id=ot.tecnico_id, horas=horas, tipo_reparacion=ot.tipo_reparacion)
        costo = Decimal(str(r.costo_mo))
        base = r.base
    except Exception:  # noqa: BLE001  (técnico sin esquema de costo vigente)
        costo, base = Decimal("0"), "sin_esquema_costo"
    bono = Decimal(str(bono_ot_de_orden(db, ot.id)))
    return costo, bono, base


def costo_piezas(db: Session, oid: int) -> Decimal:
    total = sum((Decimal(str(pu.costo or 0)) for pu in repository.piezas_de(db, oid)), Decimal("0"))
    return total.quantize(_CENT, rounding=ROUND_HALF_UP)


def costo_insumos(db: Session, oid: int) -> Decimal:
    from lubricacion import costo_insumos_ot

    return Decimal(str(costo_insumos_ot(db, oid)))


def costear(db: Session, ot) -> CosteoServicio:
    mo, bono, base = costo_mano_obra(db, ot)
    piezas = costo_piezas(db, ot.id)
    insumos = costo_insumos(db, ot.id)
    costo_interno = (mo + bono + piezas + insumos).quantize(_CENT, rounding=ROUND_HALF_UP)
    obj = margen_objetivo(db, tipo_reparacion=ot.tipo_reparacion, sucursal_id=ot.sucursal_id)
    precio_sugerido = (costo_interno * (Decimal("1") + obj)).quantize(_CENT, rounding=ROUND_HALF_UP)
    margen_real = None
    if ot.precio_cobrado is not None:
        margen_real = (Decimal(str(ot.precio_cobrado)) - costo_interno).quantize(_CENT, rounding=ROUND_HALF_UP)
    return CosteoServicio(
        costo_mano_obra=mo, costo_piezas=piezas, costo_insumos=insumos,
        costo_interno=costo_interno, bono_prorrateado=bono, margen_objetivo=obj,
        precio_sugerido=precio_sugerido, margen_real=margen_real, base_mano_obra=base,
    )
