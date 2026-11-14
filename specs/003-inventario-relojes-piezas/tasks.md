# Tasks: Inventario de Relojes y Piezas

**Feature**: `003-inventario-relojes-piezas` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: incluidos para stock no negativo (concurrencia), alertas, inmutabilidad del historial y perecederos.

**MVP** = User Story 1 + User Story 2 + User Story 3.

## Phase 1: Setup

- [X] T001 Crear módulos `backend/src/inventario/`, `backend/src/piezas/` (capas) y `frontend/src/inventario/`, `frontend/src/piezas/`
- [X] T002 [P] Declarar módulos `inventario_relojes` y `piezas` y el permiso granular `ver_costos` en el catálogo RBAC (migración de datos)

## Phase 2: Foundational

- [X] T003 Migración `0008_inventario` — todas las tablas de `data-model.md` (calibre, reloj, foto_reloj, documento_reloj, evento_serie, pieza, pieza_calibre, stock_pieza, movimiento_stock_pieza, lote_pieza, alerta_stock)
- [X] T004 [P] Migración de datos — parámetros `stock_maximo_modelo=12`, `umbral_reposicion_relojes`, `umbral_reposicion_piezas`, `umbral_caducidad_dias=30`
- [X] T005 [P] `inventario/repository.py` y `piezas/repository.py` — accesos + búsqueda multi-criterio paginada
- [X] T006 `piezas/service.py` — helper transaccional `aplicar_movimiento` con `SELECT ... FOR UPDATE` sobre `stock_pieza`; aborta si `stock_actual` quedaría < 0
- [X] T007 `inventario/service.py` — helper `registrar_evento_serie(serie, tipo, doc, detalle)` (append-only)
- [X] T008 `inventario/service.py` + `piezas/service.py` — `recalcular_alertas(sucursal, ambito)` tras cada movimiento
- [X] T009 Serializador condicional de `costo_adquisicion` según permiso `ver_costos` (en `shared` o en cada módulo)

## Phase 3: User Story 1 — Alta de una unidad de reloj (P1) 🎯 MVP

- [X] T010 [P] [US1] `inventario/service.py` — crear unidad (validar `numero_serie` único), vincular a `recepcion_linea` (002), `evento_serie(ingreso)`
- [X] T011 [US1] `inventario/service.py` — subir foto(s) a `reloj-imagenes` vía `shared/storage` (valida tipo/tamaño)
- [X] T012 [US1] `inventario/router.py` — `POST /relojes`, `GET /relojes/{serie}`, `POST /relojes/{id}/fotos`, `GET/POST /calibres`
- [X] T013 [P] [US1] Frontend `inventario/` — `FichaReloj` con galería y `CatalogoCalibres`
- [X] T014 [P] [US1] Test `backend/tests/test_alta_reloj.py` — serie duplicada → 409; `evento_serie(ingreso)` creado; foto recuperable

## Phase 4: User Story 2 — Consultar el estado del inventario (P1) 🎯 MVP

- [X] T015 [US2] `inventario/router.py` — `GET /relojes` con filtros (marca, sucursal, disponibilidad, q) y paginación
- [X] T016 [P] [US2] `inventario/router.py` — `GET /valor-inventario` (a costo / a precio; a costo solo con `ver_costos`)
- [X] T017 [P] [US2] Frontend `inventario/` — `ListaRelojes` con búsqueda multi-criterio reactiva
- [X] T018 [P] [US2] Test `backend/tests/test_estado_inventario.py` — filtros correctos; unidad vendida no aparece en disponibles; `ver_costos` respetado

## Phase 5: User Story 3 — Gestión de piezas y repuestos (P1) 🎯 MVP

- [X] T019 [P] [US3] `piezas/service.py` — CRUD pieza, calibres compatibles, `perecedera`
- [X] T020 [US3] `piezas/service.py` — `registrar_movimiento` (usa T006); FEFO para consumo de perecederas; historial de uso
- [X] T021 [US3] `piezas/router.py` — `GET/POST /piezas`, `GET/PATCH /piezas/{id}`, `GET/POST /piezas/{id}/movimientos`, `GET /piezas/{id}/lotes`
- [X] T022 [P] [US3] Frontend `piezas/` — `ListaPiezas`, `FichaPieza`, `MovimientosPieza`
- [X] T023 [P] [US3] Test `backend/tests/test_stock_pieza.py` — consumo sin stock → 409; **concurrencia**: 10 consumos paralelos de la última unidad → solo 1 pasa

## Phase 6: User Story 4b — Insumos perecederos con lote y caducidad (P2)

- [X] T024 [US4b] `piezas/service.py` — crear `lote_pieza` en ingreso de perecedera; recalcular estado del lote (`vigente`/`proximo_vencer`/`vencido`) según `umbral_caducidad_dias`
- [X] T025 [US4b] `piezas/service.py` — consumir lote vencido: advertencia + payload para merma 011 (causa `insumo_caducado`)
- [X] T026 [P] [US4b] Frontend `piezas/` — `LotesCaducidad` + badges de estado
- [X] T027 [P] [US4b] Test `backend/tests/test_perecederos.py` — ingreso sin lote/fecha → 422; alerta `caducidad_proxima` con umbral; FEFO

## Phase 7: User Story 4 — Alertas de stock y reposición (P2)

