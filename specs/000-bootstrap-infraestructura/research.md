# Research: Bootstrap de Infraestructura

**Feature**: `000-bootstrap-infraestructura` | **Phase**: 0 | **Date**: 2026-09-09

Todas las decisiones se derivan de la constitución (`Stack y Restricciones Técnicas`, Principios III, V, IX, X, XI, XII) y de `especificacion_sistema_relojeria.md` §6, §10. No quedan `NEEDS CLARIFICATION`.

## D1 — Orquestación local

- **Decisión**: `docker-compose.yml` único con servicios `db` (postgres:16), `backend`, `frontend`, `minio`, y `pgadmin` opcional (perfil `tools`).
- **Rationale**: La constitución fija "Docker Desktop + Airflow como orquestador" y que solo 000 y 012 tocan el compose. Un solo archivo evita divergencia.
- **Alternativas**: Compose por servicio / Tilt / Dev Containers — descartadas por sobre-ingeniería (Principio VII).

## D2 — Framework y capas del backend

- **Decisión**: FastAPI + SQLAlchemy 2.x + Alembic. Capas `router → service → repository` por módulo; `shared/` para config, DB, storage, excepciones, schemas base, paginación.
- **Rationale**: Principios V y X. FastAPI da OpenAPI gratis y tipado con Pydantic.
- **Alternativas**: Flask (menos batteries), Django (renderiza HTML, viola Principio V), estructura por tipo técnico (viola Principio X).

## D3 — Migraciones

- **Decisión**: Alembic con una migración inicial `0001_rbac_base` que crea `rol`, `modulo`, `operacion`, `permiso_modulo`, `permiso_operacion`. `operacion` se siembra con Crear/Consultar/Editar/Eliminar (enum de dominio, no dato de negocio). El resto vacío.
- **Rationale**: Const. "Flujo de Trabajo" §000. Sembrar el enum de operaciones es dominio fijo, no negocio.
- **Alternativas**: SQL plano / `create_all` de SQLAlchemy — descartados por falta de historial y control de esquema incremental (cada feature aportará su migración).

## D4 — Configuración y secretos

- **Decisión**: `pydantic-settings` leyendo `.env`; `.env.example` versionado sin valores reales. Variables: `DATABASE_URL`, `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `JWT_SECRET` (placeholder para 001), `CORS_ORIGINS`.
- **Rationale**: Principio IX (Seguridad).
- **Alternativas**: variables sueltas de entorno sin validación — descartada (sin fallo temprano ante config incompleta).

## D5 — Salud y readiness

- **Decisión**: `GET /health` devuelve 200 con `{status, db: "up|down", storage: "up|down"}`; 503 si `db` o `storage` fallan. Backend reintenta la conexión a PostgreSQL al arrancar (backoff con timeout).
- **Rationale**: Const. §000; Esp. §6 (continuidad). `depends_on: condition: service_healthy` para `db` y `minio`.
- **Alternativas**: solo un ping sin dependencias — insuficiente para diagnosticar.

## D6 — MinIO y buckets

- **Decisión**: servicio `minio` + un job de init (`mc mb`) idempotente que crea `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios`, `documentos`. Política: `reloj-imagenes` y `perfil-usuarios` con lectura pública (o vía URL firmada corta); `comprobantes-venta` y `documentos` privados (solo acceso desde el backend con credenciales). `landing-zone` NO se crea.
- **Rationale**: Principio III (responsabilidad por bucket; los dos primeros se sirven directo, los dos últimos vía endpoint autenticado).
- **Alternativas**: un único bucket con prefijos — descartada; la constitución exige buckets separados.

## D7 — Frontend: stack y estructura

- **Decisión**: Vue 3 + Vite + Tailwind 3 + Pinia + Vue Router + `vue-echarts` (instalado). `shared/` con `api/client.js` (axios/fetch único), `ui/DialogHost.vue` + `dialogs.js`, `ui/AppShell.vue` (barra superior fija), `exportar.js` (stub), `tokens.css`. Módulo `health` de ejemplo.
- **Rationale**: Const. "Stack", Principios X y XI.
- **Alternativas**: Nuxt (SSR, innecesario), componentes sin capa de servicios — viola Principio X.

## D8 — Paleta y tokens (Principio XII)

- **Decisión**: `tailwind.config.js` define `primary`, `secondary`, `tertiary`, `neutral`, `danger`, `warning` como escalas 900→50 generadas a partir de los hex base del Principio XI mediante la skill `ui-ux-pro-max`. `tokens.css` expone variables CSS equivalentes. Contraste AA verificado para texto sobre `primary` y `secondary`.
- **Rationale**: Principios XI y XII (NON-NEGOTIABLE).
- **Alternativas**: hex sueltos por componente — prohibido por Principio XI.

## D9 — Respaldo (Esp. §6)

- **Decisión**: script `scripts/backup_pg.sh` documentado que ejecuta `pg_dump` a un volumen/host; instrucción en README. Sin automatización de cron en esta fase (dev).
- **Rationale**: Esp. §6 exige respaldo periódico; el detalle de scheduling es de operación, no de esta feature.
- **Alternativas**: `wal-g` / backups continuos — sobre-ingeniería para dev (Principio VII).

## D10 — Testing mínimo de la feature

- **Decisión**: `pytest` para `GET /health` (200 con deps arriba, 503 con `db` caída simulada) e idempotencia de `alembic upgrade head` / `downgrade base`; `vitest` para render del `AppShell` y montaje único de `DialogHost`. Chequeo automatizado de contraste AA (script).
- **Rationale**: Principio IX (aunque la lógica de negocio crítica llega en features posteriores, la plataforma se valida).
