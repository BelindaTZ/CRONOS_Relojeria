# Quickstart: Plataforma de Datos Táctico-Estratégica

**Feature**: `012-plataforma-datos-tactico-estrategico` | **Phase**: 1

## Prerrequisitos

- 000 implementada (MinIO ya existe); features 001–011 con datos operativos (o fixtures cargados)
- `.env` con `CLICKHOUSE_*`, `AIRFLOW_*`, `LANDING_ZONE_BUCKET=landing-zone`

## Setup

```bash
docker compose up -d --build          # ahora levanta también clickhouse, airflow-webserver, airflow-scheduler
docker compose exec airflow-webserver airflow db migrate
docker compose exec clickhouse clickhouse-client --queries-file /warehouse/ddl/*.sql
```

## Escenarios

### V1 — Servicios y bucket (US1)
```bash
docker compose ps                     # clickhouse, airflow-* → healthy
docker compose exec minio mc ls local/  # ahora incluye landing-zone
curl -s http://localhost:8000/health  # 000 sigue 200 (no depende de clickhouse)
```

### V2 — Extracción a landing-zone (US2)
```bash
docker compose exec airflow-webserver airflow dags trigger elt_operativo
docker compose exec minio mc ls -r local/landing-zone/
docker compose logs postgres | grep -i "INSERT\|UPDATE"   # (no debe haber escrituras del pipeline)
```
- **Esperado**: aparecen archivos raw por dominio/run_id; PostgreSQL no recibió escrituras del pipeline.

### V3 — Carga y transformación (US3)
```bash
docker compose exec clickhouse clickhouse-client -q "SELECT count() FROM wh.fact_venta"
docker compose exec clickhouse clickhouse-client -q "SELECT * FROM wh.margen_por_marca_modelo LIMIT 5"
```
- **Esperado**: hechos poblados; el modelo `margen_por_marca_modelo` cuadra con el operativo; re-ejecutar el DAG no duplica filas (`ReplacingMergeTree`).

### V4 — Incrementalidad y frescura (US4)
```bash
# insertar una venta nueva en el origen
docker compose exec airflow-webserver airflow dags trigger elt_operativo
curl -s http://localhost:8000/reportes/estado-frescura
```
- **Esperado**: solo se procesa el delta; `estado-frescura` muestra `ultima_carga_ts` reciente por dominio.

### V5 — Anulación reflejada (US4)
```bash
# anular una venta en 009, correr el DAG
docker compose exec clickhouse clickhouse-client -q "SELECT estado FROM wh.fact_venta WHERE orden_venta_id = <id>"
```
- **Esperado**: `estado = anulada`; el modelo `margen_por_reloj_vendido` la excluye.

### V6 — Frecuencia y disparo manual (US4)
```bash
docker compose exec airflow-webserver airflow variables set elt_frecuencia "@daily"
curl -XPOST http://localhost:8000/reportes/actualizar-ahora
```
- **Esperado**: el `schedule_interval` cambia sin redeploy; "actualizar ahora" dispara una corrida fuera de horario.

### V7 — Resiliencia (US3)
```bash
docker compose stop clickhouse
curl -s http://localhost:8000/health                 # 200
curl -s http://localhost:8000/relojes                 # 200 (operativo intacto)
curl -s http://localhost:8000/reportes/estado-frescura # indica "no disponible" sin romper
```

### V8 — Respaldo (US7)
```bash
bash data/scripts/backup_warehouse.sh ./backups
```

## Contratos

- [`contracts/pipeline-estado.openapi.yaml`](./contracts/pipeline-estado.openapi.yaml)

## Criterio de "listo"

V1–V8 pasan; los 18 modelos de §4.11.2 poblados y cuadrando; app operativa 100% funcional con ClickHouse caído; 0 credenciales hardcodeadas en DAGs/config.
