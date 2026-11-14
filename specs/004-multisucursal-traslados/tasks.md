# Tasks: Multi-Sucursal y Traslados de Inventario

**Feature**: `004-multisucursal-traslados` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/traslados.openapi.yaml](./contracts/traslados.openapi.yaml)

**Tests**: incluidos para integridad de stock en ambas sucursales, no-operabilidad en tránsito y cancelación reversible.

**MVP** = User Story 1 + User Story 2.

## Phase 1: Setup

- [X] T001 Crear módulo `backend/src/traslados/` (capas) y `frontend/src/traslados/`
- [X] T002 [P] Declarar módulo `multisucursal` en el catálogo RBAC

## Phase 2: Foundational

- [X] T003 Migración `0009_traslados` — `transferencia`, `linea_transferencia`, `discrepancia_transferencia`
- [X] T004 [P] `traslados/repository.py` + `traslados/schemas.py`
- [X] T005 `traslados/service.py` — máquina de estados (`en_preparacion`/`en_transito`/`recibida`/`parcial`/`cancelada`) con guardas de transición
- [X] T006 `traslados/router.py` — esqueleto de rutas con `require_perm("multisucursal", <op>)` y `scope_sucursal`

## Phase 3: User Story 1 — Enviar una transferencia (P1) 🎯 MVP

- [X] T007 [US1] `traslados/service.py` — `crear_transferencia` (valida origen≠destino, ítems disponibles, ≥1 sucursal destino)
- [X] T008 [US1] `traslados/service.py` — `enviar`: relojes → `en_transito`; piezas → `movimiento_stock_pieza(transferencia_salida)`; fecha y responsable; auditoría
- [X] T009 [US1] `traslados/router.py` — `POST /transferencias`, `POST /transferencias/{id}/enviar`
- [X] T010 [P] [US1] Frontend `traslados/` — `PanelTransferencia` (crear + enviar) con selección de ítems (sin texto libre)
- [X] T011 [P] [US1] Test `backend/tests/test_enviar_transferencia.py` — origen==destino → 422; tras enviar, reloj `en_transito` y no disponible en origen; stock de pieza descontado de origen

## Phase 4: User Story 2 — Recibir la transferencia (P1) 🎯 MVP

- [X] T012 [US2] `traslados/service.py` — `recibir` (lock de la transferencia): relojes → destino + `evento_serie(transferencia)`; piezas → `movimiento_stock_pieza(transferencia_entrada)` en destino; estado `recibida`/`parcial`
- [X] T013 [US2] `traslados/service.py` — al faltar cantidad: crear `discrepancia_transferencia` + exponer `accion_merma` (011)
- [X] T014 [US2] `traslados/router.py` — `POST /transferencias/{id}/recibir`, `GET /transferencias/{id}/discrepancias`
- [X] T015 [P] [US2] Frontend `traslados/` — `RecepcionTransferencia` (líneas, cantidad recibida, aviso de discrepancia)
- [X] T016 [P] [US2] Test `backend/tests/test_recibir_transferencia.py` — recepción completa mueve stock en ambas sucursales; recepción con faltante → `parcial` + discrepancia; doble confirmación concurrente idempotente
- [X] T017 [P] [US2] Test `backend/tests/test_transito_no_operable.py` — 009 y 008 rechazan un reloj `en_transito` (stubs si aún no existen)

## Phase 5: User Story 3 — Visibilidad por sucursal (P2)

- [X] T018 [US3] Aplicar `scope_sucursal` a `GET /transferencias` y verificar su aplicación en `GET /relojes`, `GET /piezas`, `GET /valor-inventario` (003)
- [X] T019 [P] [US3] Frontend — selector de sucursal en listados de inventario para Gerencia General; oculto para gerente de sucursal
- [X] T020 [P] [US3] Test `backend/tests/test_scoping_inventario.py` — gerente de A no ve inventario de B en ningún listado; Gerencia General ve consolidado

## Phase 6: User Story 4 — Cancelar una transferencia en tránsito (P3)

