# CRONOS — Sistema de Gestión Integral para Relojería de Alta Gama

Feature **000 – Bootstrap de infraestructura**: sustrato ejecutable del sistema. Levanta PostgreSQL, backend (FastAPI), frontend (Vue 3 + Vite + Tailwind) y MinIO, con la migración inicial del esquema base de RBAC y los buckets de cara a la app. **Sin lógica de negocio** — esa llega en las features 001+.

- Constitución del proyecto: [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- Especificación de dominio: [`docs/especificacion_sistema_relojeria.md`](docs/especificacion_sistema_relojeria.md)
- Convenciones de código: [`CONVENCIONES.md`](CONVENCIONES.md)
- Spec de esta feature: [`specs/000-bootstrap-infraestructura/`](specs/000-bootstrap-infraestructura/)

---

## Requisitos

- **Docker Desktop** en ejecución (Windows / macOS / Linux).
- Puertos del host libres:

  | Servicio  | Puerto host | Nota |
  |-----------|-------------|------|
  | PostgreSQL | `5432` | |
  | Backend (API) | `8000` | OpenAPI en `/docs` |
  | Frontend (Vite) | `5173` | |
  | MinIO API | `9000` | |
  | MinIO Consola | `9001` | |
  | pgAdmin | `5050` | solo con el perfil opcional `tools` |

---

## Arranque (un comando)

```bash
cp .env.example .env          # editar solo si hay conflicto de puertos u otros valores locales
docker compose up -d --build
```

Esto deja `db`, `backend`, `frontend` y `minio` en estado saludable sin pasos manuales adicionales. Objetivo: **< 5 minutos** en una máquina de desarrollo estándar.

Verificación rápida:

```bash
docker compose ps                       # todo "healthy" / "running"
curl -s http://localhost:8000/health    # {"status":"ok","db":"up","storage":"up","version":"0.1.0"}
```

Abrir el frontend: <http://localhost:5173> · OpenAPI navegable: <http://localhost:8000/docs>

### Perfil opcional pgAdmin

```bash
docker compose --profile tools up -d pgadmin   # http://localhost:5050
```

pgAdmin es una herramienta de visualización opcional (Constitución, "Stack"); no forma parte del stack mínimo.

### Parar / relevantar (los datos persisten)

```bash
docker compose down       # conserva los volúmenes nombrados (db, minio)
docker compose up -d      # los datos de PostgreSQL y los objetos de MinIO siguen ahí
```

`docker compose down -v` **sí** borra los volúmenes: úsalo solo para empezar de cero.

---

## Resolución de conflictos de puerto

Si un puerto del host ya está en uso, `docker compose up` falla con un mensaje explícito indicando el servicio y el puerto (`Bind for 0.0.0.0:8000 failed: port is already allocated`).

Opciones:

1. Liberar el puerto (cerrar el proceso que lo ocupa).
2. Sobrescribir el mapeo en `.env` y volver a levantar. Variables disponibles:
   `POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`, `MINIO_API_PORT`, `MINIO_CONSOLE_PORT`, `PGADMIN_PORT`.
   Ejemplo: `BACKEND_PORT=8010` → el backend queda en <http://localhost:8010> (ajusta también `VITE_API_BASE_URL`).

Si falta `.env` o está incompleto, el backend falla al arrancar con un mensaje claro de configuración (no hay crash silencioso).

---

## Migraciones (Alembic)

```bash
docker compose exec backend alembic upgrade head       # aplica la migración inicial
docker compose exec backend alembic downgrade base     # revierte (deja el esquema limpio)
```

- La migración `0001_rbac_base` crea `rol`, `modulo`, `operacion`, `permiso_modulo`, `permiso_operacion` **vacías de datos de negocio**; solo se siembra `operacion` con el enum fijo `crear / consultar / editar / eliminar`.
- Es idempotente en la práctica: un segundo `alembic upgrade head` no aplica nada.
- **Cada feature 002+ aporta su propia migración incremental** (`0002_...`, `0003_...`). No existe ni existirá un `01_operativo_postgres.sql` monolítico: el modelo operativo se construye feature a feature y cada una documenta su porción en su `data-model.md`.
- El backend, al arrancar, espera/reintenta la conexión a PostgreSQL (backoff con timeout `DB_CONNECT_TIMEOUT_SECONDS`) antes de aceptar tráfico.

---

## Buckets MinIO

Al arrancar, el job `minio-init` crea de forma idempotente cuatro buckets:

| Bucket | Acceso | Consumidores (features) |
|---|---|---|
| `reloj-imagenes` | lectura directa por la app (política `download` anónima) | 003 |
| `perfil-usuarios` | lectura directa por la app (política `download` anónima) | 001 |
| `comprobantes-venta` | privado — solo el backend con credenciales | 009 |
| `documentos` | privado — solo el backend con credenciales | 002 / 008 / 011 |

`landing-zone` **no** se crea aquí: es exclusivo de la feature 012 (ClickHouse + Airflow), que lo añade sobre este mismo MinIO.

Consola web de MinIO: <http://localhost:9001> (usuario/clave de `.env`).

---

## Respaldo de PostgreSQL

```bash
bash scripts/backup_pg.sh ./backups
```

Genera un volcado `cronos_YYYYMMDD_HHMMSS.sql.gz` en el directorio indicado (por defecto `./backups`) usando `pg_dump` dentro del contenedor `db`. La especificación (§6) exige un respaldo periódico; la automatización con cron/Airflow es tarea de operación, no de esta feature.

Restauración:

```bash
gunzip -c backups/cronos_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

---

## Estructura del repositorio

```
CRONOS_Relojeria/
├── docker-compose.yml
├── .env.example
├── README.md
├── CONVENCIONES.md
├── backend/          # FastAPI — módulos por dominio + shared/ (ver CONVENCIONES.md)
│   ├── src/
│   │   ├── main.py
│   │   ├── shared/
│   │   └── health/   # módulo plantilla (router → service → repository)
│   ├── alembic/
│   └── tests/
├── frontend/         # Vue 3 + Vite — módulos por dominio + shared/
│   ├── src/
│   │   ├── shared/
│   │   └── health/   # módulo plantilla (components / composables / services)
│   ├── scripts/
│   └── tests/
├── scripts/          # utilidades de operación (backup_pg.sh)
├── pgadmin/          # config del servicio opcional
├── specs/            # especificaciones Spec Kit (000–014)
└── docs/             # especificación de dominio
```

La organización por módulos de negocio con frontera estricta y una única carpeta `shared/` es **NON-NEGOTIABLE** (Constitución, Principio X). Añadir un módulo nuevo no debe modificar archivos de otros módulos.

---

## Tests

```bash
docker compose exec backend pytest                     # backend
docker compose run --rm frontend npm test              # frontend
```

O en local, con las dependencias instaladas:

```bash
cd backend && pip install ".[dev]" && pytest
cd frontend && npm install && npm test
```
