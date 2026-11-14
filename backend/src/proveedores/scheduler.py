"""Scheduler in-proceso para compras programadas (APScheduler).

Corre cada hora: genera órdenes `borrador` de las compras programadas vencidas y
avanza `proxima_generacion`. NO usa Airflow (reservado a 012, Const. Ppio VII).
El endpoint `/_internal/scheduler/tick` permite forzarlo en pruebas/operación.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from proveedores import service
from shared.database import SessionLocal

logger = logging.getLogger("cronos.proveedores.scheduler")

_scheduler: BackgroundScheduler | None = None


def _tick() -> None:
    db = SessionLocal()
    try:
        n = service.generar_programadas_vencidas(db, actor=None)
        db.commit()
        if n:
            logger.info("Compras programadas: %d órdenes borrador generadas", n)
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Fallo en la corrida de compras programadas")
    finally:
        db.close()


def start() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(_tick, "interval", hours=1, id="compras_programadas", next_run_time=None)
    _scheduler.start()
    logger.info("Scheduler de compras programadas iniciado (cada 1 h)")


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
