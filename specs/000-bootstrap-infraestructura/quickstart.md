# Quickstart: Bootstrap de Infraestructura

**Feature**: `000-bootstrap-infraestructura` | **Phase**: 1

Guía de validación end-to-end. Prueba que la plataforma arranca, es saludable, aplica migraciones idempotentes y expone los buckets. No contiene código de implementación.

## Prerrequisitos

- Docker Desktop en ejecución
- Puertos libres: 5432 (db), 8000 (backend), 5173 (frontend), 9000/9001 (MinIO), 5050 (pgAdmin, opcional)
- Repo clonado en la raíz del proyecto

## Setup

```bash
cp .env.example .env          # editar solo si hay conflicto de puertos
docker compose up -d --build
```

## Escenarios de validación

### V1 — Stack saludable (US1)
```bash
docker compose ps            # db, backend, frontend, minio → "healthy"/"running"
curl -s http://localhost:8000/health
```
**Esperado**: JSON `{"status":"ok","db":"up","storage":"up"}`, HTTP 200.

### V2 — Salud degradada (US2)
```bash
docker compose stop db
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
docker compose start db
```
**Esperado**: `503` con `db` detenida; vuelve a `200` tras `start`.

### V3 — Frontend shell y paleta (US2)
- Abrir `http://localhost:5173`
- **Esperado**: barra de navegación horizontal superior fija con las categorías de primer nivel; color de barra `#0F172A` (Primary-900); chequeo de contraste AA para texto sobre Primary y Secondary (script `scripts/check_contrast.mjs`).

### V4 — Migraciones idempotentes (US3)
```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic upgrade head      # segunda vez: sin cambios
docker compose exec backend python -c "import sqlalchemy as sa, os; e=sa.create_engine(os.environ['DATABASE_URL']); print(sorted(sa.inspect(e).get_table_names()))"
docker compose exec backend alembic downgrade base     # limpia
docker compose exec backend alembic upgrade head       # reconstruye
```
**Esperado**: tras `upgrade` existen `rol`, `modulo`, `operacion`, `permiso_modulo`, `permiso_operacion`; `operacion` tiene 4 filas; el resto 0 filas; la segunda corrida no imprime migraciones aplicadas; `downgrade base` deja el esquema sin esas tablas.

### V5 — Modularidad (US4)
```bash
ls backend/src/shared backend/src/health
ls frontend/src/shared frontend/src/health
git status --porcelain        # tras añadir un módulo dummy: cambios solo en su carpeta + registro de rutas
```
**Esperado**: existen `shared/` y el módulo plantilla `health/` con capas router/service/repository (backend) y components/composables/services (frontend).

### V6 — Buckets MinIO (US5)
```bash
docker compose exec minio mc ls local/
docker compose exec minio mc cp /etc/hostname local/reloj-imagenes/prueba.txt
docker compose exec minio mc cat local/reloj-imagenes/prueba.txt
curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/comprobantes-venta/x   # sin credenciales
```
**Esperado**: se listan `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios`, `documentos`; NO aparece `landing-zone`; el objeto de prueba se recupera; el acceso anónimo a `comprobantes-venta` es denegado.

### V7 — Persistencia
```bash
docker compose down && docker compose up -d
```
**Esperado**: los datos de PostgreSQL y los objetos de MinIO persisten (volúmenes nombrados).

### V8 — Respaldo (Esp. §6)
```bash
bash scripts/backup_pg.sh ./backups
```
**Esperado**: se genera un archivo `.sql`/`.dump` con marca de tiempo.

## Contratos relacionados

- [`contracts/health.openapi.yaml`](./contracts/health.openapi.yaml)

## Criterio de "listo"

Los 8 escenarios pasan; `docker compose up` a saludable en < 5 min; 0 secretos hardcodeados (revisión).
