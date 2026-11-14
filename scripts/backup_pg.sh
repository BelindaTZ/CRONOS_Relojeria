#!/usr/bin/env bash
# Respaldo de PostgreSQL de CRONOS (Especificación §6).
#
# Uso:   bash scripts/backup_pg.sh [DIRECTORIO_SALIDA]
#        DIRECTORIO_SALIDA por defecto: ./backups
#
# Ejecuta pg_dump dentro del contenedor `db` del docker-compose y guarda un
# volcado comprimido con marca de tiempo. La automatización periódica (cron /
# Airflow) es tarea de operación, no de esta feature.
set -euo pipefail

OUT_DIR="${1:-./backups}"
COMPOSE_SERVICE="db"

# Carga variables de .env si existe (POSTGRES_USER / POSTGRES_DB).
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi
PG_USER="${POSTGRES_USER:-cronos}"
PG_DB="${POSTGRES_DB:-cronos}"

mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR%/}/cronos_${STAMP}.sql.gz"

echo "Respaldo de la base '${PG_DB}' (usuario '${PG_USER}') → ${OUT_FILE}"
docker compose exec -T "$COMPOSE_SERVICE" pg_dump -U "$PG_USER" -d "$PG_DB" --clean --if-exists \
  | gzip > "$OUT_FILE"

echo "OK: $(du -h "$OUT_FILE" | cut -f1) escritos."
echo "Restaurar con:"
echo "  gunzip -c ${OUT_FILE} | docker compose exec -T ${COMPOSE_SERVICE} psql -U ${PG_USER} -d ${PG_DB}"
