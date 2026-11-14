# Tasks: Plataforma de Datos Táctico-Estratégica (ELT)

**Feature**: `012-plataforma-datos-tactico-estrategico` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/pipeline-estado.openapi.yaml](./contracts/pipeline-estado.openapi.yaml)

**Tests**: incluidos para idempotencia, watermark, resiliencia de la app operativa y coherencia de modelos.

**MVP** = User Story 1 + User Story 2 + User Story 3 (stack + extracción + carga/transformación de un dominio).

## Phase 1: Setup

- [X] T001 Crear `data/` (`airflow/`, `dags/`, `lib/`, `warehouse/ddl/`, `warehouse/transform/`, `scripts/`) y `backend/src/reportes_estado/`
- [X] T002 [P] Añadir a `.env.example` `CLICKHOUSE_*`, `AIRFLOW_*`, `LANDING_ZONE_BUCKET`
- [X] T003 [P] `data/airflow/requirements.txt` (clickhouse-connect, minio, psycopg[binary])

## Phase 2: Foundational — Infraestructura (US1)

- [X] T004 [US1] Agregar a `docker-compose.yml` los servicios `clickhouse`, `airflow-webserver`, `airflow-scheduler` (`LocalExecutor`, DB de metadata PostgreSQL **separada** de la operativa — contenedor `airflow-db` propio)
- [X] T005 [US1] Extender el job `minio-init` para crear el bucket `landing-zone` (idempotente); NO tocar los 4 buckets de 000 — implementado como job separado `landing-zone-init` (no se tocó `minio-init` de 000)
- [X] T006 [US1] `data/warehouse/ddl/` — DDL de dimensiones y hechos de ClickHouse (`data-model.md`); tablas `pipeline_watermark`, `pipeline_corrida`, `pipeline_frescura`
- [X] T007 [US1] `data/dags/config.py` — dominios, tablas por dominio, watermark keys, `schedule_interval` desde variable `elt_frecuencia` (def. `@hourly`)
- [X] T008 [P] [US1] Test `backend/tests/test_operativo_resiliente.py` — `GET /health` (000) y endpoints operativos responden con `clickhouse` detenido
- [X] T009 [P] [US1] Verificar en `quickstart.md` V1: los 3 servicios healthy + `landing-zone` creado + `/health` 200 — verificado end-to-end (`docker compose ps` healthy, `landing-zone` creado, `/health` 200 con ClickHouse y Airflow arriba)

## Phase 3: User Story 2 — Extracción a la zona de aterrizaje (P1) 🎯 MVP

- [X] T010 [US2] `data/lib/extract.py` — lectura incremental de PostgreSQL por `updated_at > watermark`, con conexión/rol **read-only** (migración `0029_rol_elt_readonly`)
- [X] T011 [US2] `data/lib/landing.py` — escribir raw a `landing-zone/<dominio>/<run_id>/<tabla>.parquet`; retención configurable — implementado en NDJSON (formato admitido por `data-model.md`, sin dependencia nueva tipo pyarrow)
- [X] T012 [US2] `data/dags/elt_operativo.py` — tareas `extract_<dominio>` y `load_raw_<dominio>` para **todos** los dominios (no solo el piloto — el motor genérico no distingue "piloto" de "definitivo")
- [X] T013 [P] [US2] Test `data/tests/test_extract.py` — solo procesa el delta; no ejecuta escrituras sobre PostgreSQL; raw versionado por `run_id`

## Phase 4: User Story 3 — Carga y transformación en ClickHouse (P1) 🎯 MVP

- [X] T014 [US3] `data/lib/load.py` — carga de raw a ClickHouse (idempotente, motor genérico por tipo de columna vía `DESCRIBE TABLE`); hechos con `ReplacingMergeTree` (clave + `updated_at`)
- [X] T015 [US3] `data/warehouse/transform/` — decisión de diseño: cada dominio ya extrae denormalizado a su tabla destino (`config.py`), así que la agregación de los 18 modelos vive directamente como VISTAS en `warehouse/ddl/040_views_reportes.sql` (ver nota en T026)
- [X] T016 [US3] `data/dags/elt_operativo.py` — tareas `load_wh_<dominio>` y `transform_<dominio>` (para todos los dominios)
- [X] T017 [US3] `data/lib/freshness.py` — actualizar `pipeline_frescura` tras cada `load_wh` exitoso
- [X] T018 [P] [US3] Test `data/tests/test_load_transform.py` — reejecución no duplica filas; la versión más nueva gana (`ReplacingMergeTree` + `FINAL`)

## Phase 5: User Story 4 — Incrementalidad, frescura, frecuencia, anulaciones (P2)

- [X] T019 [US4] `data/lib/extract.py` — persistir/avanzar watermark por (dominio, tabla) — `data/lib/freshness.py::avanzar_watermark`/`watermark_vigente`. `--full-refresh` no se implementó como flag de CLI: el modo `"full"` por dominio (`config.py`) ya cubre el caso — reprocesa completo cada corrida, no hace falta un flag adicional para los dominios incrementales (borrar el watermark en `ctl.pipeline_watermark` logra el mismo efecto)
- [X] T020 [US4] `backend/src/reportes_estado/` — `GET /reportes/estado-frescura` (lee `pipeline_frescura`; degradación limpia si no disponible), `POST /reportes/actualizar-ahora` (Airflow REST API, 409 si ya hay una corrida en curso, 503 si Airflow no responde)
- [X] T021 [US4] `data/dags/config.py` — `schedule_interval` = variable `elt_frecuencia`; documentado en `CONVENCIONES.md` §25 (`airflow variables set elt_frecuencia "@daily"`)
- [X] T022 [US4] Manejo de anulaciones: los hechos traen `estado` actual; las 18 vistas de reporte filtran (`estado = 'confirmada'`/`'entregado'`/etc., según el hecho)
- [X] T023 [P] [US4] Test `data/tests/test_incremental.py` — watermark inicial/avance/relectura; frescura registra estado
- [X] T024 [P] [US4] Test `backend/tests/test_estado_frescura.py` — con ClickHouse caído, `estado-frescura` responde `disponible: false` sin error; con Airflow caído, `actualizar-ahora` responde 503; gating RBAC del módulo `reportes`

