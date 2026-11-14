# Implementation Plan: Bootstrap de Infraestructura

**Branch**: `000-bootstrap-infraestructura` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/000-bootstrap-infraestructura/spec.md`

## Summary

Levantar el sustrato ejecutable de CRONOS: un `docker-compose.yml` con PostgreSQL 16, backend FastAPI (esqueleto con `/health`), frontend Vue 3 + Vite + Tailwind (paleta del Principio XI) y MinIO con los buckets `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios` y `documentos`. Alembic con la migración inicial que crea las tablas base de RBAC (`rol`, `modulo`, `operacion`, `permiso_modulo`, `permiso_operacion`) **vacías de datos de negocio**. Estructura modular estricta (Principio X) en `backend/src/` y `frontend/src/` con carpeta `shared/`, helpers compartidos de diálogos y exportación, y shell de navegación horizontal superior. Sin ClickHouse/Airflow/`landing-zone` (feature 012) y sin lógica de negocio.

## Technical Context

**Language/Version**: Python 3.12 (backend), Node 20 / Vue 3.4 (frontend), SQL (PostgreSQL 16)

**Primary Dependencies**: FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, `psycopg[binary]`, `pydantic-settings`, `minio` (SDK); Vite, Vue Router, Pinia, Tailwind CSS 3, `vue-echarts` (instalado, sin uso aún)

**Storage**: PostgreSQL 16 (operativo); MinIO (objetos). Sin ClickHouse en esta feature.

**Testing**: `pytest` + `httpx` (backend), `vitest` + Vue Test Utils (frontend)

**Target Platform**: Docker Desktop en Windows/macOS/Linux de desarrollo; entorno local monositio

**Project Type**: Web (backend API REST/JSON + frontend SPA) — Estructura "Option 2"

**Performance Goals**: `docker compose up` a estado saludable < 5 min; `GET /health` < 200 ms; objetivo heredado para features: CRUD < 1 s en desarrollo

**Constraints**: sin secretos hardcodeados (solo `.env`); backend no renderiza HTML; migraciones idempotentes; sin servicios fuera de los 4 (PostgreSQL, backend, frontend, MinIO) + pgAdmin opcional

**Scale/Scope**: 1–2 sucursales, ~decenas de usuarios, ~cientos de relojes/piezas; esta feature no maneja volumen de negocio, solo la plataforma

## Constitution Check

*GATE: Debe pasar antes de Phase 0. Re-evaluado tras Phase 1.*

| Principio | Cumplimiento en esta feature |
|---|---|
| I. Trazabilidad | La feature habilita §4.1–§4.12; cada FR cita Const./§6/§3.1. ✅ |
| II. Nivel operativo = registro real | No aplica (sin operaciones de negocio); no se introducen "estados" sin persistencia. ✅ |
| III. Separación de motores | PostgreSQL OLTP; MinIO 4 buckets con responsabilidad separada; sin ClickHouse. ✅ |
| IV. RBAC dos niveles | Se crean las tablas del esquema (rol→módulo, rol→módulo→operación) vacías; el guard y la carga son 001. ✅ |
| V. Back/Front desacoplados | Backend solo REST/JSON + OpenAPI; frontend única capa de UI; capa de servicios API centralizada. ✅ |
| VI. Features autocontenidas | El spec referencia constitución y especificación; no las redefine. ✅ |
| VII. Simplicidad | Solo 4 servicios + pgAdmin opcional; sin dependencias no justificadas. ✅ |
| VIII. Guardrails IA | No se borran specs; documentos generados de corrido tras aprobación. ✅ |
| IX. Calidad/Seguridad | `.env` para secretos; `/health`; objetivo de rendimiento fijado; tests de arranque y migración. ✅ |
| X. Convenciones/Modularidad | Estructura `backend/src/<modulo>/` + `shared/`; `frontend/src/<modulo>/` + `shared/`; módulo plantilla. ✅ |
| XI. Usabilidad/Diseño | Shell con barra superior fija; helpers `dialogs.js`/`exportar.js`; paleta en Tailwind. ✅ |
| XII. Skill de diseño | Tokens/config Tailwind producidos con `ui-ux-pro-max` como base compartida. ✅ |

**Resultado**: PASS. Sin violaciones. Complexity Tracking vacío.

## Project Structure

### Documentation (this feature)

```text
specs/000-bootstrap-infraestructura/
├── spec.md
├── plan.md              # Este archivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── health.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
docker-compose.yml
.env.example
README.md
CONVENCIONES.md

backend/
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_rbac_base.py
└── src/
    ├── main.py                 # crea la app FastAPI, monta routers de módulos
    ├── shared/
    │   ├── config.py           # pydantic-settings desde .env
    │   ├── database.py         # engine, sesión, Base declarativa
    │   ├── storage.py          # cliente MinIO + helpers de bucket
    │   ├── exceptions.py       # excepciones de dominio + handlers
    │   ├── schemas.py          # schemas base (paginación, error)
    │   └── pagination.py
    └── health/                 # MÓDULO PLANTILLA (router → service → repository)
        ├── router.py
        ├── service.py
        ├── repository.py
        └── schemas.py

frontend/
├── Dockerfile
├── package.json
├── vite.config.js
├── tailwind.config.js          # paleta Principio XI (escalas 900→50)
├── postcss.config.js
├── index.html
└── src/
    ├── main.js
    ├── App.vue                 # monta <DialogHost/> una vez
    ├── router/index.js
    ├── shared/
    │   ├── api/client.js       # cliente HTTP único (base URL, interceptores)
    │   ├── ui/
    │   │   ├── DialogHost.vue
    │   │   └── dialogs.js      # confirm() / prompt()
    │   ├── ui/AppShell.vue     # barra de navegación horizontal superior fija
    │   ├── exportar.js         # opcionesExportacion() (stub)
    │   └── tokens.css          # variables de la paleta
    └── health/                 # MÓDULO PLANTILLA frontend
        ├── components/HealthBadge.vue
        ├── composables/useHealth.js
        └── services/healthApi.js

pgadmin/ (opcional, solo servicio en compose)
```

**Structure Decision**: Web app (Option 2). Backend y frontend son proyectos separados y desacoplados (Principio V), cada uno organizado por módulos de negocio con `shared/` para lo reutilizable (Principio X). El módulo `health` sirve de plantilla canónica que las features 001+ replican.

## Complexity Tracking

*Sin violaciones de la Constitution Check. No aplica.*
