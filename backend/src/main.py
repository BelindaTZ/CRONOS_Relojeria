"""Punto de entrada de la API CRONOS (feature 000).

Crea la app FastAPI, registra los handlers de error, configura CORS y monta el
registro de routers de módulos. En esta feature solo el módulo plantilla `health`
está registrado; las features 001+ añaden una línea a `MODULE_ROUTERS`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from shared.config import get_settings
from shared.database import engine
from shared.exceptions import register_exception_handlers
from health.router import router as health_router
from auth.router import router as auth_router
from usuarios.router import perfil_router, router as usuarios_router
from rbac.router import router as rbac_router
from sucursales.router import router as sucursales_router
from configuracion.router import router as configuracion_router
from proveedores.router import router as proveedores_router, internal_router as proveedores_internal
from inventario.router import router as inventario_router
from piezas.router import router as piezas_router
from traslados.router import router as traslados_router
from tecnicos.router import router as tecnicos_router, internal_router as tecnicos_internal
from clientes.router import router as clientes_router, internal_router as clientes_internal
from citas.router import router as citas_router, internal_router as citas_internal
from lubricacion.router import router as lubricacion_router
from servicio_tecnico.router import router as servicio_tecnico_router
from ventas.router import router as ventas_router
from contabilidad.router import router as contabilidad_router, internal_router as contabilidad_internal
from mermas.router import router as mermas_router
from reportes_estado.router import router as reportes_estado_router
from dashboards.router import router as dashboards_router
from notificaciones.router import router as notificaciones_router, internal_router as notificaciones_internal

logger = logging.getLogger("cronos.startup")

# --- Registro de routers de módulos -------------------------------------------
# Cada feature de negocio añade aquí SU router público y nada más.
MODULE_ROUTERS: list[APIRouter] = [
    health_router,
    auth_router,
    perfil_router,
    usuarios_router,
    rbac_router,
    sucursales_router,
    configuracion_router,
    proveedores_router,
    proveedores_internal,
    inventario_router,
    piezas_router,
    traslados_router,
    tecnicos_router,
    tecnicos_internal,
    clientes_router,
    clientes_internal,
    citas_router,
    citas_internal,
    lubricacion_router,
    servicio_tecnico_router,
    ventas_router,
    contabilidad_router,
    contabilidad_internal,
    mermas_router,
    reportes_estado_router,
    dashboards_router,
    notificaciones_router,
    notificaciones_internal,
]


def _wait_for_database(timeout_seconds: int) -> None:
    """Espera/reintenta la conexión a PostgreSQL con backoff antes de aceptar tráfico.

    Constitución / spec FR-006: el backend no acepta tráfico hasta que la base
    responde, o hasta agotar el timeout (entonces falla con un mensaje claro).
    """
    deadline = time.monotonic() + timeout_seconds
    delay = 0.5
    attempt = 0
    while True:
        attempt += 1
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL disponible tras %d intento(s)", attempt)
            return
        except Exception as exc:  # noqa: BLE001
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"PostgreSQL no respondió en {timeout_seconds}s "
                    f"({attempt} intentos). Último error: {exc}"
                ) from exc
            logger.warning("PostgreSQL no listo (intento %d): %s. Reintentando en %.1fs", attempt, exc, delay)
            time.sleep(delay)
            delay = min(delay * 2, 5.0)


@asynccontextmanager
async def lifespan(_: FastAPI) -> Iterator[None]:
    settings = get_settings()
    _wait_for_database(settings.db_connect_timeout_seconds)

    from proveedores import scheduler as proveedores_scheduler
    from proveedores import service as proveedores_service
    from inventario import service as inventario_service
    from piezas import service as piezas_service
    from tecnicos import service as tecnicos_service
    from clientes import service as clientes_service
    from servicio_tecnico import service as servicio_tecnico_service
    from ventas import service as ventas_service
    from contabilidad import service as contabilidad_service
    from contabilidad import scheduler as contabilidad_scheduler
    from notificaciones import scheduler as notificaciones_scheduler

    proveedores_service.registrar_consumidores()
    inventario_service.registrar_consumidores()
    tecnicos_service.registrar_consumidores()
    clientes_service.registrar_consumidores()
    servicio_tecnico_service.registrar_consumidores()
    servicio_tecnico_service.registrar_proveedores()
    ventas_service.registrar_consumidores()
    ventas_service.registrar_proveedores()
    # Recepción de compra (002) → alta de stock de piezas / pendientes de fichar (003).
    proveedores_service.registrar_receptor_inventario(piezas_service.recibir_de_compra)
    # Recepción completa de una OC → CxP + asiento automático (010).
    proveedores_service.registrar_receptor_cxp(contabilidad_service.recibir_compra_cxp)
    proveedores_scheduler.start()
    contabilidad_scheduler.start()
    notificaciones_scheduler.start()
    try:
        yield
    finally:
        proveedores_scheduler.shutdown()
        contabilidad_scheduler.shutdown()
        notificaciones_scheduler.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CRONOS API",
        version=settings.app_version,
        description="Backend REST/JSON de CRONOS. Feature 000 — bootstrap de infraestructura.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _capturar_ip_origen(request, call_next):
        from shared.request_context import set_ip_origen

        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
        set_ip_origen(ip)
        try:
            return await call_next(request)
        finally:
            set_ip_origen(None)

    register_exception_handlers(app)

    for module_router in MODULE_ROUTERS:
        app.include_router(module_router)

    return app


app = create_app()
