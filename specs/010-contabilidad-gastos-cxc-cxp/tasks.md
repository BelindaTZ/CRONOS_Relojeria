# Tasks: Contabilidad, Gastos, CxC y CxP

**Feature**: `010-contabilidad-gastos-cxc-cxp` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/contabilidad.openapi.yaml](./contracts/contabilidad.openapi.yaml)

**Tests**: incluidos para asientos balanceados, aging, arqueo, protesto de cheque y rentabilidad por sucursal.

**MVP** = User Story 1 + User Story 3 + User Story 5.

## Phase 1: Setup

- [x] T001 Crear módulo `backend/src/contabilidad/` (`router.py service.py gastos.py recurrentes.py scheduler.py asientos_auto.py caja.py repository.py schemas.py`) y `frontend/src/contabilidad/`; añadir `APScheduler` a `backend/pyproject.toml`
- [x] T002 [P] Declarar módulo `contable` en el catálogo RBAC (Vendedor/Técnico sin acceso, Gerente de Sucursal solo consultar, Gerencia General CRUD)

## Phase 2: Foundational

- [x] T003 Migración `0015_contabilidad` — todas las tablas de `data-model.md`
- [x] T004 [P] Migración de datos — plan de cuentas NIIF PYMES; `regla_asiento_automatico` inicial (venta / compra / gasto_pagado / gasto_por_pagar / merma / cobro / pago)
- [x] T005 [P] `contabilidad/repository.py` + `contabilidad/schemas.py`
- [x] T006 `contabilidad/service.py` — validación de partida doble (`Σ debe = Σ haber`); consultas mayor/balance/estado de resultados
- [x] T007 `contabilidad/router.py` — esqueleto con `require_perm("contable", <op>)` y `scope_sucursal`

## Phase 3: User Story 1 — Libro diario y derivados (P1) 🎯 MVP

- [x] T008 [US1] `contabilidad/service.py` — `crear_asiento` (rechaza descuadrado; rechaza fecha en periodo cerrado sin `ajuste_de_asiento_id`)
- [x] T009 [US1] `contabilidad/service.py` — `mayor`, `balance_comprobacion`, `estado_resultados` (consultas)
- [x] T010 [US1] `contabilidad/router.py` — `GET/POST /asientos`, `GET /mayor`, `GET /balance`, `GET /estado-resultados`, `GET/POST /plan-cuentas`
- [x] T011 [P] [US1] Frontend `contabilidad/` — `LibroDiario`, `BalanceComprobacion`, `EstadoResultados`, `PlanCuentas`
- [x] T012 [P] [US1] Test `backend/tests/test_asientos.py` — descuadrado → 422; balance cuadra; asiento en periodo cerrado exige ajuste **(crítico)**

## Phase 4: User Story 2 — Caja y bancos por sucursal (P1)

- [x] T013 [US2] `contabilidad/caja.py` — abrir sesión, `movimiento_caja`, cerrar sesión (`efectivo_esperado`, `diferencia`), lock ante concurrencia
- [x] T014 [US2] `contabilidad/router.py` — `POST /caja/{sucursal_id}/sesiones`, `.../movimientos`, `.../sesiones/actual/cerrar`
- [x] T015 [P] [US2] Frontend `contabilidad/` — `PanelCaja` (apertura/cierre/arqueo)
- [x] T016 [P] [US2] Test `backend/tests/test_caja.py` — diferencia registrada; movimiento en sesión cerrada → 409; cierre concurrente idempotente

## Phase 5: User Story 3 — Cuentas por cobrar (P1) 🎯 MVP

- [x] T017 [US3] `contabilidad/service.py` — ingesta de `cuenta_por_cobrar` de 009/008; `cobro_cxc` (parcial/total); `aging`
- [x] T018 [US3] `contabilidad/router.py` — `GET /cxc`, `POST /cxc/{id}/cobros`, `GET /cxc/aging`, `GET /cxc-pendientes`
- [x] T019 [P] [US3] Frontend `contabilidad/` — `AgingCxC`, reporte de CxC pendientes
- [x] T020 [P] [US3] Test `backend/tests/test_cxc.py` — CxC por saldo exacto; cobro parcial reduce saldo; aging por tramos **(crítico)**

