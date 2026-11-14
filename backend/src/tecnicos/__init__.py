"""Módulo `tecnicos` (feature 005): RRHH técnico, costo interno de mano de obra
por tarifa horaria, esquema de bono por productividad configurable + motor de
acumulación y prorrateo, y vista operativa de productividad.

API pública para otros módulos (Principio X):
- `costo_mo_ot(db, *, tecnico_id, horas?, tipo_reparacion?)` — costo de mano de obra
  de una OT (lo consume 008 para el costo interno del servicio, nunca el cliente).
- `bono_ot_de_orden(db, orden_trabajo_id)` — bono prorrateado de esa OT (008 lo
  suma al costo de MO en los reportes de margen).
- `especialidades_de(db, tecnico_id)` / `tecnico_activo(db, tecnico_id)` — 008 los
  usa para sugerir la asignación de una OT.
- `registrar_proveedor_ot(fn)` — 008 registra aquí la fuente de OT cerradas que
  alimenta el motor de bono e indicadores de productividad.
- `registrar_consumidores()` — recálculo en cascada de bonos abiertos (001).
"""

from tecnicos.service import (
    OrdenTrabajoInfo,
    bono_ot_de_orden,
    costo_mo_ot,
    datos_para_correo,
    especialidades_de,
    registrar_consumidores,
    registrar_proveedor_ot,
    sugerir_tecnico,
    tecnico_activo,
    tecnico_de_usuario,
)

__all__ = [
    "OrdenTrabajoInfo",
    "bono_ot_de_orden",
    "costo_mo_ot",
    "datos_para_correo",
    "especialidades_de",
    "registrar_consumidores",
    "registrar_proveedor_ot",
    "sugerir_tecnico",
    "tecnico_activo",
    "tecnico_de_usuario",
]
