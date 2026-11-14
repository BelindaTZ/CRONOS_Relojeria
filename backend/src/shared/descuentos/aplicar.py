"""Aplicación de un descuento o cupón + validación de margen mínimo (feature 006).

Contrato compartido consumido por 008 (orden de trabajo) y 009 (venta). Recibe
**UN descuento O UN cupón** (nunca ambos: §FR-015 → 422). Devuelve el precio
final, el monto descontado, el margen resultante (absoluto) y la decisión frente
al margen mínimo protegido.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from shared.descuentos import margen_minimo
from shared.exceptions import ValidationError

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class BeneficioAplicable:
    tipo: str          # "porcentaje" | "monto"
    valor: Decimal     # porcentaje como fracción (0.30 = 30 %) o monto fijo


@dataclass(frozen=True)
class ResultadoAplicacion:
    precio_final: Decimal
    monto_descontado: Decimal
    margen_resultante: Decimal
    decision: str
    margen_minimo: margen_minimo.MargenMinimo


def _monto_descuento(b: BeneficioAplicable, precio_lista: Decimal) -> Decimal:
    if b.tipo == "porcentaje":
        monto = precio_lista * Decimal(str(b.valor))
    else:
        monto = Decimal(str(b.valor))
    monto = max(Decimal("0"), min(monto, precio_lista))  # nunca negativo ni mayor que el precio
    return monto.quantize(_CENT, rounding=ROUND_HALF_UP)


def aplicar(
    db: Session,
    *,
    item_ref: str,
    costo: Decimal,
    precio_lista: Decimal,
    marca: str | None = None,
    descuento: BeneficioAplicable | None = None,
    cupon: BeneficioAplicable | None = None,
) -> ResultadoAplicacion:
    if descuento is not None and cupon is not None:
        raise ValidationError(
            "Un descuento general y un cupón no se pueden aplicar juntos a la misma operación",
            field="cupon",
        )

    precio_lista = Decimal(str(precio_lista))
    costo = Decimal(str(costo))
    beneficio = descuento or cupon
    monto_descontado = _monto_descuento(beneficio, precio_lista) if beneficio else Decimal("0.00")
    precio_final = (precio_lista - monto_descontado).quantize(_CENT, rounding=ROUND_HALF_UP)
    margen_resultante = (precio_final - costo).quantize(_CENT, rounding=ROUND_HALF_UP)

    decision, mm = margen_minimo.evaluar(
        db, margen_resultante=margen_resultante, costo=costo, marca=marca, item_ref=item_ref
    )
    return ResultadoAplicacion(
        precio_final=precio_final,
        monto_descontado=monto_descontado,
        margen_resultante=margen_resultante,
        decision=decision,
        margen_minimo=mm,
    )
