# Tasks: Proveedores y Órdenes de Compra

**Feature**: `002-proveedores` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/proveedores.openapi.yaml](./contracts/proveedores.openapi.yaml)

**Tests**: incluidos para cumplimiento de plazos, generación de compras programadas y correcciones auditadas.

**MVP** = User Story 1 + User Story 2.

## Phase 1: Setup

- [x] T001 Crear módulo `backend/src/proveedores/` (`router.py service.py repository.py schemas.py scheduler.py`) y `frontend/src/proveedores/` (components/composables/stores/services)
- [x] T002 [P] Añadir `APScheduler` a `backend/pyproject.toml`
- [x] T003 [P] Declarar el módulo `proveedores` en el catálogo de `modulo` (migración de datos) si no está sembrado por 001

## Phase 2: Foundational

- [x] T004 Migración `0007_proveedores` — `proveedor`, `proveedor_tipo`, `proveedor_documento`, `calificacion_proveedor`, `orden_compra`, `linea_orden_compra`, `recepcion_compra`, `recepcion_linea`, `compra_programada` (ver `data-model.md`)
- [x] T005 [P] `proveedores/repository.py` — accesos a todas las tablas + búsqueda multi-criterio paginada
- [x] T006 [P] `proveedores/schemas.py` — Pydantic para request/response conforme al contrato
- [x] T007 `proveedores/router.py` — esqueleto de rutas con `require_perm("proveedores", <op>)` en cada una

## Phase 3: User Story 1 — Mantener la ficha de proveedor (P1) 🎯 MVP

- [x] T008 [P] [US1] `proveedores/service.py` — crear/editar proveedor; `razon_social`/`ruc_nit` requieren rol elevado; auditoría en toda edición
- [x] T009 [US1] `proveedores/router.py` — `GET/POST /proveedores`, `GET/PATCH /proveedores/{id}`, `POST /proveedores/{id}/inactivar`
- [x] T010 [P] [US1] `proveedores/service.py` (cont.) — subida de documentos al bucket `documentos` (`shared/storage`), recuperación con URL firmada
- [x] T011 [US1] `proveedores/router.py` (cont.) — `POST /proveedores/{id}/documentos`
- [x] T012 [P] [US1] Frontend `proveedores/` — `ListaProveedores` (búsqueda multi-criterio reactiva) y `FichaProveedor` con `ui-ux-pro-max`
- [x] T013 [P] [US1] Test `backend/tests/test_proveedor_crud.py` — RUC duplicado → 409; edición de `ruc_nit` con rol no elevado → 403; toda edición audita; inactivar en vez de borrar

## Phase 4: User Story 2 — Órdenes de compra y recepción (P1) 🎯 MVP

- [x] T014 [P] [US2] `proveedores/service.py` (cont.) — crear orden (borrador), emitir, cancelar; transiciones de estado
- [x] T015 [US2] `proveedores/service.py` (cont.) — `registrar_recepcion`: recepción parcial/total, `sobre_entrega`, `desfase_dias`, propagación a 003 (crear unidades/stock + `lote_pieza` si perecedero)
- [x] T016 [US2] `proveedores/router.py` (cont.) — `GET/POST /ordenes-compra`, `POST /ordenes-compra/{id}/emitir`, `POST /ordenes-compra/{id}/recepciones`
- [x] T017 [P] [US2] Frontend `proveedores/` — `PanelOrdenCompra` + `Recepcion` (líneas, lote/caducidad condicional)
- [x] T018 [P] [US2] Test `backend/tests/test_orden_compra.py` — parcial→recibida; recepción de perecedero sin lote → 422; historial de compras refleja órdenes+recepciones
- [x] T019 [US2] `proveedores/service.py` (cont.) — construir el historial de compras del proveedor

## Phase 5: User Story 3 — Calificación de confiabilidad (P2)

- [x] T020 [P] [US3] `proveedores/service.py` (cont.) — registrar calificación (`nota_calidad`, `nota_soporte` manuales), calcular `nota_agregada`, historial por inserción
- [x] T021 [US3] `proveedores/router.py` (cont.) — `POST /proveedores/{id}/calificaciones`
- [x] T022 [P] [US3] Frontend — panel de calificación en `FichaProveedor` con historial

