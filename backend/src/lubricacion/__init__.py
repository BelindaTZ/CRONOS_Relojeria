"""Módulo `lubricacion` (feature 008): catálogo Moebius, fichas de lubricación por
calibre (puntos + producto recomendado) y registro por punto en la OT
(recomendado vs. usado) con reporte operativo de desviaciones.

API pública para `servicio_tecnico` (Principio X):
- `ficha_para_calibre(db, calibre_id)` — puntos con recomendado, al abrir la OT.
- `producto_por_codigo(db, codigo)` — resuelve el código Moebius.
- `registrar_en_ot(db, *, orden_trabajo_id, sucursal_id, producto_usado_codigo, ...)` —
  registro + consumo de insumo; devuelve `(registro, costo_insumo)`.
- `registros_de_ot(db, orden_trabajo_id)` / `costo_insumos_ot(db, orden_trabajo_id)`.
"""

from lubricacion.service import (
    costo_insumos_ot,
    ficha_para_calibre,
    producto_por_codigo,
    registrar_en_ot,
    registros_de_ot,
)

__all__ = [
    "costo_insumos_ot",
    "ficha_para_calibre",
    "producto_por_codigo",
    "registrar_en_ot",
    "registros_de_ot",
]
