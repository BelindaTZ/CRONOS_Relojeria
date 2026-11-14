# Tasks: Bootstrap de Infraestructura

**Feature**: `000-bootstrap-infraestructura` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/health.openapi.yaml](./contracts/health.openapi.yaml)

**Tests**: incluidos para `/health` y migraciones (plataforma verificable, Const. Ppio IX). No hay lógica de negocio crítica en esta feature.

**Organización**: por User Story (spec.md). MVP = User Story 1.

## Phase 1: Setup

- [x] T001 Crear el árbol del repositorio (`backend/`, `frontend/`, `pgadmin/`, `scripts/`) y `README.md` + `CONVENCIONES.md` (snake_case backend, camelCase frontend) en la raíz del proyecto
- [x] T002 Crear `.env.example` en la raíz con `DATABASE_URL`, `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `JWT_SECRET`, `CORS_ORIGINS` (sin valores reales) y `.gitignore` que excluya `.env`
- [x] T003 [P] Inicializar `backend/pyproject.toml` con FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, psycopg[binary], pydantic-settings, minio, pytest, httpx
- [x] T004 [P] Inicializar `frontend/package.json` con Vue 3, Vite, Vue Router, Pinia, Tailwind 3, vue-echarts, vitest, @vue/test-utils
- [x] T005 [P] `backend/Dockerfile` (imagen slim de Python 3.12, arranque Uvicorn)
- [x] T006 [P] `frontend/Dockerfile` (Node 20, `vite dev` para desarrollo)

## Phase 2: Foundational (bloquea todas las user stories)

- [x] T007 Crear `docker-compose.yml` con servicios `db` (postgres:16), `backend`, `frontend`, `minio`, y `pgadmin` bajo perfil `tools`; volúmenes nombrados para `db` y `minio`; `depends_on` con `condition: service_healthy` para `db` y `minio`
- [x] T008 Añadir al `docker-compose.yml` un job `minio-init` idempotente que cree los buckets `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios`, `documentos` y aplique la política por bucket (2 públicos, 2 privados) — NO crear `landing-zone`
- [x] T009 [P] `backend/src/shared/config.py` — `Settings` con pydantic-settings desde `.env`
- [x] T010 [P] `backend/src/shared/database.py` — engine SQLAlchemy, `SessionLocal`, `Base` declarativa, dependencia `get_db`
- [x] T011 [P] `backend/src/shared/storage.py` — cliente MinIO desde config + helpers `ensure_bucket`, `put_object`, `get_object_url`
- [x] T012 [P] `backend/src/shared/exceptions.py` — jerarquía de excepciones de dominio + handlers FastAPI (formato de error de `shared/schemas.py`)
- [x] T013 [P] `backend/src/shared/schemas.py` y `backend/src/shared/pagination.py` — modelos base `Page[T]`, `ErrorResponse`, parámetros de paginación
- [x] T014 `backend/src/main.py` — crea la app FastAPI, registra handlers de `shared/exceptions`, CORS desde config, y un registro de routers de módulos (vacío salvo `health`)
- [x] T015 Configurar Alembic: `backend/alembic.ini`, `backend/alembic/env.py` (usa `DATABASE_URL` y `Base.metadata`)
- [x] T016 Migración `backend/alembic/versions/0001_rbac_base.py` — crea `rol`, `modulo`, `operacion`, `permiso_modulo`, `permiso_operacion` (según `data-model.md`) y siembra `operacion` con crear/consultar/editar/eliminar; `downgrade` elimina las 5 tablas
- [x] T017 [P] `frontend/tailwind.config.js` + `frontend/src/shared/tokens.css` — escalas 900→50 de `primary/secondary/tertiary/neutral/danger/warning` a partir de los hex del Principio XI (skill `ui-ux-pro-max`)
- [x] T018 [P] `frontend/src/shared/api/client.js` — cliente HTTP único (base URL desde env, interceptor de error, preparado para el token de 001)
- [x] T019 [P] `frontend/src/shared/ui/DialogHost.vue` + `frontend/src/shared/ui/dialogs.js` (`confirm()`, `prompt()`)
- [x] T020 [P] `frontend/src/shared/exportar.js` — stub `opcionesExportacion()` (menú de 3 formatos, sin implementación de salida aún)
- [x] T021 `frontend/src/App.vue` (monta `<DialogHost/>` una vez) + `frontend/src/main.js` + `frontend/src/router/index.js`

## Phase 3: User Story 1 — Levantar el stack completo con un comando (P1) 🎯 MVP

**Goal**: `cp .env.example .env` + `docker compose up` deja db, backend, frontend y minio saludables sin pasos manuales.
**Independent Test**: `docker compose ps` muestra todo saludable y la app responde; parar/levantar conserva datos.

- [x] T022 [US1] Añadir healthchecks nativos a `db` y `minio` en `docker-compose.yml` y `restart: unless-stopped` a los servicios
- [x] T023 [US1] Implementar en `backend/src/main.py` el arranque con reintento/backoff a PostgreSQL (timeout configurable) antes de aceptar tráfico
- [x] T024 [P] [US1] Test `backend/tests/test_startup.py` — la app no acepta tráfico hasta que `db` responde (simulado); arranca cuando `db` está disponible
- [x] T025 [US1] Documentar en `README.md` el flujo de arranque, puertos y solución de conflicto de puertos

## Phase 4: User Story 2 — Salud del backend y shell del frontend (P2)

**Goal**: `/health` reporta estado de PostgreSQL y MinIO; el frontend muestra el shell con barra superior y la paleta.
**Independent Test**: `/health` da 200/503 según dependencias; el shell carga con contraste AA.

- [x] T026 [P] [US2] Módulo plantilla backend `backend/src/health/repository.py` — chequeos `ping_db()` y `ping_storage()`
- [x] T027 [P] [US2] `backend/src/health/service.py` — compone el estado agregado
- [x] T028 [US2] `backend/src/health/router.py` + `backend/src/health/schemas.py` — `GET /health` (200 con deps arriba, 503 si alguna falla), según `contracts/health.openapi.yaml`; registrar el router en `main.py`
- [x] T029 [P] [US2] Test `backend/tests/test_health.py` — 200 con deps arriba; 503 con `db` caída; forma del payload conforme al contrato
- [x] T030 [P] [US2] `frontend/src/shared/ui/AppShell.vue` — barra de navegación horizontal superior fija con las categorías de primer nivel (Dashboard, Ventas, Inventario, Servicio Técnico, Citas, Clientes, Proveedores, Técnicos, Sucursales, Finanzas, Sistema) sin contenido de módulo
- [x] T031 [P] [US2] Módulo plantilla frontend `frontend/src/health/` — `services/healthApi.js`, `composables/useHealth.js`, `components/HealthBadge.vue` mostrado en el shell
- [x] T032 [P] [US2] `scripts/check_contrast.mjs` — valida contraste AA (≥4.5:1) para texto sobre Primary y Secondary usando los tokens
- [x] T033 [P] [US2] Test `frontend/tests/appShell.spec.js` — renderiza la barra superior; `DialogHost` montado exactamente una vez

## Phase 5: User Story 3 — Esquema base de RBAC vacío y migraciones idempotentes (P2)

**Goal**: `alembic upgrade head` crea las 5 tablas vacías (salvo `operacion`); re-aplicar no cambia nada; `downgrade base` limpia.
**Independent Test**: inspección de tablas + doble `upgrade` sin diffs + `downgrade`/`upgrade`.

- [x] T034 [US3] Verificar en `0001_rbac_base` las restricciones únicas (`rol.nombre`, `modulo.clave`, `operacion.clave`, únicos compuestos de permisos) y las FKs
- [x] T035 [P] [US3] Test `backend/tests/test_migrations.py` — tras `upgrade head`: existen las 5 tablas, `operacion` = 4 filas, resto = 0; segundo `upgrade head` no aplica migraciones; `downgrade base` elimina las tablas
- [x] T036 [US3] Documentar en `README.md` que cada feature 002+ aporta su propia migración (sin SQL monolítico)

## Phase 6: User Story 4 — Estructura modular impuesta (P3)

**Goal**: `shared/` + módulo plantilla en backend y frontend; añadir un módulo no toca otros.
**Independent Test**: diff tras añadir un módulo dummy → solo su carpeta + registro de rutas.

- [x] T037 [P] [US4] Añadir a `CONVENCIONES.md` la regla de modularidad (Const. Ppio X): módulos de negocio con frontera, `shared/` único, prohibición de imports cruzados de internos
- [x] T038 [P] [US4] Añadir `scripts/check_module_boundaries.mjs` (o linter config) que detecte imports de un módulo hacia los internos de otro
- [x] T039 [P] [US4] Test `backend/tests/test_module_boundaries.py` y `frontend/tests/moduleBoundaries.spec.js` — un módulo dummy solo altera su carpeta

## Phase 7: User Story 5 — MinIO con los buckets de cara a la app (P3)

**Goal**: los 4 buckets existen con su política; `landing-zone` no.
**Independent Test**: `mc ls`, subir/recuperar objeto, acceso anónimo denegado a privados.

- [x] T040 [US5] Verificar en `minio-init` la idempotencia (re-arranque no falla) y la política: `reloj-imagenes`/`perfil-usuarios` legibles por la app, `comprobantes-venta`/`documentos` privados
- [x] T041 [P] [US5] Test `backend/tests/test_storage.py` — `shared/storage` sube y recupera un objeto de prueba en cada bucket; el acceso sin credenciales a un bucket privado falla; `landing-zone` no existe

## Phase 8: Polish & Cross-Cutting

- [x] T042 [P] `scripts/backup_pg.sh` — `pg_dump` con marca de tiempo a un directorio de salida; documentado en `README.md` (Esp. §6)
- [x] T043 [P] Servicio `pgadmin` bajo perfil `tools` en `docker-compose.yml` documentado como opcional
- [x] T044 [P] Revisión estática: 0 secretos hardcodeados (grep en `backend/`, `frontend/`, `docker-compose.yml`)
- [x] T045 CI local: `docker compose config` valida; `pytest` y `vitest` verdes; ejecutar `quickstart.md` V1–V8 y registrar resultados
- [x] T046 [P] Verificar que el backend expone OpenAPI navegable en `/docs` y `/openapi.json`

## Dependencies & Execution Order

- **Setup (T001–T006)** → **Foundational (T007–T021)** → User Stories.
- US1 (T022–T025) es el MVP y solo depende de Foundational.
- US2 (T026–T033) depende de Foundational (T014 registro de routers, T017 tokens).
- US3 (T034–T036) depende de T015–T016.
- US4 (T037–T039) depende de la estructura de Foundational.
- US5 (T040–T041) depende de T008 y T011.
- Polish (T042–T046) al final.

## Parallel Execution Examples

- Foundational: `T009`, `T010`, `T011`, `T012`, `T013` en paralelo (archivos distintos en `shared/`); `T017`–`T020` en paralelo (frontend `shared/`).
- US2: `T026`+`T027` (backend health) en paralelo con `T030`+`T031`+`T032` (frontend shell).
- Polish: `T042`, `T043`, `T044`, `T046` en paralelo.

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 → stack levantable y saludable.
2. **Incremento 2**: US2 (salud observable + shell visual).
3. **Incremento 3**: US3 (esquema RBAC listo para 001).
4. **Incremento 4**: US4 + US5 (garantías de modularidad y almacenamiento).
5. **Cierre**: Polish + ejecución completa de `quickstart.md`.
