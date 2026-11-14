"""Capacidad compartida de pagos multimedios (feature 008, reutilizada por 009).

API pública:
- `registrar_pago(db, *, documento_tipo, documento_id, medio_pago_id, monto, referencia?, actor?)`
- `saldo(db, *, documento_tipo, documento_id, total)` — `total − Σ pagos`.
- `pagado(db, *, documento_tipo, documento_id)` — Σ pagos registrados.
- `pagos_de(db, *, documento_tipo, documento_id)` — detalle para el comprobante.

Un pago es append-only (trigger en DB). `documento_tipo` ∈ {orden_trabajo, venta}.
"""

from shared.pagos.service import (
    PagoRegistrado,
    pagado,
    pagos_de,
    registrar_pago,
    saldo,
)

__all__ = ["PagoRegistrado", "pagado", "pagos_de", "registrar_pago", "saldo"]
