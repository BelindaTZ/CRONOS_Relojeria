"""Módulo `piezas` (feature 003): repuestos e insumos, stock por sucursal
(invariante ≥ 0), lotes/caducidad FEFO y libro de movimientos append-only.

API pública para otros módulos (Principio X):
- `recibir_de_compra(db, orden, propagacion)` — receptor de recepción de compra
  (lo cablea `main.py` sobre `proveedores.registrar_receptor_inventario`).
- Traslados (004): `stock_en`, `piezas_disponibles_en`, `mover_stock_traslado`.
- `aplicar_movimiento(...)` — helper transaccional de bajo nivel (08/09 futuras).
"""

from piezas.service import (
    aplicar_movimiento,
    buscar_o_crear_por_codigo,
    consumir_en_ot,
    costo_pieza,
    dar_baja_pieza,
    datos_pieza,
    datos_pieza_venta,
    mover_stock_traslado,
    piezas_disponibles_en,
    recibir_de_compra,
    reingresar_pieza,
    revertir_venta_pieza,
    stock_en,
    vender_pieza,
)

__all__ = [
    "aplicar_movimiento",
    "recibir_de_compra",
    "stock_en",
    "datos_pieza",
    "datos_pieza_venta",
    "buscar_o_crear_por_codigo",
    "consumir_en_ot",
    "costo_pieza",
    "piezas_disponibles_en",
    "mover_stock_traslado",
    "vender_pieza",
    "revertir_venta_pieza",
    "dar_baja_pieza",
    "reingresar_pieza",
]
