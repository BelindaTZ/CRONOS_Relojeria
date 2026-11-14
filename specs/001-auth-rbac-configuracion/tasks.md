# Tasks: Autenticación, RBAC de Dos Niveles y Configuración

**Feature**: `001-auth-rbac-configuracion` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: incluidos para el guard RBAC de dos niveles (módulo crítico, Const. Ppio IX), autoservicio, restablecimiento, recálculo de parámetros y anti-lockout.

**MVP** = User Story 1 + User Story 2 (matriz + login/guard).

## Phase 1: Setup

- [x] T001 Crear módulos backend vacíos con capas: `backend/src/auth/`, `usuarios/`, `rbac/`, `sucursales/`, `configuracion/` (cada uno `router.py service.py repository.py schemas.py`)
- [x] T002 [P] Crear utilidades compartidas vacías: `backend/src/shared/guard.py`, `shared/auditoria/`, `shared/parametros/`, `shared/correo/`
- [x] T003 [P] Añadir dependencias a `backend/pyproject.toml`: `passlib[bcrypt]`, `pyjwt`, `jinja2`, SDK/adaptador de email
- [x] T004 [P] Crear módulos frontend: `frontend/src/auth/`, `perfil/`, `usuarios/`, `rbac/`, `sucursales/`, `configuracion/` (components/composables/stores/services)
- [x] T005 [P] `frontend/src/shared/stores/session.js` (Pinia) + guard de navegación por permisos en `frontend/src/router/`

## Phase 2: Foundational (bloquea todas las user stories)

- [x] T006 Migración `0002_usuario_y_sesion` en `backend/alembic/versions/` — `usuario`, `usuario_rol`, `usuario_sucursal`, `refresh_token`, `solicitud_restablecimiento` (ver `data-model.md`)
- [x] T007 Migración `0003_rbac_datos` — `permiso_usuario`; siembra `modulo` con §3.1 + `ventas`, `notificaciones`
- [x] T008 [P] Migración `0004_sucursal` — `sucursal` con `motivo_inactivacion`
- [x] T009 [P] Migración `0005_catalogos` — `medio_pago` (sembrado 4 valores), `categoria_gasto`, `canal_cita` (sembrado)
- [x] T010 [P] Migración `0006_parametros_y_auditoria` — `parametro_configuracion`, `registro_auditoria`
- [x] T011 `backend/src/shared/auditoria/service.py` — `registrar_cambio(actor, accion, entidad, entidad_id, antes, despues)` + repositorio
- [x] T012 `backend/src/shared/correo/` — interfaz `enviar(plantilla, a, contexto)`, render Jinja2 con layout de paleta (Ppio XI), adaptador de proveedor desde `.env`; plantillas base: `inactivacion_sucursal`, `password_temporal`
- [x] T013 `backend/src/shared/parametros/service.py` — `get_parametro(clave, ambito, fecha)`, `set_parametro(...)` (insert-only), `recalcular(clave)` (registro de consumidores; recorre solo entidades abiertas) + auditoría
- [x] T014 `backend/src/shared/guard.py` — `require_perm(modulo, operacion)` (dependencia FastAPI): resuelve acceso a módulo (rol + `permiso_usuario`) como prerrequisito, luego operación; 401 sin token, 403 sin permiso; caché en proceso con invalidación
- [x] T015 `backend/src/shared/guard.py` (cont.) — helpers `scope_sucursal(query, user)` y `scope_propiedad(query, user, campo)`; usuario sin sucursal ⇒ error en operaciones "propia sucursal"
- [x] T016 [P] Test `backend/tests/test_guard_rbac.py` — matriz de casos: acceso a módulo sin operación, operación sin acceso a módulo, override de usuario conceder/revocar, 401/403, frescura tras cambio de rol **(módulo crítico Const. Ppio IX)**
- [x] T017 [P] Test `backend/tests/test_endpoints_declaran_permiso.py` — prueba de contrato: todo router de negocio montado tiene `require_perm` (falla si falta)
- [x] T018 `backend/src/main.py` — registrar routers de los 5 módulos y los handlers de auditoría

## Phase 3: User Story 1 — Definir roles y la matriz de permisos (P1) 🎯 MVP

**Independent Test**: crear rol con subconjunto de módulos/operaciones, asignarlo, verificar acceso exacto.

