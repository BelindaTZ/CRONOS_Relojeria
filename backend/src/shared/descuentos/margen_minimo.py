"""Margen mínimo protegido (feature 006, §4.8.2 / §9.1).

Regla de negocio: ningún descuento ni cupón puede dejar el margen de una venta u
orden de trabajo por debajo del mínimo configurable. El cálculo es **siempre de
backend** (Const. Ppio V). Lo consumen 008 (OT) y 009 (venta) vía
`shared.descuentos.aplicar`.

- **Base del margen (BR009)**: `margen = precio_final − costo`, en valor absoluto.
  Para servicios, `costo` que entra ya incluye mano de obra + piezas + insumos (008).
- **Precedencia de ámbitos (BR010)**: producto → marca → global.
- **Decisión (BR011)**: `permitir` si `margen ≥ mínimo`; si cae por debajo,
  `bloquear` o `requiere_autorizacion` según el parámetro `margen_minimo_politica`.
- **BR013**: `margen == mínimo` ⇒ permitir (`>=`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from shared.parametros import get_parametro
from shared.parametros import repository as _param_repo


@dataclass(frozen=True)
class MargenMinimo:
    tipo: str          # "porcentaje_costo" | "monto"
    valor: Decimal
    ambito: str        # "producto" | "marca" | "global"
    ref: str | None
    politica: str      # "bloquear" | "autorizar"

    def minimo_absoluto(self, costo: Decimal) -> Decimal:
        if self.tipo == "porcentaje_costo":
            return (Decimal(str(costo)) * Decimal(str(self.valor))).quantize(Decimal("0.01"))
        return Decimal(str(self.valor))


def vigente(db: Session, *, marca: str | None = None, item_ref: str | None = None) -> MargenMinimo:
    """Resuelve el margen mínimo aplicable con precedencia producto → marca → global."""
    resuelto: tuple[dict, str, str | None] | None = None
    for ambito, ref in (("producto", item_ref), ("marca", marca)):
        if not ref:
            continue
        row = _param_repo.vigente(db, "margen_minimo", ambito_tipo=ambito, ambito_ref=ref)
        if row is not None:
            resuelto = (row.valor, ambito, ref)
            break
    if resuelto is None:
        row = _param_repo.vigente(db, "margen_minimo", ambito_tipo="global", ambito_ref=None)
        base = row.valor if row is not None else {"tipo": "porcentaje_costo", "valor": 0}
        resuelto = (base, "global", None)

    cfg, ambito, ref = resuelto
    politica = str(get_parametro(db, "margen_minimo_politica", default="autorizar") or "autorizar")
    return MargenMinimo(
        tipo=str(cfg.get("tipo", "porcentaje_costo")),
        valor=Decimal(str(cfg.get("valor", 0))),
        ambito=ambito, ref=ref, politica=politica,
    )


def evaluar(
    db: Session, *, margen_resultante: Decimal, costo: Decimal,
    marca: str | None = None, item_ref: str | None = None,
) -> tuple[str, MargenMinimo]:
    """Devuelve (`decision`, `MargenMinimo`). `decision` ∈ {permitir, bloquear, requiere_autorizacion}."""
    mm = vigente(db, marca=marca, item_ref=item_ref)
    minimo = mm.minimo_absoluto(Decimal(str(costo)))
    if Decimal(str(margen_resultante)) >= minimo:
        return "permitir", mm
    return ("bloquear" if mm.politica == "bloquear" else "requiere_autorizacion"), mm