## Phase 6: User Story 4 — Cuentas por pagar (P1)

- [x] T021 [US4] `contabilidad/service.py` — `cuenta_por_pagar` con `origen_tipo` (`orden_compra` de 002 **o** `gasto`), contraparte proveedor **o** beneficiario; `pago_cxp` con `retencion_fuente`; `aging`; invariante de contraparte/origen único
- [x] T022 [US4] `contabilidad/router.py` — `GET/POST /beneficiarios`, `GET /cxp` (filtro por origen/contraparte), `POST /cxp/{id}/pagos`, `GET /cxp/aging`
- [x] T023 [P] [US4] Test `backend/tests/test_cxp.py` — CxP de compra (002) y CxP de gasto comparten aging/pagos; pago con retención; invariante proveedor⊕beneficiario / orden_compra⊕gasto

## Phase 7: User Story 5 — Gastos operativos: pagado o por pagar (P1) 🎯 MVP

- [x] T024 [US5] `contabilidad/gastos.py` — `registrar_gasto` (solo Gerencia General; exige categoría; soporte a `documentos`; `estado_pago`): `pagado` → movimiento de caja/banco + asiento; `por_pagar` → `cuenta_por_pagar` (`origen_tipo=gasto`) + asiento
- [x] T025 [US5] `contabilidad/router.py` — `GET/POST /gastos` (con `estado_pago`, `beneficiario_id`/`proveedor_id`, `medio_pago`)
- [x] T026 [P] [US5] Frontend `contabilidad/` — `PanelGastos` (categoría del catálogo, selector pagado/por-pagar, selector proveedor/beneficiario, adjunto de soporte)
- [x] T027 [P] [US5] Test `backend/tests/test_gastos.py` — sin categoría → 422; `por_pagar` sin contraparte → 422; `pagado` sin medio → 422; Gerente de Sucursal → 403; gasto "por pagar" aparece en `/cxp`; gasto "pagado" genera movimiento y asiento **(crítico)**

## Phase 7b: User Story 5b — Gastos recurrentes (P2)

- [x] T027a [US5b] `contabilidad/recurrentes.py` — CRUD `gasto_recurrente` (frecuencia, monto estimado, contraparte); cálculo de `proxima_generacion`
- [x] T027b [US5b] `contabilidad/scheduler.py` — job horario que genera el `gasto` en `borrador` (monto estimado) de los recurrentes vencidos y avanza `proxima_generacion`; endpoint interno `POST /_internal/scheduler/tick` para pruebas
- [x] T027c [US5b] `contabilidad/gastos.py` — `confirmar_gasto(id, monto, estado_pago, medio_pago?)`: pasa el borrador a `confirmado`, genera asiento y (si `por_pagar`) la CxP
- [x] T027d [US5b] `contabilidad/router.py` — `GET/POST /gastos-recurrentes`, `PUT /gastos-recurrentes/{id}/estado`, `POST /gastos/{id}/confirmar`
- [x] T027e [P] [US5b] Frontend `contabilidad/` — `GastosRecurrentes` (crear/pausar/cancelar) y bandeja de borradores a confirmar
- [x] T027f [P] [US5b] Test `backend/tests/test_gastos_recurrentes.py` — activo+vencido → 1 borrador (sin asiento ni CxP); pausado → no genera; confirmar → asiento + CxP según `estado_pago` **(módulo con lógica)**

## Phase 8: User Story 6 — Asientos automáticos y rentabilidad (P2)