- [x] T019 [P] [US1] `rbac/repository.py` — CRUD `rol`, lectura/escritura de `permiso_modulo` y `permiso_operacion`, catálogo `modulo`
- [x] T020 [US1] `rbac/service.py` — `set_permisos_rol(rol, matriz)`: valida que toda operación tenga acceso al módulo (422 si no), invalida caché del guard, audita
- [x] T021 [US1] `rbac/router.py` — `GET/POST /roles`, `GET/PUT /roles/{id}/permisos`, `GET /modulos` según `contracts/rbac.openapi.yaml`
- [x] T022 [P] [US1] Test `backend/tests/test_matriz_permisos.py` — operación sin acceso a módulo → 422; guardado válido refleja en el guard
- [x] T023 [P] [US1] Frontend `rbac/` — pantalla de matriz (grilla módulo × operación por rol), reactiva, con `ui-ux-pro-max`

## Phase 4: User Story 2 — Login y autorización por petición (P1) 🎯 MVP

**Independent Test**: login, llamadas con/sin permiso, token ausente/expirado.

- [x] T024 [US2] `auth/repository.py` + `auth/service.py` — verificación de credenciales (bcrypt), emisión de JWT de acceso, `refresh_token` opaco en DB (revocable)
- [x] T025 [US2] `auth/router.py` — `POST /auth/login`, `/auth/refresh`, `/auth/logout` según `contracts/auth.openapi.yaml`
- [x] T026 [P] [US2] Frontend `auth/` — pantalla de login, almacenamiento del token en el store de sesión, interceptor del `shared/api/client.js` que adjunta el bearer y maneja 401
- [x] T027 [P] [US2] Test `backend/tests/test_auth_login.py` — credenciales válidas/invalidas, refresh válido/revocado, rate-limit

## Phase 5: User Story 3 — Autoservicio del usuario (P1)

**Independent Test**: ver datos propios, editar email/foto, rechazo de cambio de rol.

- [x] T028 [P] [US3] `usuarios/repository.py` — CRUD `usuario`, `usuario_rol`, `usuario_sucursal`, `permiso_usuario`
- [x] T029 [US3] `usuarios/service.py` — `get_perfil(user)`, `update_perfil(user, {email?, foto?})` (solo esos campos; sube foto a `perfil-usuarios` vía `shared/storage`); audita
- [x] T030 [US3] `usuarios/router.py` — `GET /perfil`, `PATCH /perfil` (multipart) según `contracts/auth.openapi.yaml`; endpoints admin `GET/POST /usuarios`, `PATCH /usuarios/{id}`, `PUT /usuarios/{id}/roles|sucursales|excepciones`
- [x] T031 [US3] `usuarios/service.py` (cont.) — validación anti-lockout de Gerencia General en desactivación y cambio de roles
- [x] T032 [P] [US3] Frontend `perfil/` — "Mis datos" (lectura + edición de email/foto + cambio de contraseña)
- [x] T033 [P] [US3] Test `backend/tests/test_autoservicio.py` — email/foto editables; rol/identificación/sucursales inmutables desde `PATCH /perfil`; auditoría generada
- [x] T034 [P] [US3] Test `backend/tests/test_anti_lockout.py` — no se puede dejar 0 Gerencia General activos **(regla crítica)**

## Phase 6: User Story 4 — Cambio y restablecimiento de contraseña (P1)

**Independent Test**: solicitar reset, recibir temporal, login con temporal fuerza cambio.

- [x] T035 [US4] `auth/service.py` (cont.) — `solicitar_restablecimiento(identificacion)`: genera temporal, guarda hash + `expira_en` + `usada=false`, envía correo (`shared/correo`, plantilla `password_temporal`); respuesta 202 neutra
- [x] T036 [US4] `auth/service.py` (cont.) — login detecta temporal vigente ⇒ `must_change_password`; el token resultante solo autoriza `POST /auth/cambiar-contrasena`; `cambiar_contrasena(actual, nueva)`; temporal usada/caducada ⇒ 401
- [x] T037 [US4] `auth/router.py` (cont.) — `POST /auth/olvide-contrasena`, `POST /auth/cambiar-contrasena`
- [x] T038 [P] [US4] Frontend `auth/` — "Olvidé mi contraseña" + pantalla de cambio forzado
- [x] T039 [P] [US4] Test `backend/tests/test_reset_password.py` — un solo uso, caducidad, cambio forzado, rate-limit, respuesta neutra

## Phase 7: User Story 5 — Sucursales y catálogos (P2)

**Independent Test**: crear sucursal/categoría; inactivar con motivo y verificar avisos.

