"""Scheduler in-proceso del worker de envíos (APScheduler) — Ppio VII: sin
broker, sin Airflow (reservado a 012). Corre cada minuto (Spec SC-001: un
cambio de estado de OT genera el email en menos de 1 minuto) — toma los
`envio` `encolado` con `proxima_ejecucion <= now()` y los envía vía
`shared/correo`. Un recordatorio de cita "programado para el futuro" no
necesita un job aparte: ya nace `encolado` con `proxima_ejecucion` en el
futuro (`citas.confirmar` → `notificaciones.encolar(programar_para=...)`) y
este mismo tick lo recoge en cuanto se cumple el plazo.

El endpoint `/_internal/notificaciones/scheduler/tick` permite forzarlo en
pruebas/operación (mismo patrón que `proveedores`/`contabilidad`).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from notificaciones import service
from shared.database import SessionLocal

logger = logging.getLogger("cronos.notificaciones.scheduler")

_scheduler: BackgroundScheduler | None = None


def _tick() -> None:
    db = SessionLocal()
    try:
        r = service.generar_recordatorios_cita(db)
        if r:
            logger.info("Recordatorios de cita: %d encolados", r)
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Fallo generando recordatorios de cita")
    try:
        n = service.procesar_cola(db)
        if n:
            logger.info("Cola de notificaciones: %d envío(s) procesados", n)
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Fallo en el worker de notificaciones")
    finally:
        db.close()


def start() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(_tick, "interval", minutes=1, id="notificaciones_cola", next_run_time=None)
    _scheduler.start()
    logger.info("Worker de notificaciones iniciado (cada 1 min)")


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
