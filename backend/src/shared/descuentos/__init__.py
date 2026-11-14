"""Capacidad compartida de descuentos y margen mínimo protegido (feature 006).

API pública para 008 (orden de trabajo) y 009 (venta):
- `aplicar(db, *, item_ref, costo, precio_lista, marca?, descuento?, cupon?)` →
  `ResultadoAplicacion{precio_final, monto_descontado, margen_resultante, decision, margen_minimo}`.
  `decision` ∈ {permitir, bloquear, requiere_autorizacion}. 422 si se pasan
  descuento y cupón a la vez (mutuamente excluyentes).
- `BeneficioAplicable` — DTO de entrada (tipo porcentaje|monto, valor).
- `margen_minimo_vigente` / `evaluar_margen` — consulta directa del mínimo aplicable.
"""

from shared.descuentos.aplicar import BeneficioAplicable, ResultadoAplicacion, aplicar
from shared.descuentos.margen_minimo import MargenMinimo
from shared.descuentos.margen_minimo import evaluar as evaluar_margen
from shared.descuentos.margen_minimo import vigente as margen_minimo_vigente

__all__ = [
    "aplicar",
    "BeneficioAplicable",
    "ResultadoAplicacion",
    "MargenMinimo",
    "evaluar_margen",
    "margen_minimo_vigente",
]
