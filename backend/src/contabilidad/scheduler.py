"""Scheduler in-proceso para gastos recurrentes (APScheduler, research D12).

Corre cada hora: genera `gasto` en `borrador` de los recurrentes vencidos y avanza
`proxima_generacion`. Mismo patrón que `proveedores/scheduler.py` (002). NO usa
Airflow (reservado a 012, Const. Ppio VII). `POST /_internal/scheduler/tick`
permite forzarlo en pruebas/operación.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from contabilidad import recurrentes
from shared.database import SessionLocal

logger = logging.getLogger("cronos.contabilidad.scheduler")

_scheduler: BackgroundScheduler | None = None


def _tick() -> None:
    db = SessionLocal()
    try:
        n = recurrentes.generar_vencidos(db)
        db.commit()
        if n:
            logger.info("Gastos recurrentes: %d gastos borrador generados", n)
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Fallo en la corrida de gastos recurrentes")
    finally:
        db.close()


def start() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(_tick, "interval", hours=1, id="gastos_recurrentes", next_run_time=None)
    _scheduler.start()
    logger.info("Scheduler de gastos recurrentes iniciado (cada 1 h)")


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
