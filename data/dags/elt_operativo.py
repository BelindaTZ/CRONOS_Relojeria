"""DAG `elt_operativo` (feature 012): Extract PostgreSQL (solo lectura) → Load
raw (`landing-zone`, MinIO) → Load warehouse (ClickHouse) → Transform.

Una fila de tareas por dominio (`dags/config.py::DOMINIOS`), cada fase
observable por separado en la UI de Airflow (Spec §FR-005):

    seed_dim_fecha >> extract_<dominio> >> load_raw_<dominio> >>
        load_wh_<dominio> >> transform_<dominio> >> landing_zone_retencion >> limpiar_tmp

`max_active_runs=1` evita que dos corridas del mismo DAG se solapen (Spec
"Edge Cases"). Añadir un dominio nuevo = agregarlo a `config.py`, nada se toca
aquí (FR-018, `CONVENCIONES.md` "cómo añadir un dominio nuevo").
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from dags.config import DOMINIOS, WATERMARK_INICIAL, frecuencia_default
from lib import db as libdb
from lib import extract as libextract
from lib import freshness as libfreshness
from lib import landing as liblanding
from lib import load as libload

logger = logging.getLogger("cronos.elt.dag")

TMP_ROOT = Path(os.environ.get("ELT_TMP_DIR", "/opt/airflow/tmp"))


def _tmp_dir(run_id: str) -> Path:
    return TMP_ROOT / run_id.replace(":", "_").replace("+", "_")


def _extract(dominio_nombre: str, **context) -> None:
    dominio = DOMINIOS[dominio_nombre]
    run_id = context["run_id"]
    ch = libdb.clickhouse_client()
    watermark = WATERMARK_INICIAL
    if dominio.modo == "incremental":
        watermark = libfreshness.watermark_vigente(
            ch, dominio=dominio.nombre, tabla=dominio.tabla_destino, valor_inicial=WATERMARK_INICIAL
        )
    inicio = datetime.now(timezone.utc)
    try:
        resultado = libextract.extraer(dominio, run_id, _tmp_dir(run_id), watermark)
    except Exception as exc:  # noqa: BLE001
        libfreshness.registrar_corrida(
            ch, run_id=run_id, dominio=dominio.nombre, fase="extract",
            inicio=inicio, fin=datetime.now(timezone.utc), estado="error", detalle_error=str(exc),
        )
        raise
    libfreshness.registrar_corrida(
        ch, run_id=run_id, dominio=dominio.nombre, fase="extract",
        inicio=inicio, fin=datetime.now(timezone.utc), estado="ok", filas=resultado.filas,
    )
    context["ti"].xcom_push(key="filas", value=resultado.filas)
    context["ti"].xcom_push(key="max_updated_at", value=resultado.max_updated_at)


def _load_raw(dominio_nombre: str, **context) -> None:
    dominio = DOMINIOS[dominio_nombre]
    run_id = context["run_id"]
    ch = libdb.clickhouse_client()
    ruta_local = _tmp_dir(run_id) / f"{dominio.nombre}.ndjson"
    inicio = datetime.now(timezone.utc)
    try:
        liblanding.subir(dominio.nombre, run_id, ruta_local)
    except Exception as exc:  # noqa: BLE001
        libfreshness.registrar_corrida(
            ch, run_id=run_id, dominio=dominio.nombre, fase="load_raw",
            inicio=inicio, fin=datetime.now(timezone.utc), estado="error", detalle_error=str(exc),
        )
        raise
    libfreshness.registrar_corrida(
        ch, run_id=run_id, dominio=dominio.nombre, fase="load_raw",
        inicio=inicio, fin=datetime.now(timezone.utc), estado="ok",
    )


def _load_wh(dominio_nombre: str, **context) -> None:
    dominio = DOMINIOS[dominio_nombre]
    run_id = context["run_id"]
    ch = libdb.clickhouse_client()
    ruta_descarga = _tmp_dir(run_id) / f"{dominio.nombre}.landing.ndjson"
    inicio = datetime.now(timezone.utc)
    max_ua = context["ti"].xcom_pull(task_ids=f"extract_{dominio.nombre}", key="max_updated_at")
    try:
        liblanding.descargar(dominio.nombre, run_id, ruta_descarga)
        filas = libload.cargar_a_clickhouse(ch, dominio, ruta_descarga)
    except Exception as exc:  # noqa: BLE001
        libfreshness.registrar_corrida(
            ch, run_id=run_id, dominio=dominio.nombre, fase="load_wh",
            inicio=inicio, fin=datetime.now(timezone.utc), estado="error", detalle_error=str(exc),
        )
        libfreshness.actualizar_frescura(
            ch, dominio=dominio.nombre, ultima_carga_ts=datetime.now(timezone.utc),
            max_updated_at_origen=None, run_id=run_id, estado="error",
        )
        raise

    if dominio.modo == "incremental" and max_ua:
        libfreshness.avanzar_watermark(
            ch, dominio=dominio.nombre, tabla=dominio.tabla_destino, run_id=run_id, nuevo_valor=max_ua,
        )
    estado_frescura = "ok" if (filas or dominio.modo == "full") else "sin_datos"
    libfreshness.actualizar_frescura(
        ch, dominio=dominio.nombre, ultima_carga_ts=datetime.now(timezone.utc),
        max_updated_at_origen=max_ua, run_id=run_id, estado=estado_frescura,
    )
    libfreshness.registrar_corrida(
        ch, run_id=run_id, dominio=dominio.nombre, fase="load_wh",
        inicio=inicio, fin=datetime.now(timezone.utc), estado="ok", filas=filas,
    )


def _transform(dominio_nombre: str, **context) -> None:
    """Los dominios ya extraen denormalizado al grano de su tabla destino
    (`config.py`) — no hay agregación in-warehouse adicional por dominio. Esta
    tarea queda como punto de extensión explícito (FR-005 exige la fase
    Transform observable); los 18 modelos de reporte de §4.11.2 son VISTAS
    sobre los hechos/dimensiones ya cargados (`040_views_reportes.sql`), no
    requieren un paso de transformación propio por dominio."""
    dominio = DOMINIOS[dominio_nombre]
    run_id = context["run_id"]
    ch = libdb.clickhouse_client()
    inicio = datetime.now(timezone.utc)
    libfreshness.registrar_corrida(
        ch, run_id=run_id, dominio=dominio.nombre, fase="transform",
        inicio=inicio, fin=datetime.now(timezone.utc), estado="ok",
    )


def _seed_dim_fecha(**context) -> None:
    libload.asegurar_dim_fecha(libdb.clickhouse_client())


def _landing_zone_retencion(**context) -> None:
    dias = int(os.environ.get("LANDING_ZONE_RETENCION_DIAS", "30"))
    liblanding.purgar_antiguos(dias)


def _limpiar_tmp(**context) -> None:
    shutil.rmtree(_tmp_dir(context["run_id"]), ignore_errors=True)


with DAG(
    dag_id="elt_operativo",
    description=(
        "ELT operativo -> warehouse (012). Extract PostgreSQL (solo lectura) -> "
        "Load raw (landing-zone) -> Load warehouse (ClickHouse) -> Transform."
    ),
    schedule=frecuencia_default(),
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    tags=["cronos", "012", "elt"],
) as dag:
    seed = PythonOperator(task_id="seed_dim_fecha", python_callable=_seed_dim_fecha)
    retencion = PythonOperator(task_id="landing_zone_retencion", python_callable=_landing_zone_retencion)
    limpiar = PythonOperator(task_id="limpiar_tmp", python_callable=_limpiar_tmp, trigger_rule="all_done")

    for _nombre in DOMINIOS:
        t_extract = PythonOperator(
            task_id=f"extract_{_nombre}", python_callable=_extract, op_kwargs={"dominio_nombre": _nombre},
        )
        t_load_raw = PythonOperator(
            task_id=f"load_raw_{_nombre}", python_callable=_load_raw, op_kwargs={"dominio_nombre": _nombre},
        )
        t_load_wh = PythonOperator(
            task_id=f"load_wh_{_nombre}", python_callable=_load_wh, op_kwargs={"dominio_nombre": _nombre},
        )
        t_transform = PythonOperator(
            task_id=f"transform_{_nombre}", python_callable=_transform, op_kwargs={"dominio_nombre": _nombre},
        )
        seed >> t_extract >> t_load_raw >> t_load_wh >> t_transform >> retencion

    retencion >> limpiar