## Phase 6: User Story 5/6 — Cobertura completa de dominios y §4.11.2 (P2)

- [X] T025 [US6] Extender `elt_operativo` a todos los dominios: órdenes de trabajo, inventario, citas, mermas, contabilidad, fidelización, técnicos, proveedores, lubricación — 21 dominios en total (7 dimensiones + 14 hechos), verificado con `airflow tasks list elt_operativo` (84 tareas: 21 dominios × 4 fases)
- [X] T026 [US6] `data/warehouse/ddl/040_views_reportes.sql` — los 18 modelos de §4.11.2, con claves de filtro periodo/sucursal/marca/técnico donde aplica. Decisión de diseño (documentada en `CONVENCIONES.md` §25): VISTAS planas, no `MATERIALIZED VIEW` — a este volumen de negocio una vista calculada al vuelo cumple el objetivo de <3s y es más simple de mantener
- [X] T027 [P] [US6] Test `data/tests/test_modelos_4_11_2.py` — cada uno de los 18 modelos existe y es consultable — verificado además manualmente contra ClickHouse real (`SELECT count() FROM wh.<vista>` en los 18, sin error)
- [X] T028 [US6] Tolerancia a esquema nuevo: `extract` no depende de columnas fijas más allá de las que pide su SQL; un dominio sin entrada en `config.py` simplemente no se extrae — no rompe el DAG (FR-018); documentado el procedimiento para añadir uno nuevo en `CONVENCIONES.md` §25

## Phase 7: Polish & Cross-Cutting

- [X] T029 [P] `data/scripts/backup_warehouse.sh` (`BACKUP DATABASE` nativo de ClickHouse, disco `backups` vía `data/clickhouse/config.d/backups.xml`) + copia de `data/dags/`/`warehouse/` + export de variables de Airflow
- [X] T030 [P] Política de retención de `landing-zone` (job de limpieza) — implementada como tarea `landing_zone_retencion` del propio DAG (corre cada ejecución, parametrizable por `LANDING_ZONE_RETENCION_DIAS`), no un job de compose aparte
- [X] T031 [P] Revisión: 0 credenciales hardcodeadas en DAGs/config (grep) — verificado, todas vía `os.environ`/`.env`
- [X] T032 [P] `CONVENCIONES.md` §25 — cómo añadir un dominio nuevo al DAG (para features futuras)
- [X] T033 Ejecutar `quickstart.md` V1–V8 y registrar resultados — ver `CONVENCIONES.md` §25 y la verificación end-to-end de esta sesión (stack levantado, DAG disparado y corrido completo, 18 vistas pobladas y consultables, resiliencia con ClickHouse/Airflow abajo confirmada)
- [X] T034 [P] Revisar `checklists/data-pipeline.md` (cerrar DP002, DP006, DP018) — DP002 (rol de solo lectura) resuelto por `0029_rol_elt_readonly`; DP006 (reintento de una fase fallida) resuelto: cada fase registra su propio estado en `ctl.pipeline_corrida` y una excepción de una tarea Airflow no afecta el estado ya persistido de las fases previas — se puede reintentar solo la tarea fallida (`airflow tasks clear`); DP018 (cómo añadir un dominio nuevo) documentado en `CONVENCIONES.md` §25. El checklist en sí no se marcó (gate de solo lectura del reviewer, mismo criterio que 010/011).

## Dependencies & Execution Order

- Setup → US1 (infra) → US2 (extract, dominio piloto) → US3 (load/transform piloto) [MVP] → US4 (incremental/frescura/frecuencia) → US5/US6 (todos los dominios y modelos) → Polish.

## Parallel Execution Examples

- US1: T004, T005, T006 en secuencia; T008 en paralelo con T007.
- US6: los `extract_<dominio>` y `transform_<modelo>` de dominios distintos se implementan y prueban en paralelo.
- Polish: T029, T030, T031, T032 en paralelo.

## Implementation Strategy

1. **MVP**: US1 + US2 + US3 sobre el dominio `ventas` → warehouse levantado con un modelo cuadrando.
2. **Incremento 2**: US4 (incrementalidad, frescura, frecuencia configurable, anulaciones).
3. **Incremento 3**: US5/US6 (todos los dominios y los 18 modelos de §4.11.2) + Polish.

## Nota de implementación (2026-09-11)

Se implementó todo de corrido (no solo el MVP) dado que el motor de extracción/carga es genérico por diseño (`config.py::DOMINIOS`) — declarar los 21 dominios desde el principio no costó más que declarar 1, y evita una segunda ronda de trabajo repetitivo. Ver `CONVENCIONES.md` §25 para el detalle completo de decisiones de diseño y desviaciones documentadas frente a `data-model.md`/`research.md`.
