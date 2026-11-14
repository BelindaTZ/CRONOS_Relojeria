"""Módulo `contabilidad` (feature 010): plan de cuentas NIIF PYMES, libro diario
con partida doble y derivados (mayor, balance, estado de resultados), caja y
bancos por sucursal, cheques, subledger de CxC (de 009/008) y de CxP (de 002 y de
gastos), gastos operativos (pagados/por pagar) + recurrentes, motor de asiento
automático y rentabilidad neta por sucursal.

API pública para otros módulos (Principio X):
- `generar_asiento(db, *, evento, monto, glosa, origen, origen_id, condicion_ctx?, actor?)` —
  009 (venta confirmada/cobro), 008 (OT entregada/cobro) y 011 (merma, cuando exista)
  disparan aquí su asiento automático. Best-effort: si no hay regla configurada o el
  periodo está cerrado, registra un aviso y NO bloquea la operación de origen.
- `generar_asiento_reversa(...)` — para anulaciones (009 al anular una venta).
- `recibir_compra_cxp(db, orden)` — receptor que cablea `main.py` sobre
  `proveedores.registrar_receptor_cxp` (crea la CxP al completarse una recepción).
"""

from contabilidad.asientos_auto import generar as generar_asiento
from contabilidad.asientos_auto import generar_reversa as generar_asiento_reversa
from contabilidad.service import recibir_compra_cxp

__all__ = ["generar_asiento", "generar_asiento_reversa", "recibir_compra_cxp"]
