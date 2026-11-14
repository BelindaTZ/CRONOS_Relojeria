"""Módulo `ventas` (feature 009): orden de venta de relojes y piezas sueltas
(Principio II), baja de stock + evento de serie, descuentos/cupones con margen
mínimo protegido (006), pagos multimedios (`shared/pagos`), garantías fábrica/tienda,
comprobante + certificado de autenticidad (`shared/pdf`) a `comprobantes-venta`,
cuenta por cobrar del saldo, y anulación con reversas.

Registro en el arranque (`main.py`):
- `registrar_consumidores()` — re-evalúa el margen mínimo de ventas en borrador.
- `registrar_proveedores()` — alimenta a 006 (motor de nivel y reportes) con las ventas.

API pública para 010 (Principio X):
- `cuentas_por_cobrar_abiertas(db, *, cliente_id?)` — CxC pendientes (ventas/OT a crédito).
- `listar_cuentas_por_cobrar(db, *, cliente_id?, estado?)` — todas, para el subledger/aging.
- `marcar_cxc_saldada(db, cxc_id, *, monto?)` — 010 la llama al registrar el cobro.

API pública para 008 (Principio X):
- `crear_cxc_externa(db, *, origen_tipo, origen_id, cliente_id, monto)` — CxC que no nace
  de una venta (entrega de una OT a crédito autorizada por Gerencia General).
- `propietario_de_reloj(db, reloj_id)` — cliente que compró la unidad (venta
  confirmada vigente), para autocompletar el cliente al abrir una OT.
"""

from ventas.service import registrar_consumidores, registrar_proveedores
from ventas.public import (
    crear_cxc_externa,
    cuentas_por_cobrar_abiertas,
    listar_cuentas_por_cobrar,
    marcar_cxc_saldada,
    propietario_de_reloj,
    resumen_periodo,
)

__all__ = [
    "registrar_consumidores",
    "registrar_proveedores",
    "cuentas_por_cobrar_abiertas",
    "listar_cuentas_por_cobrar",
    "marcar_cxc_saldada",
    "crear_cxc_externa",
    "propietario_de_reloj",
    "resumen_periodo",
]