- [x] T028 [US6] `contabilidad/asientos_auto.py` — `generar(evento, payload)` según `regla_asiento_automatico` (venta, compra, `gasto_pagado`, `gasto_por_pagar`, merma, cobro, pago); endpoint interno para que 009/002/011 lo invoquen
- [x] T029 [US6] `contabilidad/service.py` — `rentabilidad_sucursal(periodo, sucursal)` (ingresos − costos − gastos operativos)
- [x] T030 [US6] `contabilidad/router.py` — `GET/PUT /reglas-asiento`, `GET /rentabilidad-sucursal`
- [x] T031 [P] [US6] Frontend `contabilidad/` — `RentabilidadSucursal`
- [x] T032 [P] [US6] Test `backend/tests/test_asientos_auto.py` y `test_rentabilidad.py` — venta genera asiento; rentabilidad descuenta gastos operativos **(crítico)**

## Phase 9: User Story 7 — Cheques (P2)

- [x] T033 [US7] `contabilidad/service.py` — CRUD `cheque`; `protestar` (revierte cobro, reactiva CxC, atómico)
- [x] T034 [US7] `contabilidad/router.py` — `GET /cheques`, `POST /cheques/{id}/protestar`
- [x] T035 [P] [US7] Test `backend/tests/test_cheques.py` — protesto revierte cobro y reactiva CxC

## Phase 10: User Story 8/9 — Cierre de periodo y estado de resultados (P2/P3)

- [x] T036 [US9] `contabilidad/service.py` — `periodo_contable` CRUD; `cerrar` (bloquea edición; ajustes por asiento nuevo)
- [x] T037 [US9] `contabilidad/router.py` — `POST /periodos/{periodo}/cerrar`
- [x] T038 [P] [US9] Test `backend/tests/test_cierre_periodo.py` — original inmutable; ajuste requiere `ajuste_de_asiento_id`; parámetro no recalcula periodo cerrado

## Phase 11: Polish & Cross-Cutting

- [x] T039 [P] Exportación CSV/Excel/PDF de libros y reportes (solo CSV si > 5 000 filas)
- [x] T040 [P] Registrar consumidor en `shared/parametros` (aunque contabilidad no recalcula periodos cerrados)
- [x] T041 Ejecutar `quickstart.md` V1–V9 (incluye V5, V5b) y registrar resultados — cada escenario mapea 1:1 a un test de `test_contabilidad.py` (ver Notas de implementación en `data-model.md`)
- [x] T042 [P] Revisar `checklists/accounting.md` (cerrar ACC004, ACC006, ACC008, ACC011) — ACC004: `Decimal` + `ROUND_HALF_UP` a centavos en todo `service.py`; ACC006: evento sin regla activa → `logger.warning`, no excepción (`asientos_auto.generar`/`generar_reversa`); ACC008: `ventas.anular_venta` invoca `generar_asiento_reversa`; ACC011: `cerrar_periodo` exige `es_gerencia`. El checklist en sí queda sin marcar (gate de solo lectura del reviewer)
- [x] T043 [P] Catálogo inicial de beneficiarios de servicios comunes (alcance opcional implementado mediante creación inline `:crear` en `GastoFormModal.vue` y tabla `beneficiario`)

## Dependencies & Execution Order

- Setup → Foundational (T003–T007) → US1 + US3 + US5 (MVP) → US2 → US4 → US5b → US6 → US7 → US8/US9 → Polish.
- US3/US4 consumen datos de 009/008/002; US6 lo invocan 009/002/011; US7 usa cheques originados en 008/009.
- US5b (gastos recurrentes) depende de US5 (registro/confirmación de gasto) y de US4 (CxP genérica).

## Parallel Execution Examples

- Foundational: T004, T005 en paralelo.
- MVP: US1 (T008–T012) || US5 (T024–T027); US3 (T017–T020) tras Foundational.
- Tests T012, T016, T020, T023, T027, T032, T035, T038 en paralelo con sus servicios.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US3 + US5 → diario, CxC y gastos operativos (pagados y por pagar).
2. **Incremento 2**: US2 (caja) + US4 (CxP de compras y de gastos) + US5b (gastos recurrentes) + US6 (asientos automáticos + rentabilidad).
3. **Incremento 3**: US7 (cheques) + US8/US9 (cierre de periodo) + Polish.
