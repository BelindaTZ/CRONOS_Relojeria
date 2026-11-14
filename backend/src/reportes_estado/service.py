"""Lógica del módulo `reportes_estado` (feature 012).

Solo lectura del estado de frescura del warehouse + disparo manual del DAG. NO
abre estas conexiones en el arranque del backend ni en `/health` (research D7,
Spec §FR-011): si ClickHouse o Airflow no responden, degrada limpio en vez de
propagar el error a la app operativa.
"""

from __future__ import annotations

import logging

from shared.config import get_settings
from shared.exceptions import ConflictError, DependencyUnavailableError

logger = logging.getLogger("cronos.reportes_estado")


def get_estado_frescura() -> dict:
    try:
        from shared.clickhouse import get_client

        cliente = get_client()
        filas = cliente.query(
            """
            SELECT dominio, ultima_carga_ts, max_updated_at_origen, ultimo_run_id, estado_ultima_corrida
            FROM ctl.pipeline_frescura FINAL
            ORDER BY dominio
            """
        ).result_rows
    except Exception as exc:  # noqa: BLE001 — ClickHouse caído/no alcanzable
        logger.warning("ClickHouse no disponible para estado-frescura: %s", exc)
        return {"disponible": False, "dominios": []}

    dominios = [
        {
            "dominio": f[0],
            "ultima_carga_ts": f[1],
            "max_updated_at_origen": f[2],
            "ultimo_run_id": f[3],
            "estado_ultima_corrida": f[4],
        }
        for f in filas
    ]
    return {"disponible": True, "dominios": dominios}


def _airflow_auth():
    import httpx

    s = get_settings()
    return httpx.BasicAuth(s.airflow_admin_user, s.airflow_admin_password)


def disparar_actualizacion() -> dict:
    """`POST /reportes/actualizar-ahora`: dispara `elt_operativo` vía la REST
    API de Airflow. 409 si ya hay una corrida en curso; 503 si Airflow no
    responde (Spec contrato `pipeline-estado.openapi.yaml`)."""
    import httpx

    s = get_settings()
    base = s.airflow_base_url.rstrip("/")
    try:
        with httpx.Client(auth=_airflow_auth(), timeout=5.0) as cliente:
            en_curso = cliente.get(
                f"{base}/api/v1/dags/elt_operativo/dagRuns",
                params={"state": "running", "limit": 1},
            )
            en_curso.raise_for_status()
            if en_curso.json().get("total_entries", 0) > 0:
                raise ConflictError("Ya hay una corrida de elt_operativo en curso")

            disparo = cliente.post(f"{base}/api/v1/dags/elt_operativo/dagRuns", json={})
            disparo.raise_for_status()
    except ConflictError:
        raise
    except Exception as exc:  # noqa: BLE001 — Airflow caído/no alcanzable
        logger.warning("Airflow no disponible para actualizar-ahora: %s", exc)
        raise DependencyUnavailableError("Airflow no está disponible") from exc

    datos = disparo.json()
    return {"run_id": datos.get("dag_run_id", ""), "estado": datos.get("state", "queued")}
