# Research: Plataforma de Datos Táctico-Estratégica (ELT)

**Feature**: `012-plataforma-datos-tactico-estrategico` | **Phase**: 0 | **Date**: 2026-09-10

Sin `NEEDS CLARIFICATION` (frecuencia horaria resuelta por el negocio).

## D1 — Servicios en el compose

- **Decisión**: `clickhouse` (imagen oficial, puerto 8123/9000 interno), `airflow-webserver` + `airflow-scheduler` (misma imagen, `LocalExecutor`, metadata DB = una base PostgreSQL propia de Airflow, **separada** de la operativa). Bucket `landing-zone` creado por un job `minio-init` (extiende el de 000).
- **Rationale**: Const. "Flujo de Trabajo" §012.
- **Alternativas**: `CeleryExecutor` (necesita broker, sobre-ingeniería); Airflow en la misma DB operativa (acoplamiento y riesgo).

## D2 — Flujo ELT y estructura del DAG

- **Decisión**: un DAG `elt_operativo` con tareas por **dominio** y **fase**:
  - `extract_<dominio>` → lee el delta de PostgreSQL (watermark) en solo lectura.
  - `load_raw_<dominio>` → escribe el raw a `landing-zone/<dominio>/<run_id>/` (parquet o ndjson).
  - `load_wh_<dominio>` → carga el raw a tablas *staging* de ClickHouse (idempotente por `run_id` + clave natural).
  - `transform_<modelo>` → agregaciones in-warehouse hacia las tablas de hechos/dimensiones de §4.11.2.
  Dependencias: `extract → load_raw → load_wh → transform`.
- **Rationale**: Const. Ppio III (ELT, no ETL); Spec §FR-003, §FR-005.

## D3 — Incrementalidad y reprocesamiento

- **Decisión**: `watermark` por (dominio, tabla) persistido (tabla de control en la DB de Airflow o en ClickHouse). Extracción por `updated_at > watermark`. Carga a ClickHouse con `ReplacingMergeTree` (dedup por clave + versión) para que un reintento no duplique. Reprocesar un rango = borrar el watermark o pasar `--full-refresh`.
- **Rationale**: Spec §FR-007; volumen pequeño (Ppio VII).
- **Alternativas**: CDC con Debezium — sobre-ingeniería.

## D4 — Anulaciones y bajas

- **Decisión**: los hechos que se anulan (venta anulada, merma, cambio de nivel) traen su estado actual en el `updated_at`; `ReplacingMergeTree` los sobrescribe con el estado nuevo (p. ej. `estado = anulada`), y las agregaciones filtran por estado.
- **Rationale**: Spec §FR-013; §6.

## D5 — Modelo del warehouse (§4.11.2)

- **Decisión**: tablas de hechos (`fact_venta`, `fact_orden_trabajo`, `fact_movimiento_inventario`, `fact_cita`, `fact_merma`, `fact_asiento`, `fact_pieza_uso`, `fact_lubricacion`, `fact_cxc_cxp`) y dimensiones (`dim_fecha`, `dim_sucursal`, `dim_marca`, `dim_modelo`, `dim_tecnico`, `dim_cliente`, `dim_nivel`, `dim_proveedor`). Los 18 reportes de §4.11.2 se resuelven como consultas/vistas materializadas sobre estos hechos con las claves de filtro (periodo, sucursal, marca, técnico).
- **Rationale**: Spec §FR-008, §FR-009.

## D6 — Estado de frescura

- **Decisión**: `data/lib/freshness.py` escribe, tras cada `load_wh_<dominio>` exitoso, `{dominio, ultimo_run_id, ultima_carga_ts, max_updated_at_origen}`. Un endpoint mínimo del backend (`GET /reportes/estado-frescura`) lo lee (desde ClickHouse o desde un archivo en `landing-zone`/control) y 013 lo muestra.
- **Rationale**: Spec §FR-010; Const. Ppio IX ("carga asíncrona").

## D7 — Resiliencia de la app operativa

- **Decisión**: el backend operativo NO abre conexión a ClickHouse en el arranque ni en el health-check de 000. Solo 013 consulta ClickHouse, y ante fallo muestra "datos no disponibles". Airflow y ClickHouse pueden estar caídos sin afectar 001–011.
- **Rationale**: Spec §FR-011; Const. Ppio III, Ppio IX.

## D8 — Frecuencia configurable y disparo manual

- **Decisión**: `schedule_interval` del DAG por defecto `@hourly`, leído de `data/dags/config.py` que a su vez puede leer una variable de Airflow (`elt_frecuencia`) ajustable sin redeploy. "Actualizar ahora" = disparo manual del DAG (Airflow REST API o `airflow dags trigger`), expuesto por 013 mediante un endpoint del backend que llama a esa API.
- **Rationale**: Spec §FR-017; decisión del negocio.

## D9 — Respaldo

- **Decisión**: script documentado para `clickhouse-backup` (o `BACKUP` nativo) del warehouse y copia de `data/dags/` + variables de Airflow. Sin automatización de cron en dev.
- **Rationale**: Esp. §6; Spec §FR-015.

## D10 — Transformaciones: SQL vs dbt

- **Decisión**: SQL plano versionado en `data/warehouse/transform/` para el MVP; dbt-core opcional si crece la complejidad. No es un requisito duro.
- **Rationale**: Ppio VII (empezar simple).
