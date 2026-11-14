# Implementation Plan: Plataforma de Datos Táctico-Estratégica (ELT)

**Branch**: `012-plataforma-datos-tactico-estrategico` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Feature de infraestructura. Agrega al `docker-compose.yml` (única junto con 000) los servicios **ClickHouse** y **Airflow** (webserver + scheduler, `LocalExecutor`) y el bucket **`landing-zone`** en el MinIO ya provisionado por 000. Construye desde cero los **DAGs del flujo ELT** con tareas explícitas por fase — **Extract** (solo lectura de PostgreSQL) → **Load raw** (a `landing-zone`, nunca fuente de negocio) → **Load warehouse** (a ClickHouse) → **Transform** (in-warehouse) — con extracción **incremental** (watermark), reprocesable, y modelo de warehouse que cubre **todos** los reportes analíticos de §4.11.2 con filtros por periodo/sucursal/marca/técnico. Corrida **horaria** por defecto, **disparo manual** y **frecuencia configurable**. Expone el **estado de frescura** para 013. La app operativa (001–011) no depende de estos servicios.

## Technical Context

**Language/Version**: Python 3.12 (DAGs); SQL (ClickHouse); YAML (compose, Airflow)

**Primary Dependencies**: Apache Airflow (`LocalExecutor`), ClickHouse server + `clickhouse-connect`/`clickhouse-driver`, `minio` SDK, `psycopg` (solo lectura sobre PostgreSQL); opcional dbt-core para las transformaciones in-warehouse

**Storage**: ClickHouse (warehouse); MinIO `landing-zone` (raw); PostgreSQL (fuente, solo lectura)

**Testing**: `pytest` para las funciones de extracción/carga (idempotencia, watermark); pruebas de los modelos de ClickHouse contra datos de fixtures; validación de que la app operativa sigue viva con ClickHouse caído

**Target Platform**: Docker Desktop (mismo compose)

**Project Type**: Data platform — `data/` en la raíz (DAGs, modelos ClickHouse, config Airflow)

**Performance Goals**: corrida completa incremental < 10 min a volumen del negocio; consulta de un modelo < 3 s

**Constraints**: ELT (no ETL); `landing-zone` nunca consultado como fuente de negocio; extracción read-only; solo 000/012 tocan el compose; sin forecasting/ML; sin streaming/CDC

**Scale/Scope**: ~decenas de miles de filas totales; ~18 reportes analíticos (§4.11.2)

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | Trazabilidad a §4.11.2 (lista completa) y §4.11.3; citas a Const. Ppio III y "Flujo de Trabajo" §012. ✅ |
| II | No aplica (no es OLTP; extracción read-only). ✅ |
| III | **Esta feature implementa el flujo ELT del Principio III**: Extract → Load raw (`landing-zone`) → Load → Transform in-warehouse, Airflow. ✅ |
| IV | Acceso a Airflow/ClickHouse por credenciales `.env`; los reportes en 013 declaran permisos. ✅ |
| V | El backend operativo no recalcula agregaciones; la lógica analítica vive en el warehouse. ✅ |
| VI | Referencia 001–011 como fuente; no los modifica. ✅ |
| VII | Sin streaming, sin CDC complejo, sin ML (volumen pequeño, §4.11.3). ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | Credenciales `.env`; respaldo del warehouse y DAGs; app operativa resiliente a ClickHouse caído. ✅ |
| X | `data/dags/`, `data/warehouse/`, `data/airflow/` separados; funciones reutilizables en `data/lib/`. ✅ |
| XI | (013 consume el estado de frescura para "actualizado a HH:MM"). ✅ |
| XII | No aplica (sin UI propia). ✅ |

**Resultado**: PASS.

## Project Structure

```text
docker-compose.yml           # + clickhouse, airflow-webserver, airflow-scheduler (LocalExecutor)
.env.example                 # + CLICKHOUSE_*, AIRFLOW_*, LANDING_ZONE_BUCKET

data/
├── airflow/
│   ├── airflow.cfg
│   └── requirements.txt
├── dags/
│   ├── elt_operativo.py     # DAG principal: tasks extract_* / load_raw_* / load_wh_* / transform_*
│   └── config.py            # dominios, tablas, watermarks, frecuencia (parametrizable)
├── lib/
│   ├── extract.py           # lectura incremental de PostgreSQL (read-only)
│   ├── landing.py           # escritura/lectura de landing-zone (parquet/ndjson por corrida)
│   ├── load.py              # carga a ClickHouse idempotente
│   └── freshness.py         # estado de frescura consultable
└── warehouse/
    ├── ddl/                 # tablas de hechos y dimensiones de ClickHouse
    └── transform/           # SQL (o modelos dbt) de las agregaciones de §4.11.2

backend/src/reportes_estado/  # endpoint mínimo que expone el estado de frescura (leído por 013)
```

**Structure Decision**: Toda la plataforma de datos vive bajo `data/` (separada de `backend/` y `frontend/`). El único punto de contacto con el backend operativo es un endpoint de solo lectura del estado de frescura, para que 013 muestre la hora de última actualización sin acoplarse a ClickHouse.

## Complexity Tracking

| Elemento | Por qué | Alternativa más simple rechazada porque |
|---|---|---|
| Airflow + ClickHouse | Const. Ppio III y "Flujo de Trabajo" §012 lo asignan explícitamente a esta feature | Cron + vistas materializadas en PostgreSQL: la constitución exige el warehouse separado y Airflow |
| DAG con fases separadas | Spec §FR-005 (tareas nombradas E/L/T observables) | Un solo script monolítico: no observable, difícil de reintentar por fase |
