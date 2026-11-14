"""Motor de asiento automático (feature 010, research D7).

Cada hecho de negocio dispara un `evento`; `generar()` busca la `regla_asiento_automatico`
activa que mejor coincide (por `condicion`, con fallback a la regla sin condición) y
produce un asiento de dos líneas (`debe`/`haber`) por `monto`.

**Si no hay regla configurada, no bloquea la operación de origen** (ACC006): se
registra un aviso y se devuelve `None`. Las features que llaman a `generar` desde
otro módulo (ventas, servicio técnico, proveedores) lo hacen dentro de un
`try/except` — el asiento es contabilidad de respaldo, no debe impedir la venta,
la entrega o la recepción.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from contabilidad import repository
from contabilidad.models import Asiento
from contabilidad.service import crear_asiento

logger = logging.getLogger("cronos.contabilidad.asientos_auto")


def _mejor_regla(db: Session, evento: str, condicion_ctx: dict | None):
    reglas = repository.listar_reglas(db, evento=evento)
    if not reglas:
        return None
    if condicion_ctx:
        for r in reglas:
            if r.condicion and all(r.condicion.get(k) == v for k, v in condicion_ctx.items()):
                return r
    # fallback: la regla sin condición (aplica a cualquier caso)
    return next((r for r in reglas if not r.condicion), reglas[0])


def generar(
    db: Session, *, evento: str, monto: Decimal | float | str, glosa: str,
    origen: str = "manual", origen_id: int | None = None,
    condicion_ctx: dict | None = None, fecha: date | None = None, actor: int | None = None,
) -> Asiento | None:
    monto = Decimal(str(monto))
    if monto <= 0:
        return None
    regla = _mejor_regla(db, evento, condicion_ctx)
    if regla is None:
        logger.warning("sin regla_asiento_automatico activa para el evento '%s' (%s) — no se generó asiento",
                       evento, condicion_ctx or {})
        return None
    return crear_asiento(
        db, fecha=fecha or date.today(), glosa=glosa,
        lineas=[
            {"cuenta_id": regla.cuenta_debe_id, "debe": monto, "haber": 0},
            {"cuenta_id": regla.cuenta_haber_id, "debe": 0, "haber": monto},
        ],
        origen=origen, origen_id=origen_id, actor=actor,
    )


def generar_reversa(
    db: Session, *, evento: str, monto: Decimal | float | str, glosa: str,
    origen: str = "ajuste", origen_id: int | None = None,
    condicion_ctx: dict | None = None, fecha: date | None = None, actor: int | None = None,
) -> Asiento | None:
    """Genera el asiento de reversa de `evento` (debe/haber intercambiados) — se usa
    ante una anulación (ACC008), no una edición del asiento original."""
    monto = Decimal(str(monto))
    if monto <= 0:
        return None
    regla = _mejor_regla(db, evento, condicion_ctx)
    if regla is None:
        logger.warning("sin regla para reversar el evento '%s' — no se generó asiento de reversa", evento)
        return None
    return crear_asiento(
        db, fecha=fecha or date.today(), glosa=glosa,
        lineas=[
            {"cuenta_id": regla.cuenta_haber_id, "debe": monto, "haber": 0},
            {"cuenta_id": regla.cuenta_debe_id, "debe": 0, "haber": monto},
        ],
        origen=origen, origen_id=origen_id, actor=actor,
    )
