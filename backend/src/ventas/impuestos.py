"""Desglose de IVA de la venta (feature 009 — ampliación 2026-09-10).

Los precios del sistema son **PVP: IVA incluido**. La factura hace el back-out y
muestra el desglose reglamentario ecuatoriano:

    base_imponible = precio_con_iva / (1 + iva_pct)
    iva_monto      = precio_con_iva − base_imponible

Relojes y piezas tributan a la tarifa general (`iva_porcentaje`, parámetro; 0,15).
`tarifa_iva` se guarda por línea por si a futuro hay ítems a 0 %.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


def _q(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass
class DesgloseLinea:
    base_imponible: Decimal
    iva_monto: Decimal
    descuento_monto: Decimal        # sobre el PVP (IVA incluido)
    tarifa_iva: Decimal             # p. ej. 15 (porcentaje)


@dataclass
class DesgloseVenta:
    subtotal_bruto: Decimal = Decimal("0")        # Σ precio_lista_base (antes de descuento)
    total_descuento: Decimal = Decimal("0")       # Σ descuento_base
    subtotal_sin_impuestos: Decimal = Decimal("0")  # base gravada tras descuento
    subtotal_15: Decimal = Decimal("0")
    subtotal_0: Decimal = Decimal("0")
    iva_monto: Decimal = Decimal("0")
    valor_total: Decimal = Decimal("0")           # = Σ precio_final (PVP)
    iva_porcentaje: Decimal = Decimal("0.15")
    lineas: list[DesgloseLinea] = field(default_factory=list)


def desglosar_linea(*, precio_lista_con_iva, precio_final_con_iva, iva_pct: Decimal, tarifa_iva: Decimal | None = None) -> DesgloseLinea:
    tarifa = iva_pct if tarifa_iva is None else Decimal(str(tarifa_iva)) / 100
    factor = Decimal("1") + tarifa
    base_final = _q(_q(precio_final_con_iva) / factor) if factor else _q(precio_final_con_iva)
    base_lista = _q(_q(precio_lista_con_iva) / factor) if factor else _q(precio_lista_con_iva)
    iva = _q(_q(precio_final_con_iva) - base_final)
    return DesgloseLinea(
        base_imponible=base_final, iva_monto=iva,
        descuento_monto=_q(_q(precio_lista_con_iva) - _q(precio_final_con_iva)),
        tarifa_iva=(tarifa * 100).quantize(_CENT),
    )


def desglosar_venta(lineas, *, iva_pct: Decimal) -> DesgloseVenta:
    """`lineas` = iterables con `.precio_lista`, `.precio_final` y opcional `.tarifa_iva` (porcentaje)."""
    d = DesgloseVenta(iva_porcentaje=Decimal(str(iva_pct)))
    for ln in lineas:
        dl = desglosar_linea(
            precio_lista_con_iva=ln.precio_lista, precio_final_con_iva=ln.precio_final,
            iva_pct=Decimal(str(iva_pct)), tarifa_iva=getattr(ln, "tarifa_iva", None),
        )
        d.lineas.append(dl)
        factor = Decimal("1") + dl.tarifa_iva / 100
        base_lista = _q(_q(ln.precio_lista) / factor) if factor else _q(ln.precio_lista)
        d.subtotal_bruto += base_lista
        d.total_descuento += _q(base_lista - dl.base_imponible)
        d.subtotal_sin_impuestos += dl.base_imponible
        if dl.tarifa_iva > 0:
            d.subtotal_15 += dl.base_imponible
        else:
            d.subtotal_0 += dl.base_imponible
        d.iva_monto += dl.iva_monto
        d.valor_total += _q(ln.precio_final)
    for campo in ("subtotal_bruto", "total_descuento", "subtotal_sin_impuestos", "subtotal_15",
                  "subtotal_0", "iva_monto", "valor_total"):
        setattr(d, campo, _q(getattr(d, campo)))
    return d