- [X] T021 [US4] `traslados/service.py` — `cancelar` (solo `en_preparacion`/`en_transito`): revierte ítems a `disponible` en origen; auditoría
- [X] T022 [US4] `traslados/router.py` — `POST /transferencias/{id}/cancelar`
- [X] T023 [P] [US4] Test `backend/tests/test_cancelar_transferencia.py` — ítems vuelven al 100% a origen; estado no cancelable → 409

## Phase 7: Polish & Cross-Cutting

- [X] T024 [P] Historial de transferencias: `GET /transferencias` con filtros (sucursal, estado, número de serie) reactivos y paginación
- [X] T025 [P] Exportación CSV/Excel/PDF del historial (`shared/exportar.js`)
- [X] T026 [P] Frontend `ListaTransferencias` con panel de trabajo estandarizado ("Confirmar recepción", "Cancelar transferencia")
- [X] T027 Ejecutar `quickstart.md` V1–V8 y registrar resultados

## Dependencies & Execution Order

- Setup → Foundational (T003–T006) → US1 → US2 (MVP) → US3 → US4 → Polish.
- US2 depende de US1. T017 usa stubs de 008/009 si aún no existen.

## Parallel Execution Examples

- Foundational: T004 en paralelo con el diseño de T005.
- US1: T010 (frontend) || T007–T009 (backend); test T011 en paralelo.
- US2: T015 || T012–T014; tests T016, T017 en paralelo.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US2 → transferencias completas con inventario consistente.
2. **Incremento 2**: US3 (visibilidad por sucursal).
3. **Incremento 3**: US4 (cancelación) + Polish (historial, exportación).

## Notas de implementación (2026-09-10)

- **Migración**: es `0010_traslados` (0009 lo tomó Inventario). Módulo `multisucursal` ya sembrado en `0003`; la clave RBAC es `multisucursal` y el directorio de código `backend/src/traslados/`.
- **Efecto en inventario** (todo en la misma transacción, vía API pública de 003):
  - enviar → `inventario.marcar_reloj_en_transito` + `piezas.mover_stock_traslado(transferencia_salida)`; el reloj `en_transito` sale del conteo de modelo (dispara alerta de reposición en origen) y de los listados `disponible`.
  - recibir → `inventario.recibir_reloj_transferido` (sucursal destino + `evento_serie(transferencia)`) + `piezas.mover_stock_traslado(transferencia_entrada)` en destino. Faltante ⇒ `discrepancia_transferencia` con `accion_merma` (causa `dano_transito`, para 011).
  - cancelar → `inventario.revertir_reloj_transferencia` + movimiento compensatorio `transferencia_entrada` de la pieza en el origen.
- **Idempotencia**: `recibir` toma `SELECT … FOR UPDATE` sobre la transferencia; una segunda confirmación ve `recibida` y devuelve 409.
- **Scoping por sucursal (FR-008)**: `inventario.sucursales_visibles(user, sucursal_id)` — Gerencia General ve el consolidado (o filtra por `sucursal_id`); el resto solo sus `sucursal_ids`. Aplicado a `GET /relojes`, `/valor-inventario`, `/piezas`, `/piezas/lotes`, `/piezas/valor` y `GET /transferencias`. Nota: las rutas de inventario/traslados del frontend siguen gated por `soloGerencia` hasta que exista el RBAC por módulo en el frontend; el backend ya soporta el rol "Gerente de Sucursal".
- **Merma (011)** aún no existe: el botón "Registrar merma" de las discrepancias queda deshabilitado con tooltip, igual que en Lotes/Caducidad.
- **Nav**: reagrupada en menús desplegables (Abastecimiento / Inventario / Sistema) al superar las ~9 entradas — cumple el Principio XI (mega-menú para 4+ sub-opciones).
- **Verificación**: `docker compose exec backend pytest` → 103 passed (8 nuevos: `test_traslados.py`, `test_scoping_inventario.py` — origen==destino 422, envío pone reloj en tránsito y descuenta pieza, recepción completa mueve inventario en ambas, parcial → discrepancia, doble recepción 409, cancelar devuelve 100% a origen, scoping por sucursal). Frontend 8 + build + boundaries + contraste OK. Quickstart V1–V8 cubiertos.
