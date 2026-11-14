# Tasks: Gestión de Citas

**Feature**: `007-citas` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/citas.openapi.yaml](./contracts/citas.openapi.yaml)

**Tests**: incluidos para ciclo de estados, vínculo a transacción, agenda y scope por sucursal.

**MVP** = User Story 1 + User Story 2 + User Story 3.

## Phase 1: Setup

- [X] T001 Crear módulo `backend/src/citas/` (capas) y `frontend/src/citas/`
- [X] T002 [P] Declarar módulo `citas` en el catálogo RBAC (Vendedor: crear/consultar/editar, no eliminar)

## Phase 2: Foundational

- [X] T003 Migración `0012_citas` — `cita`, `historial_estado_cita`
- [X] T004 [P] `citas/repository.py` + `citas/schemas.py`
- [X] T005 `citas/service.py` — máquina de estados con guardas (`pendiente`/`confirmada`/`cancelada`/`atendida`)
- [X] T006 `citas/router.py` — esqueleto con `require_perm("citas", <op>)` y `scope_sucursal`

## Phase 3: User Story 1 — Registrar una cita (P1) 🎯 MVP

- [X] T007 [US1] `citas/service.py` — `crear_cita` (valida `cliente_id` existe, `canal_cita_id` del catálogo)
- [X] T008 [US1] `citas/router.py` — `GET/POST /citas` con filtros reactivos y paginación
- [X] T009 [P] [US1] Frontend `citas/` — `PanelCita` (selectores de cliente/canal/motivo, sin texto libre) y `ListaCitas`
- [X] T010 [P] [US1] Test `backend/tests/test_crear_cita.py` — cliente inexistente → 422; canal fuera de catálogo → 422

## Phase 4: User Story 2 — Confirmar, cancelar, atender (P1) 🎯 MVP

- [X] T011 [US2] `citas/service.py` — `confirmar` (fija `fecha_confirmada`, advertencia de solape); `cancelar` (exige motivo, no sobre atendida); `historial_estado_cita`
- [X] T012 [US2] `citas/router.py` — `POST /citas/{id}/confirmar`, `POST /citas/{id}/cancelar`
- [X] T013 [P] [US2] Frontend `citas/` — panel de trabajo con "Confirmar"/"Cancelar", modal de motivo (design-system)
- [X] T014 [P] [US2] Test `backend/tests/test_ciclo_cita.py` — transiciones válidas/invalidas; cancelar atendida → 409; advertencia de solape sin bloqueo

## Phase 5: User Story 3 — Agenda del día y de la semana (P1) 🎯 MVP

- [X] T015 [US3] `citas/service.py` — `agenda(rango, fecha, sucursal)` ordenada por hora (confirmada o preferida)
- [X] T016 [US3] `citas/router.py` — `GET /agenda`
- [X] T017 [P] [US3] Frontend `citas/` — `AgendaDia` y `AgendaSemana`
- [X] T018 [P] [US3] Test `backend/tests/test_agenda.py` — solo sucursal del usuario; Gerencia General con `sucursal_id`; orden por hora

## Phase 6: User Story 4 — Vincular la cita atendida (P2)

- [X] T019 [US4] `citas/service.py` — `atender(cita, venta_id?, orden_trabajo_id?)`: vincula si existe; si no, devuelve `accion` (`crear_venta`/`crear_ot`) con contexto
- [X] T020 [US4] `citas/router.py` — `POST /citas/{id}/atender`
- [X] T021 [US4] Exponer un endpoint interno para que 008 y 009 vinculen la cita al confirmar su transacción (`PUT /_internal/citas/{id}/vincular`)
- [X] T022 [P] [US4] Frontend `citas/` — acción "Atender" que navega al flujo de 008/009 con `cliente_id` y `cita_id`
- [X] T023 [P] [US4] Test `backend/tests/test_atender_cita.py` — sin transacción → `accion` con contexto; con `orden_trabajo_id` → vínculo directo

