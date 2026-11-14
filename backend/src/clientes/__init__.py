"""Módulo `clientes` (feature 006): CRM básico, programa de fidelización con
niveles configurables y motor de recálculo, descuentos generales y cupones, y los
endpoints de configuración / autorización del margen mínimo protegido (la lógica
del margen mínimo vive en `shared/descuentos`).

API pública para otros módulos (Principio X):
- `recalcular_nivel(db, *, cliente_id, hecho, documento_id?)` — 008/009 lo llaman al
  confirmar una compra/servicio.
- `consumir_cupon(db, *, codigo, documento_tipo, documento_id, actor?)` — 008/009.
- `cliente_mini(db, cliente_id)` / `id_consumidor_final(db)` — datos mínimos del
  cliente para citas (007), OT (008) y ventas (009).
- `registrar_proveedor_transacciones(fn)` — 008 (servicios) y 009 (ventas)
  registran aquí su fuente de transacciones para el motor de nivel y los reportes.
- `TransaccionCliente` — DTO de esa fuente.
- `registrar_consumidores()` — recálculo en cascada (001).
"""

from clientes.service import (
    TransaccionCliente,
    autorizacion_por_id,
    cliente_mini,
    consumir_cupon,
    cupon_datos,
    descuento_por_id,
    id_consumidor_final,
    ids_por_texto,
    recalcular_nivel,
    registrar_consumidores,
    registrar_proveedor_transacciones,
)

__all__ = [
    "TransaccionCliente",
    "autorizacion_por_id",
    "cliente_mini",
    "consumir_cupon",
    "cupon_datos",
    "descuento_por_id",
    "id_consumidor_final",
    "ids_por_texto",
    "recalcular_nivel",
    "registrar_consumidores",
    "registrar_proveedor_transacciones",
]
