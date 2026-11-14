"""Módulo `inventario` (feature 003): relojes (unidad física), calibres, fotos,
historial inalterable por número de serie y alertas de stock.

API pública para otros módulos (Principio X):
- `calibres_por_ids(db, ids)` — etiquetas de calibre (lo usa `piezas`).
- `recalcular_alertas_pieza(...)` — `piezas` lo llama tras cada movimiento.
- `registrar_evento_externo(...)` — 008/009/011 escriben en el historial de serie.
- `sucursales_visibles(user, sucursal_id)` — scoping por sucursal (004).
- Traslados (004): `reloj_para_traslado`, `relojes_disponibles_en`,
  `marcar_reloj_en_transito`, `recibir_reloj_transferido`, `revertir_reloj_transferencia`.
- Servicio técnico (008): `marcar_reloj_en_servicio`, `revertir_reloj_servicio` — la
  unidad deja de estar vendible en Ventas mientras está en el taller;
  `relojes_elegibles_para_ot(db, *, q?)` — catálogo real para el selector de "unidad"
  al abrir una OT (nunca texto libre).
"""

from inventario.service import (
    calibres_por_ids,
    ids_relojes_por_serie,
    marcar_reloj_baja,
    marcar_reloj_en_servicio,
    marcar_reloj_en_transito,
    recalcular_alertas_pieza,
    marcar_reloj_vendido,
    recibir_reloj_transferido,
    registrar_consumidores,
    registrar_evento_externo,
    reloj_para_merma,
    reloj_para_ot,
    reloj_para_traslado,
    reloj_para_venta,
    relojes_disponibles_en,
    relojes_elegibles_para_ot,
    revertir_reloj_baja,
    revertir_reloj_servicio,
    revertir_reloj_transferencia,
    revertir_reloj_venta,
    serie_adquirida_en_tienda,
    sucursales_visibles,
)

__all__ = [
    "calibres_por_ids",
    "recalcular_alertas_pieza",
    "registrar_consumidores",
    "registrar_evento_externo",
    "sucursales_visibles",
    "ids_relojes_por_serie",
    "reloj_para_ot",
    "reloj_para_traslado",
    "reloj_para_venta",
    "reloj_para_merma",
    "relojes_disponibles_en",
    "relojes_elegibles_para_ot",
    "serie_adquirida_en_tienda",
    "marcar_reloj_en_servicio",
    "marcar_reloj_en_transito",
    "marcar_reloj_vendido",
    "marcar_reloj_baja",
    "recibir_reloj_transferido",
    "revertir_reloj_servicio",
    "revertir_reloj_transferencia",
    "revertir_reloj_venta",
    "revertir_reloj_baja",
]