## Phase 7: Polish & Cross-Cutting

- [X] T024 [P] `citas/router.py` — `GET /citas/conversion` (versión operativa)
- [X] T025 [P] `citas/router.py` — `GET /_internal/citas/confirmadas-pendientes-recordatorio` (para 014)
- [X] T026 [P] Exportación CSV/Excel/PDF de la agenda (`shared/exportar.js`)
- [X] T027 Ejecutar `quickstart.md` V1–V7 y registrar resultados

## Dependencies & Execution Order

- Setup → Foundational (T003–T006) → US1 + US2 + US3 (MVP) → US4 → Polish.
- US4 (T021) lo consumen 008 y 009; T025 lo consume 014.

## Parallel Execution Examples

- MVP: US1 (T007–T010) → US2 (T011–T014) → US3 (T015–T018); frontends T009, T013, T017 en paralelo con sus servicios.
- Polish: T024, T025, T026 en paralelo.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US2 + US3 → citas y agenda operativas.
2. **Incremento 2**: US4 (vínculo a transacción con contexto).
3. **Cierre**: Polish (conversión, datos para 014, exportación).

---

## Notas de implementación (2026-09-10)

- **Migración renumerada**: `0012_citas` → **`0019_citas`** (0012+ ya usados). Encadenada tras `0018`.
- `cita.venta_id` / `cita.orden_trabajo_id` son `BigInteger` sin FK (las tablas de 009/008 aún no existen); 008/009 podrán añadir la FK o solo usar el vínculo.
- **Scope por sucursal**: se reutiliza `inventario.sucursales_visibles(user, None)` (helper único de 003/004) — Gerencia = todo, otros = sus sucursales.
- **Búsqueda por cliente** en `/citas`: `q` se resuelve vía `clientes.ids_por_texto(db, q)` (helper público nuevo de 006) → `cliente_ids`, sin acoplar `citas` a la tabla `cliente`.
- **`atender`**: si el motivo es `consulta` no se genera `accion`. `servicio_tecnico` → `crear_ot`, `compra` → `crear_venta`. Como 008/009 no existen, el frontend marca la cita atendida y avisa que el flujo se abrirá cuando estén disponibles; 008/009 vincularán vía `citas.vincular_transaccion(...)` o `PUT /_internal/citas/{id}/vincular`.
- **Parámetro nuevo** (`0019`): `citas_ventana_solape_min = 30` (tolerancia de la advertencia de solape, editable en Sistema · Parámetros).
- `historial_estado_cita` es append-only (trigger DB).
- Frontend: categoría de navegación **"Citas"** (Citas / Agenda). `AtenderModal` con radio "ya existe / se creará después". `AgendaView` con toggle día/semana + conversión operativa. Búsqueda de cliente en la lista.
- Tests: `test_cita_ciclo.py` (7) + `test_cita_agenda.py` (4) — backend **164 pasan**.

## Corrección (2026-09-10, feedback del usuario)

- [X] **Bug de alcance en la agenda**: `repository.agenda` aplicaba `sucursal_id` con `elif`, saltándose el filtro de sucursales del usuario. Corregido: el alcance por sucursal SIEMPRE se aplica; `sucursal_id` solo acota más (un no-Gerencia que pida otra sucursal ve 0 citas). Test `test_agenda_del_dia_ordenada_y_con_scope` ampliado.
- [X] **Etiqueta del filtro de sucursal**: "Mi sucursal" solo para no-Gerencia; para Gerencia General ahora dice "Todas las sucursales" (`session.esGerencia`).
- [X] **Acciones en la agenda**: se añadieron "Confirmar" / "Atender" / "Cancelar" por fila + leyenda que aclara **Confirmar** (agendar en firme, antes de la cita) vs **Atender** (el cliente llegó y fue atendido). Etiquetas equivalentes en el listado.
