# Tasks: Mermas y Pérdidas

**Feature**: `011-mermas-perdidas` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/mermas.openapi.yaml](./contracts/mermas.openapi.yaml)

**Tests**: **cobertura obligatoria (Const. Ppio IX)** del registro/costeo de mermas, umbral de autorización y baja + asiento.

**MVP** = User Story 1 + User Story 2 + User Story 3.

## Phase 1: Setup

- [x] T001 Crear módulo `backend/src/mermas/` (capas) y `frontend/src/mermas/`
- [x] T002 [P] Declarar módulo `mermas` en el catálogo RBAC (Técnico: crear/consultar; Gerente de Sucursal: CRUD; Gerencia General: también "autorizar baja")

## Phase 2: Foundational

- [x] T003 Migración `0016_mermas` — `merma`, `autorizacion_baja`, `documento_soporte_merma`, `reclamo_merma`, `historial_estado_merma`
- [x] T004 [P] Migración de datos — parámetro `umbral_merma_autorizacion`; cuenta contable de pérdida extraordinaria + `regla_asiento_automatico` para `merma_confirmada`
- [x] T005 [P] `mermas/repository.py` + `mermas/schemas.py`
- [x] T006 `mermas/service.py` — máquina de estados con guardas (research D2)
- [x] T007 `mermas/router.py` — esqueleto con `require_perm("mermas", <op>)` y `scope_sucursal`

## Phase 3: User Story 1 — Reportar una merma (P1) 🎯 MVP 🔒

- [x] T008 [US1] `mermas/service.py` — `crear_merma` (calcula `costo_perdida` a costo de adquisición; valida bien no vendido/dado de baja; pieza ≤ stock)
- [x] T009 [US1] `mermas/service.py` — subir `documento_soporte_merma` a bucket `documentos` (`shared/storage`)
- [x] T010 [US1] `mermas/router.py` — `GET/POST /mermas`, `GET /mermas/{id}`, `POST /mermas/{id}/documentos`
- [x] T011 [US1] Serializador que oculta `costo_perdida` a roles no administrativos
- [x] T012 [P] [US1] Frontend `mermas/` — `PanelMerma` (causa del catálogo, adjuntos), `ListaMermas` con búsqueda
- [x] T013 [P] [US1] Test `backend/tests/test_crear_merma.py` — costo a costo de adquisición; bien vendido → 409; pieza > stock → 422; costo oculto sin rol admin **(crítico)**

## Phase 4: User Story 2 — Autorización de baja sobre el umbral (P1) 🎯 MVP 🔒

- [x] T014 [US2] `mermas/service.py` — `autorizar_baja(merma, observacion)`: solo Gerencia General; crea `autorizacion_baja`; auditoría
- [x] T015 [US2] `mermas/service.py` — guarda en la transición a `dado_de_baja`: si `costo_perdida > umbral` y sin `autorizacion_baja` → 409
- [x] T016 [US2] `mermas/router.py` — `POST /mermas/{id}/autorizar-baja`
- [x] T017 [P] [US2] Frontend `mermas/` — `AutorizarBaja` (acción del panel de trabajo, modal con observación)
- [x] T018 [P] [US2] Test `backend/tests/test_autorizar_baja.py` — sobre el umbral sin autorización → 409; con autorización → procede; registra quién/cuándo **(crítico)**

## Phase 5: User Story 3 — Baja del inventario y asiento (P1) 🎯 MVP 🔒

- [x] T019 [US3] `mermas/service.py` — `dar_de_baja`: reloj → `dado_de_baja` + `evento_serie(baja)`; pieza → `movimiento_stock_pieza(merma)`; historial conservado
- [x] T020 [US3] `mermas/service.py` — invocar 010 `asientos_auto.generar("merma_confirmada", {costo_perdida, ...})` (cuenta de pérdida extraordinaria)
- [x] T021 [US3] `mermas/router.py` — `POST /mermas/{id}/estado`
- [x] T022 [P] [US3] Test `backend/tests/test_baja_merma.py` — bien fuera del stock activo; historial consultable por serie; asiento de pérdida extraordinaria generado **(crítico)**

## Phase 6: User Story 4 — Ciclo de estados y reingreso (P2)

- [x] T023 [US4] `mermas/service.py` — `reparado_reingresado`: reloj → `disponible` + `evento_serie(reingreso)`; pieza → `movimiento_stock_pieza(ingreso)`; merma queda en historial
- [x] T024 [US4] `mermas/service.py` — `reclamo_merma` CRUD (destino proveedor/seguro, estado, monto recuperado)
- [x] T025 [US4] `mermas/router.py` — `POST/PATCH /mermas/{id}/reclamo`
- [x] T026 [P] [US4] Frontend `mermas/` — `ReclamoPanel` + acción de reingreso
- [x] T027 [P] [US4] Test `backend/tests/test_reingreso_merma.py` — bien vuelve al stock; merma en historial

## Phase 7: User Story 5 — Mermas derivadas de servicio o traslado (P2)

- [x] T028 [US5] `mermas/service.py` — aceptar payloads prellenados de 008 (`dano_servicio`, `orden_trabajo_id`, `tecnico_id`) y 004 (`dano_transito`, `transferencia_id`)
- [x] T029 [P] [US5] Test `backend/tests/test_merma_derivada.py` — vínculos conservados; sin sanción automática al técnico

## Phase 8: User Story 6 — Reporte de mermas (P2)

- [x] T030 [US6] `mermas/service.py` — `reporte_mermas(filtros)` agrupado por causa (monto, frecuencia)
- [x] T031 [US6] `mermas/router.py` — `GET /reportes/mermas`
- [x] T032 [P] [US6] Frontend `mermas/` — `ReporteMermas` + exportación CSV/Excel/PDF
- [x] T033 [P] [US6] Test `backend/tests/test_reporte_mermas.py` — cuadra por monto/causa/frecuencia; `insumo_caducado` con lote

## Phase 9: Polish & Cross-Cutting

- [x] T034 [P] Integración con la alerta de lote vencido de 003 (acción "dar de baja por merma" prellena `POST /mermas` con `insumo_caducado`)
- [x] T035 [P] Registrar consumidor en `shared/parametros` (`umbral_merma_autorizacion`)
- [x] T036 Ejecutar `quickstart.md` V1–V8; confirmar cobertura del registro/costeo de mermas

## Dependencies & Execution Order

- Setup → Foundational (T003–T007) → US1 → US2 → US3 (MVP) → US4 → US5 → US6 → Polish.
- US3 depende de la API de asientos de 010; US5 recibe payloads de 008 y 004.

## Parallel Execution Examples

- Foundational: T004, T005 en paralelo.
- Tests T013, T018, T022, T027, T029, T033 en paralelo con sus servicios.
- Frontend T012, T017, T026, T032 en paralelo.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US2 + US3 → merma reportada, autorizada y dada de baja con asiento.
2. **Incremento 2**: US4 (ciclo completo + reclamos) + US5 (orígenes derivados).
3. **Incremento 3**: US6 (reporte) + Polish (integración con alerta de caducidad).
