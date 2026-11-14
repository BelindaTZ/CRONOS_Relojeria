"""Módulo `traslados` (feature 004): transferencias de relojes y piezas entre
sucursales, con máquina de estados, actualización automática del inventario en
ambas sucursales, discrepancias derivables a merma y scoping por sucursal.

API pública para otros módulos (Principio X):
- `discrepancia_para_merma(db, discrepancia_id)` — payload prellenado de
  `POST /mermas` (causa `dano_transito`) para una discrepancia de recepción (011).
- `vincular_merma(db, discrepancia_id, *, merma_id)` — 011 la llama al crear la
  merma derivada; marca la discrepancia resuelta.
"""

from traslados.service import discrepancia_para_merma, vincular_merma

__all__ = ["discrepancia_para_merma", "vincular_merma"]
