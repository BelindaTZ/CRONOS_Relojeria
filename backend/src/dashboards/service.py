"""Fachada de lectura del módulo `dashboards` (feature 013). El backend
operativo NO agrega datos — toda la lógica analítica vive en el warehouse
(012); este módulo solo consulta, aplica scope por sucursal y da forma a la
respuesta (Ppio III, Ppio VII, Spec §FR-016).
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from shared.exceptions import NotFoundError, PermissionDeniedError
from shared.guard import CurrentUser

from dashboards.warehouse import CATALOGO, ReporteDef, get_client

logger = logging.getLogger("cronos.dashboards")

_MOTIVO_NO_DISPONIBLE = "El warehouse analítico (ClickHouse) no está disponible en este momento."


# ------------------------------------------------------------------- scope
def _sucursales_permitidas(user: CurrentUser, solicitado: int | None) -> list[int] | None:
    """`None` = sin filtro (consolidado, solo Gerencia General). Un Gerente de
    Sucursal nunca ve datos fuera de las suyas (Spec §FR-012, SC-006)."""
    if user.es_gerencia:
        return [solicitado] if solicitado is not None else None
    propias = list(user.sucursal_ids or [])
    if solicitado is not None:
        if solicitado not in propias:
            raise PermissionDeniedError("Sin acceso a esa sucursal")
        return [solicitado]
    return propias or [-1]  # -1: sin sucursal asignada -> ningún dato


def _periodo_a_fecha(periodo: str | None) -> date | None:
    """"2026-09" -> date(2026,9,1). `None`/formato inválido -> `None` (sin filtro)."""
    if not periodo:
        return None
    try:
        anio, mes = periodo.split("-")
        return date(int(anio), int(mes), 1)
    except (ValueError, AttributeError):
        return None


# -------------------------------------------------------------- consulta CH
def _frescura(dominio_esperado: str | None = None) -> dict | None:
    try:
        cliente = get_client()
        filas = cliente.query(
            "SELECT dominio, ultima_carga_ts FROM ctl.pipeline_frescura FINAL ORDER BY ultima_carga_ts DESC LIMIT 1"
        ).result_rows
    except Exception:  # noqa: BLE001
        return None
    if not filas:
        return None
    return {"dominio": filas[0][0], "ultima_carga_ts": filas[0][1].isoformat() if filas[0][1] else None}


def _where(cat: ReporteDef, *, periodo: date | None, sucursales: list[int] | None, marca: str | None, tecnico_id: int | None) -> tuple[str, dict]:
    clausulas: list[str] = []
    params: dict = {}
    if "periodo" in cat.filtros_soportados and periodo is not None:
        clausulas.append("periodo = {periodo:Date}")
        params["periodo"] = periodo
    if "sucursal" in cat.filtros_soportados and sucursales is not None:
        clausulas.append("sucursal_id IN {sucursales:Array(Int64)}")
        params["sucursales"] = sucursales
    if "marca" in cat.filtros_soportados and marca:
        clausulas.append("marca = {marca:String}")
        params["marca"] = marca
    if "tecnico" in cat.filtros_soportados and tecnico_id is not None:
        clausulas.append("tecnico_id = {tecnico_id:Int64}")
        params["tecnico_id"] = tecnico_id
    where = (" WHERE " + " AND ".join(clausulas)) if clausulas else ""
    return where, params


def _valor_json(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if hasattr(v, "__float__") and not isinstance(v, (int, float, bool)):
        return float(v)  # Decimal de clickhouse-connect
    return v


def _shape_chart(cat: ReporteDef, columnas: list[str], filas: list[dict]) -> tuple[list[str], list[dict]]:
    if not cat.col_categoria or cat.col_categoria not in columnas:
        return [], []
    categorias = [str(f.get(cat.col_categoria, "")) for f in filas]
    series = [
        {"nombre": col, "datos": [f.get(col) for f in filas]}
        for col in cat.cols_series
        if col in columnas
    ]
    return categorias, series


# ------------------------------------------------------------------ pública
def reporte(slug: str, *, user: CurrentUser, periodo: str | None, sucursal_id: int | None, marca: str | None, tecnico_id: int | None) -> dict:
    cat = CATALOGO.get(slug)
    if cat is None:
        raise NotFoundError(f"Reporte desconocido: {slug}")

    sucursales = _sucursales_permitidas(user, sucursal_id) if "sucursal" in cat.filtros_soportados else None
    periodo_fecha = _periodo_a_fecha(periodo) if "periodo" in cat.filtros_soportados else None

    filtros_aplicados = {
        k: v for k, v in {
            "periodo": periodo if periodo_fecha else None,
            "sucursal_id": sucursal_id if sucursales else None,
            "marca": marca if "marca" in cat.filtros_soportados else None,
            "tecnico_id": tecnico_id if "tecnico" in cat.filtros_soportados else None,
        }.items() if v is not None
    }

    try:
        cliente = get_client()
        where, params = _where(cat, periodo=periodo_fecha, sucursales=sucursales, marca=marca, tecnico_id=tecnico_id)
        resultado = cliente.query(f"SELECT * FROM wh.{cat.modelo_ch}{where} LIMIT 20000", parameters=params)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Reporte '%s' no disponible: %s", slug, exc)
        return {"disponible": False, "motivo": _MOTIVO_NO_DISPONIBLE, "frescura": _frescura(), "slug": slug, "titulo": cat.titulo}

    columnas = resultado.column_names
    filas = [{c: _valor_json(v) for c, v in zip(columnas, fila)} for fila in resultado.result_rows]
    categorias, series = _shape_chart(cat, columnas, filas)

    return {
        "disponible": True,
        "slug": cat.slug,
        "titulo": cat.titulo,
        "tipo_grafico": cat.tipo_grafico,
        "filtros_soportados": list(cat.filtros_soportados),
        "filtros_aplicados": filtros_aplicados,
        "categorias": categorias,
        "series": series,
        "filas": filas,
        "total_filas": len(filas),
        "frescura": _frescura(),
    }


_TENDENCIA_NEUTRA = {"valor": None, "direccion": "estable"}


def _kpi_valor(sql: str, params: dict) -> float | None:
    cliente = get_client()
    filas = cliente.query(sql, parameters=params).result_rows
    if not filas or filas[0][0] is None:
        return None
    return _valor_json(filas[0][0])


def panel(*, user: CurrentUser, periodo: str | None, sucursal_id: int | None) -> dict:
    periodo_fecha = _periodo_a_fecha(periodo) or date.today().replace(day=1)
    sucursales = _sucursales_permitidas(user, sucursal_id)
    suc_where = "AND sucursal_id IN {sucursales:Array(Int64)}" if sucursales is not None else ""
    suc_params = {"sucursales": sucursales} if sucursales is not None else {}

    try:
        get_client()  # valida que el warehouse responde antes de armar los 6 KPIs
    except Exception as exc:  # noqa: BLE001
        logger.warning("Panel de Gerencia no disponible: %s", exc)
        return {"disponible": False, "motivo": _MOTIVO_NO_DISPONIBLE, "frescura": _frescura(), "kpis": []}

    def _kpi(sql: str, extra_params: dict | None = None) -> float | None:
        try:
            return _kpi_valor(sql, {"periodo": periodo_fecha, **suc_params, **(extra_params or {})})
        except Exception as exc:  # noqa: BLE001 — un KPI puntual no tumba el panel entero
            logger.warning("KPI del panel falló: %s", exc)
            return None

    kpis = [
        {
            "clave": "margen_periodo",
            "titulo": "Margen del periodo",
            "valor": _kpi(f"SELECT sum(margen_ventas) + sum(margen_servicios) FROM wh.rentabilidad_neta_sucursal WHERE periodo = {{periodo:Date}} {suc_where}"),
            "unidad": "USD",
            "tendencia": _TENDENCIA_NEUTRA,
            "drill_down": {"tipo": "navegar", "ruta": "/reportes/margen-por-marca-modelo", "filtros": {"periodo": periodo}},
        },
        {
            "clave": "rentabilidad_neta_sucursal",
            "titulo": "Rentabilidad neta por sucursal",
            "valor": _kpi(f"SELECT sum(rentabilidad_neta) FROM wh.rentabilidad_neta_sucursal WHERE periodo = {{periodo:Date}} {suc_where}"),
            "unidad": "USD",
            "tendencia": _TENDENCIA_NEUTRA,
            "drill_down": {"tipo": "navegar", "ruta": "/contabilidad/rentabilidad-sucursal", "filtros": {}},
        },
        {
            "clave": "cxc_vencidas",
            "titulo": "Cuentas por cobrar vencidas",
            "valor": _kpi(f"SELECT sum(saldo) FROM wh.aging_cxc_cxp WHERE tipo = 'cxc' AND dias_antiguedad > 30 {suc_where}"),
            "unidad": "USD",
            "tendencia": _TENDENCIA_NEUTRA,
            "drill_down": {"tipo": "navegar", "ruta": "/contabilidad/cuentas-por-cobrar", "filtros": {}},
        },
        {
            "clave": "rotacion_stock",
            "titulo": "Rotación de stock",
            "valor": _kpi(f"SELECT avg(dias_promedio_rotacion) FROM wh.rotacion_stock WHERE periodo = {{periodo:Date}} {suc_where}"),
            "unidad": "días",
            "tendencia": _TENDENCIA_NEUTRA,
            "drill_down": {"tipo": "navegar", "ruta": "/reportes/rotacion-stock", "filtros": {"periodo": periodo}},
        },
        {
            "clave": "productividad_tecnicos",
            "titulo": "Productividad de técnicos",
            "valor": _kpi(f"SELECT sum(ordenes_completadas) FROM wh.productividad_tecnico WHERE periodo = {{periodo:Date}} {suc_where}"),
            "unidad": "órdenes",
            "tendencia": _TENDENCIA_NEUTRA,
            "drill_down": {"tipo": "navegar", "ruta": "/reportes/productividad-tecnico", "filtros": {"periodo": periodo}},
        },
        {
            "clave": "clientes_por_nivel",
            "titulo": "Clientes en el nivel más alto",
            "valor": _kpi("SELECT clientes FROM wh.clientes_por_nivel ORDER BY orden DESC LIMIT 1", {}),
            "unidad": "clientes",
            "tendencia": _TENDENCIA_NEUTRA,
            "drill_down": {"tipo": "navegar", "ruta": "/reportes/clientes-por-nivel", "filtros": {}},
        },
    ]
    return {"disponible": True, "frescura": _frescura(), "kpis": kpis}


# -------------------------------------------------------- índice §4.11.1
_REPORTES_SIMPLES = [
    {"titulo": "Agenda de citas del día/semana", "modulo": "citas", "ruta": "/citas/agenda", "rbac": ("citas", "consultar")},
    {"titulo": "Estado de inventario actual (relojes)", "modulo": "inventario", "ruta": "/inventario", "rbac": ("inventario_relojes", "consultar")},
    {"titulo": "Estado de inventario actual (piezas)", "modulo": "piezas", "ruta": "/piezas", "rbac": ("piezas", "consultar")},
    {"titulo": "Órdenes de trabajo en curso", "modulo": "servicio_tecnico", "ruta": "/taller/ordenes-en-curso", "rbac": ("ordenes_trabajo", "consultar")},
    {"titulo": "Cuentas por cobrar pendientes", "modulo": "contabilidad", "ruta": "/contabilidad/cuentas-por-cobrar", "rbac": ("contable", "consultar")},
    {"titulo": "Historial de un cliente", "modulo": "clientes", "ruta": "/clientes", "rbac": ("clientes_fidelizacion", "consultar")},
    {"titulo": "Historial de servicios de un reloj (por N.º de serie)", "modulo": "inventario", "ruta": "/inventario", "rbac": ("inventario_relojes", "consultar")},
    {"titulo": "Informe de servicios / arreglos", "modulo": "servicio_tecnico", "ruta": "/taller/informe-servicios", "rbac": ("ordenes_trabajo", "consultar")},
]


def indice(*, user: CurrentUser, permisos: dict[str, list[str]]) -> dict:
    def _permitido(modulo: str, operacion: str) -> bool:
        if user.es_gerencia:
            return True
        return operacion in permisos.get(modulo, [])

    simples = [
        {"titulo": r["titulo"], "modulo": r["modulo"], "ruta": r["ruta"]}
        for r in _REPORTES_SIMPLES
        if _permitido(*r["rbac"])
    ]
    complejos_permitido = user.es_gerencia or "consultar" in permisos.get("reportes", [])
    complejos = [
        {"slug": c.slug, "titulo": c.titulo, "tipo_grafico": c.tipo_grafico}
        for c in CATALOGO.values()
    ] if complejos_permitido else []
    return {"simples": simples, "complejos": complejos}