- [x] T040 [P] [US5] `sucursales/repository.py` + `service.py` — CRUD; `inactivar(id, motivo)` cambia estado, exige motivo, dispara `shared/correo` a los usuarios de `usuario_sucursal`, audita
- [x] T041 [US5] `sucursales/router.py` — `GET/POST /sucursales`, `POST /sucursales/{id}/inactivar` (422 sin motivo) según contrato
- [x] T042 [P] [US5] `configuracion/` — endpoints de catálogos `medio-pago`, `categoria-gasto`, `canal-cita` según `contracts/configuracion.openapi.yaml`
- [x] T043 [P] [US5] Frontend `sucursales/` y `configuracion/` — listados con búsqueda multi-criterio, modal de inactivación con motivo (design-system)
- [x] T044 [P] [US5] Test `backend/tests/test_inactivar_sucursal.py` — sin motivo → 422; con motivo → estado + N correos + auditoría

## Phase 8: User Story 6 — Parámetros, recálculo y auditoría (P2)

**Independent Test**: cambiar parámetro con dependencias abiertas/cerradas y verificar recálculo y auditoría.

- [x] T045 [US6] `configuracion/router.py` — `GET/PUT /parametros/{clave}`, `GET /auditoria` según contrato
- [x] T046 [US6] `shared/parametros/service.py` (cont.) — registro de consumidores (interfaz que 005/006/008/009/010 implementarán); `recalcular` invoca `recalcular_por_parametro(clave)` de cada consumidor registrado; resumen en la respuesta
- [x] T047 [P] [US6] Frontend `configuracion/` — pantalla de parámetros (valor vigente + historial + ámbito) y visor de auditoría, restringidos a Gerencia General/delegado
- [x] T048 [P] [US6] Test `backend/tests/test_parametros_recalculo.py` — insert-only con historial; `set` dispara `recalcular` (consumidor mock); documentos "emitidos" mock quedan intactos; auditoría con antes/después **(regla crítica)**
- [x] T049 [US6] `guard.py` — restricción del módulo `configuracion` a Gerencia General/delegado; mecanismo de delegación explícita

## Phase 9: User Story 7 — Scoping por sucursal y por propiedad (P3)

**Independent Test**: datos de 2 sucursales; gerente de A no ve B; técnico solo lo propio.

- [x] T050 [P] [US7] Test `backend/tests/test_scoping.py` — `scope_sucursal` y `scope_propiedad` con datos mock de 2 sucursales; Gerencia General consolidado
- [x] T051 [US7] Documentar en `CONVENCIONES.md` cómo cada endpoint de features 002+ declara su modo de scoping

## Phase 10: Polish & Cross-Cutting

- [x] T052 [P] Plantillas de correo `inactivacion_sucursal` y `password_temporal` con la identidad visual del Principio XI (revisión de diseño con `ui-ux-pro-max`)
- [x] T053 [P] Definir la política del bucket `perfil-usuarios` (URLs firmadas de corta duración) y documentarla
- [x] T054 [P] Script `scripts/seed_gerencia.py` — usuario Gerencia General inicial desde `.env` (idempotente)
- [x] T055 Ejecutar `quickstart.md` V1–V9 y registrar resultados; confirmar cobertura del guard (Const. Ppio IX)
- [x] T056 [P] Revisar `checklists/security.md`: cerrar SEC013 (retención de auditoría) y SEC014 (URLs firmadas) en implementación

## Dependencies & Execution Order

- Setup → Foundational (T006–T018) → User Stories.
- **MVP**: US1 + US2 (T019–T027) sobre Foundational.
- US3 (T028–T034) depende de US2 (login) y T014 (guard).
- US4 (T035–T039) depende de US2 y T012 (`shared/correo`).
- US5 (T040–T044) depende de T012 (correo) y T008/T009.
- US6 (T045–T049) depende de T013 (`shared/parametros`) y T011 (auditoría).
- US7 (T050–T051) depende de T015.
- Polish al final.

## Parallel Execution Examples

- Foundational: T008, T009, T010 en paralelo (migraciones independientes); T016, T017 en paralelo (tests distintos).
- US1 + US2 pueden avanzar en paralelo tras Foundational (equipos distintos): T019–T023 || T024–T027.
- Polish: T052, T053, T054, T056 en paralelo.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US2 → un usuario puede iniciar sesión y los endpoints se autorizan.
2. **Incremento 2**: US3 + US4 (autoservicio y recuperación de acceso).
3. **Incremento 3**: US5 + US6 (sucursales, catálogos, parámetros con recálculo).
4. **Incremento 4**: US7 (scoping) + Polish.
