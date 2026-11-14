"""Router del módulo `dashboards` (feature 013). Solo HTTP — la lógica vive en
`service.py` (Ppio X). El backend operativo no depende de ClickHouse para
arrancar; estos endpoints degradan limpio si no responde (Spec §FR-008)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from dashboards import service
from dashboards.schemas import IndiceReportesOut, PanelOut, ReporteOut
from shared.guard import CurrentUser, get_current_user_full_scope, permisos_efectivos, require_gerencia_o_delegado, require_perm
from shared.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["dashboards"])

# Reportes complejos: audiencia gerencia/administración (Spec §FR-011) — el
# mismo permiso "reportes:consultar" que ya tienen Gerente de Sucursal, Técnico
# Jefe y Contador (0024).
_leer = require_perm("reportes", "consultar")
# Panel principal: explícitamente "solo Gerencia General" (Spec FR-001, contrato
# `dashboards.openapi.yaml`) — más estrecho que "reportes:consultar".
_leer_panel = require_gerencia_o_delegado
# El índice es de consulta libre para TODO el personal autenticado — la propia
# lista se filtra por el permiso real de cada quien (service.indice), no el
# acceso al endpoint (Spec §FR-010: "reportes simples... según su rol").
_leer_indice = get_current_user_full_scope


@router.get("/panel", response_model=PanelOut)
def get_panel(
    periodo: str | None = None,
    sucursal_id: int | None = None,
    user: CurrentUser = Depends(_leer_panel),
) -> dict:
    return service.panel(user=user, periodo=periodo, sucursal_id=sucursal_id)


@router.get("/reportes/indice", response_model=IndiceReportesOut)
def get_indice(user: CurrentUser = Depends(_leer_indice), db: Session = Depends(get_db)) -> dict:
    permisos = permisos_efectivos(db, user)
    return service.indice(user=user, permisos=permisos)


@router.get("/reportes/analitico/{slug}", response_model=ReporteOut)
def get_reporte(
    slug: str,
    periodo: str | None = None,
    sucursal_id: int | None = None,
    marca: str | None = None,
    tecnico_id: int | None = None,
    user: CurrentUser = Depends(_leer),
) -> dict:
    return service.reporte(
        slug, user=user, periodo=periodo, sucursal_id=sucursal_id, marca=marca, tecnico_id=tecnico_id,
    )
