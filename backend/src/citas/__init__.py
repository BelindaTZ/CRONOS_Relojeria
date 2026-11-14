"""Módulo `citas` (feature 007): registro manual de citas, ciclo de estados
(pendiente → confirmada → cancelada|atendida), agenda del día y de la semana por
sucursal, y vínculo de la cita atendida a la venta (009) o la orden de trabajo (008).

API pública para otros módulos (Principio X):
- `vincular_transaccion(db, cita_id, *, venta_id?, orden_trabajo_id?, actor?)` —
  008/009 la llaman al confirmar la transacción que nació de una cita.
"""

from citas.service import vincular_transaccion

__all__ = ["vincular_transaccion"]
