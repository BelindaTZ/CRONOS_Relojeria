"""Parámetros de configuración con vigencia + recálculo en cascada (Const.).

API pública:
  get_parametro(db, clave, ambito_tipo, ambito_ref, en_fecha) -> valor vigente
  set_parametro(db, clave, ...) -> inserta valor nuevo y dispara recalcular()
  registrar_consumidor(clave, fn) -> las features 005/006/008/009/010 se registran
"""

from shared.parametros.service import (
    ResumenRecalculo,
    get_parametro,
    registrar_consumidor,
    set_parametro,
)

__all__ = [
    "get_parametro",
    "set_parametro",
    "registrar_consumidor",
    "ResumenRecalculo",
]