## Phase 6: User Story 4 — Cumplimiento de plazos automático (P2)

- [x] T023 [US4] `proveedores/service.py` (cont.) — al registrar cada recepción, recalcular `indicador_plazos_dias` (promedio de últimas N) y derivar `nota_plazos` por tramos
- [x] T024 [P] [US4] Test `backend/tests/test_cumplimiento_plazos.py` — a tiempo / +2 / +5 días → indicador y `nota_plazos` esperados; `nota_calidad`/`nota_soporte` intactas **(módulo con cálculo)**
- [x] T025 [P] [US4] Frontend — mostrar el indicador de cumplimiento en la ficha

## Phase 7: User Story 5 — Compras programadas y especiales (P2)

- [x] T026 [P] [US5] `proveedores/service.py` (cont.) — CRUD `compra_programada`; cálculo de `proxima_generacion` por `frecuencia`
- [x] T027 [US5] `proveedores/scheduler.py` — job horario que genera órdenes `borrador` de las programadas vencidas y avanza `proxima_generacion`; endpoint interno `POST /_internal/scheduler/tick` para pruebas
- [x] T028 [US5] `proveedores/router.py` (cont.) — `GET/POST /compras-programadas`, `PUT /compras-programadas/{id}/estado`
- [x] T029 [P] [US5] Frontend — `CompraProgramada` (crear, pausar, cancelar)
- [x] T030 [P] [US5] Test `backend/tests/test_compras_programadas.py` — activa+vencida → genera 1 borrador y avanza fecha; pausada → no genera; puntual no genera recurrencia **(módulo con lógica)**

## Phase 8: User Story 6 — Corrección de datos y baja (P2)

- [x] T031 [US6] `proveedores/service.py` (cont.) — `corregir_orden(id, cambios, motivo)`: exige rol elevado + motivo, aplica sobre orden `recibida`, audita antes/después
- [x] T032 [US6] `proveedores/router.py` (cont.) — `PATCH /ordenes-compra/{id}`
- [x] T033 [P] [US6] Test `backend/tests/test_correccion_compra.py` — 403 rol normal; 200 + auditoría rol elevado
- [x] T034 [P] [US6] Frontend — acción "Corregir" (rol elevado) con modal de motivo

## Phase 9: User Story 7 — Reponer stock desde una alerta (P3)

- [x] T035 [US7] `proveedores/service.py` (cont.) — `prellenar_orden(params)`: resuelve proveedor habitual del ítem, devuelve borrador
- [x] T036 [US7] `proveedores/router.py` (cont.) — `POST /ordenes-compra/prellenar`
- [x] T037 [P] [US7] Test `backend/tests/test_prellenar_orden.py` — devuelve borrador con proveedor/ítem/cantidad; ítem sin proveedor habitual → pide elegir

## Phase 10: Polish & Cross-Cutting

- [x] T038 [P] Exportación CSV/Excel/PDF del historial de compras (`shared/exportar.js`)
- [x] T039 [P] Registrar en `shared/parametros` los consumidores de esta feature (N de recepciones para el indicador)
- [x] T040 Ejecutar `quickstart.md` V1–V7 y registrar resultados
- [x] T041 [P] Revisar `checklists/requirements.md` (cerrar CHK028)

## Dependencies & Execution Order

- Setup → Foundational (T004–T007) → US1 + US2 (MVP) → US3/US4 → US5/US6/US7 → Polish.
- US4 depende de US2 (recepciones). US7 lo consume 003.

## Parallel Execution Examples

- Foundational: T005, T006 en paralelo.
- US1 || US2 tras Foundational (T008–T013 || T014–T019).
- Tests T013, T018, T024, T030, T033, T037 en paralelo con sus servicios respectivos.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US2 → proveedores y compras con recepción.
2. **Incremento 2**: US3 + US4 (calificación con retroalimentación automática).
3. **Incremento 3**: US5 (programadas), US6 (correcciones), US7 (prellenado).
4. **Cierre**: Polish + quickstart.
