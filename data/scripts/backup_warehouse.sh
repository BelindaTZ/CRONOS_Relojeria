#!/usr/bin/env bash
# Respaldo del warehouse (ClickHouse) + de los DAGs/variables de Airflow
# (Spec §FR-015, research D9). Sin automatización de cron en dev — se corre a
# mano o desde un cron externo del anfitrión.
#
# Uso:  bash data/scripts/backup_warehouse.sh ./backups
set -euo pipefail

DESTINO="${1:?Uso: backup_warehouse.sh <directorio-destino>}"
SELLO="$(date -u +%Y%m%dT%H%M%SZ)"
CARPETA="${DESTINO%/}/${SELLO}"
mkdir -p "$CARPETA"

echo "== Respaldo CRONOS ELT (012) -> ${CARPETA} =="

# 1) Esquema + datos de ClickHouse (BACKUP nativo a un disco montado en el
#    propio contenedor — para producción, apuntar a un disco S3/MinIO
#    configurado en config.xml; en dev basta el disco por defecto).
echo "-- ClickHouse: BACKUP nativo --"
docker compose exec -T clickhouse clickhouse-client -q \
  "BACKUP DATABASE wh, DATABASE ctl TO Disk('backups', 'elt_${SELLO}.zip')" \
  > "${CARPETA}/clickhouse_backup.log" 2>&1 || {
    echo "  (falló el BACKUP nativo — revisa ${CARPETA}/clickhouse_backup.log; alternativa: clickhouse-backup)"
  }

# 2) DDL como texto plano (siempre útil, además del backup binario)
echo "-- ClickHouse: DDL de referencia --"
docker compose exec -T clickhouse clickhouse-client -q \
  "SHOW CREATE DATABASE wh" > "${CARPETA}/wh_schema.sql" 2>/dev/null || true

# 3) DAGs y warehouse/ tal como están en el repo (versión desplegada)
echo "-- DAGs y warehouse (copia del repo) --"
cp -r "$(dirname "$0")/../dags" "${CARPETA}/dags"
cp -r "$(dirname "$0")/../warehouse" "${CARPETA}/warehouse"

# 4) Variables de Airflow (incluye elt_frecuencia)
echo "-- Variables de Airflow --"
docker compose exec -T airflow-webserver airflow variables export \
  "/opt/airflow/tmp/variables_${SELLO}.json" > /dev/null 2>&1 || true
docker compose cp "airflow-webserver:/opt/airflow/tmp/variables_${SELLO}.json" \
  "${CARPETA}/airflow_variables.json" 2>/dev/null || \
  echo "  (no se pudo copiar variables de Airflow — revisa el contenedor)"

echo "== Respaldo completo en ${CARPETA} =="