- [X] T028 [US4] `inventario/service.py` + `piezas/service.py` — generar `alerta_stock` (`cerca_maximo`, `ultima_unidad`, `bajo_minimo`); no bloquear
- [X] T029 [US4] `inventario/router.py` — `GET /alertas-stock`; cada alerta incluye `accion_reponer` (cuerpo para `POST /ordenes-compra/prellenar` de 002)
- [X] T030 [P] [US4] Frontend `inventario/` — `PanelAlertasStock` con botón "Reponer stock" que abre el borrador de orden de compra (002) prellenado
- [X] T031 [P] [US4] Test `backend/tests/test_alertas_stock.py` — 1 unidad → `ultima_unidad`; superar máximo → `cerca_maximo` sin bloqueo; la acción devuelve el cuerpo de prellenado

## Phase 8: User Story 5 — Historial por número de serie (P2)

- [X] T032 [US5] `inventario/router.py` — `GET /relojes/{serie}/historial` (orden cronológico, append-only; sin endpoint de edición)
- [X] T033 [P] [US5] Frontend `inventario/` — `HistorialSerie` (línea de tiempo)
- [X] T034 [P] [US5] Test `backend/tests/test_historial_serie.py` — eventos ordenados; no hay ruta de edición/borrado

## Phase 9: User Story 6 — Corrección con rol elevado y restricción de costo (P3)

- [X] T035 [US6] `inventario/service.py` — `corregir_reloj(id, cambios, motivo)`: rol elevado + motivo; `evento_serie(correccion)`; re-vincular historial si cambia la serie; auditoría
- [X] T036 [US6] `inventario/router.py` — `PATCH /relojes/{id}`
- [X] T037 [P] [US6] Test `backend/tests/test_correccion_reloj.py` — 403 rol normal; 200 + evento + auditoría + historial preservado
- [X] T038 [P] [US6] Test `backend/tests/test_restriccion_costo.py` — `costo_adquisicion` ausente sin `ver_costos`

## Phase 10: Polish & Cross-Cutting

- [X] T039 [P] Exportación CSV/Excel/PDF de estado de inventario e historial (`shared/exportar.js`)
- [X] T040 [P] Registrar consumidores en `shared/parametros` (stock máximo, umbrales) para el recálculo de alertas
- [X] T041 [P] Papeles del Full Set: subida a `documentos` (`POST /relojes/{id}/documentos`)
- [X] T042 Ejecutar `quickstart.md` V1–V8 y registrar resultados

## Dependencies & Execution Order

- Setup → Foundational (T003–T009) → US1/US2/US3 (MVP) → US4b/US4 → US5/US6 → Polish.
- US4 (alertas) depende de US1–US3 (movimientos). US4 "Reponer" consume 002.

## Parallel Execution Examples

- Foundational: T005, T009 en paralelo; T006 y T007 en archivos distintos.
- MVP: US1 (T010–T014) || US3 (T019–T023); US2 (T015–T018) tras US1.
- Tests T014, T018, T023, T027, T031, T034, T037, T038 en paralelo con sus servicios.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US2 + US3 → inventario de relojes y piezas operativo con stock seguro.
2. **Incremento 2**: US4b (perecederos) + US4 (alertas + reposición).
3. **Incremento 3**: US5 (historial) + US6 (correcciones, restricción de costo).
4. **Cierre**: Polish + quickstart.

## Notas de implementación (2026-09-10)

- **Migración**: es `0009_inventario` (no `0008_*`, ya usado por `0008_proveedores_v2`).
- **`ver_costos`**: la constitución fija el enum de operaciones RBAC en 4
  (crear/consultar/editar/eliminar) y un test de migración lo verifica. La
  visibilidad de costo/margen se resuelve por **rol administrativo**
  (`inventario.service.puede_ver_costos` / `piezas.service.puede_ver_costos`:
  Gerencia General, Gerente de Sucursal, Contador, Administrador), no como una 5ª
  operación. La respuesta lleva `costos_visibles: bool` para que el frontend
  distinga "restringido" de "sin dato".
- **Historial inalterable**: `evento_serie` y `movimiento_stock_pieza` tienen
  trigger `BEFORE UPDATE OR DELETE` que aborta (append-only real en DB). Al
  corregir el número de serie NO se reescriben los eventos previos: `historial`
  resuelve serie → `reloj_id` y une todos los eventos de esa unidad física.
- **Hook recepción → inventario**: lo cablea `main.py` con
  `proveedores.registrar_receptor_inventario(piezas.recibir_de_compra)`. Las
  líneas de pieza suben stock (y lote si son perecederas); las de reloj quedan
  como "pendientes de fichar" (`GET /relojes/pendientes-recepcion`), visibles en
  el modal de alta.
- **Alertas de modelo**: `ultima_unidad` (stock ≤ `umbral_reposicion_relojes`,
  por defecto 1) abre la reposición; `cerca_maximo` (stock ≥ `stock_maximo_modelo`)
  es sobre-stock, avisa sin acción de compra.
- **Verificación**: `docker compose exec backend pytest` → 95 passed;
  `check_module_boundaries` + `check_contrast` + `npm run build` + `npm test` OK.
  Quickstart V1–V8 cubiertos por `test_inventario_relojes.py`,
  `test_piezas_stock.py`, `test_inventario_alertas.py`, `test_recepcion_a_inventario.py`.
