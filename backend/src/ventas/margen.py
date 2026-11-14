"""Cálculo del margen de la venta (feature 009, spec §FR-004, research D2).

Los precios son PVP (IVA incluido). El **margen comercial** del negocio se calcula
sobre el precio **neto de IVA** (el IVA se remite, no es ingreso del retailer):

    base_linea   = precio_final_con_iva / (1 + iva_pct)
    margen_linea = base_linea − costo
    margen_venta = Σ margen_linea

`costo` = `reloj.costo_adquisicion` (por unidad) o `pieza.costo_adquisicion × cantidad`.
**Restringido a rol administrativo; nunca en la factura** (Const. Ppio V / §FR-009).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


def _q(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


def base_neta(precio_con_iva, iva_pct) -> Decimal:
    factor = Decimal("1") + Decimal(str(iva_pct or 0))
    return _q(_q(precio_con_iva) / factor) if factor else _q(precio_con_iva)


def margen_linea(*, precio_final, costo, iva_pct=Decimal("0")) -> Decimal:
    return _q(base_neta(precio_final, iva_pct) - _q(costo))


def margen_venta(lineas, *, iva_pct=Decimal("0")) -> Decimal:
    """`lineas` = iterables con `.precio_final` y `.costo`."""
    return _q(sum(
        (margen_linea(precio_final=ln.precio_final, costo=ln.costo, iva_pct=iva_pct) for ln in lineas),
        Decimal("0"),
    ))
