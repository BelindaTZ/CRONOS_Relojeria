# Tasks: Técnicos y Productividad

**Feature**: `005-tecnicos-productividad` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/tecnicos.openapi.yaml](./contracts/tecnicos.openapi.yaml)

**Tests**: **cobertura obligatoria (Const. Ppio IX)** del cálculo de bono, tarifa horaria y prorrateo. Fixtures de OT en `backend/tests/fixtures/ordenes_trabajo.json`.

**MVP** = User Story 1 + User Story 2.

## Phase 1: Setup

- [X] T001 Crear módulo `backend/src/tecnicos/` (`router.py service.py costeo.py repository.py schemas.py`) y `frontend/src/tecnicos/`
- [X] T002 [P] Declarar módulo `tecnicos` y el permiso administrativo (`ver_costos` reutilizable o `tecnicos_admin`)
- [X] T003 [P] Crear `backend/tests/fixtures/ordenes_trabajo.json` (OT de prueba con técnico, horas, margen, fechas)

## Phase 2: Foundational

- [X] T004 Migración `0010_tecnicos` — `tecnico`, `especialidad`, `tecnico_especialidad`, `tecnico_sucursal`, `esquema_costo_mano_obra`, `regla_bono`, `componente_bono`, `periodo_liquidacion`, `bono_acumulado`, `bono_ot`
- [X] T005 [P] Migración de datos — parámetro `horas_productivas_estandar_mes = 160`
- [X] T006 [P] `tecnicos/repository.py` + `tecnicos/schemas.py`
- [X] T007 `tecnicos/router.py` — esqueleto con `require_perm("tecnicos", <op>)`

## Phase 3: User Story 1 — Ficha de técnico y costo interno (P1) 🎯 MVP

- [X] T008 [P] [US1] `tecnicos/service.py` — CRUD técnico, especialidades, certificaciones, sucursales, vínculo a `usuario`
- [X] T009 [US1] `tecnicos/service.py` — `set_costo(tecnico, sueldo, vigencia)` (historial, rol administrativo); `tarifa_hora(tecnico, fecha)` derivada
- [X] T010 [US1] `tecnicos/costeo.py` — `costo_mo_ot(tecnico_id, horas?, tipo_reparacion?)` (función pura) + endpoint interno `POST /_internal/costeo/costo-mo-ot`
- [X] T011 [US1] `tecnicos/router.py` — `GET/POST /tecnicos`, `GET/PATCH /tecnicos/{id}`, `PUT /tecnicos/{id}/estado`, `POST /tecnicos/{id}/costo`
- [X] T012 [US1] `tecnicos/service.py` — reglas: técnico no edita costo/especialidades/certificaciones ni se inactiva
- [X] T013 [P] [US1] Frontend `tecnicos/` — `FichaTecnico`, `EsquemaCosto` (rol administrativo), `ListaTecnicos` con búsqueda
- [X] T014 [P] [US1] Test `backend/tests/test_tecnico_costo.py` — `tarifa_hora` = sueldo/horas estándar; `costo_mo_ot` con y sin horas; sueldo oculto sin permiso; autoedición/autoinactivación → 403 **(crítico)**

## Phase 4: User Story 2 — Definir el esquema de bono (P1) 🎯 MVP

- [X] T015 [P] [US2] `tecnicos/service.py` — CRUD `regla_bono` + `componente_bono`; vigencia; auditoría
- [X] T016 [US2] `tecnicos/router.py` — `GET/POST /reglas-bono`
- [X] T017 [P] [US2] Frontend `tecnicos/` — `ReglaBono` (constructor de componentes con selectores, sin texto libre)
- [X] T018 [P] [US2] Test `backend/tests/test_regla_bono.py` — regla vigente y auditada; componentes válidos

## Phase 5: User Story 3 — Cálculo automático del bono acumulado (P2)

- [X] T019 [US3] `tecnicos/service.py` — indicadores por periodo: `ot_completadas`, `cumplimiento_tiempos`, `margen_generado`, `calidad` (desde OT de 008 / fixtures)
- [X] T020 [US3] `tecnicos/service.py` — `calcular_bono(periodo, tecnico?)`: evalúa componentes vs. umbral, suma, `valor_total ≥ 0`, `desglose`; prorratea en `bono_ot` por `costo_mo_ot`
- [X] T021 [US3] `tecnicos/service.py` — CRUD `periodo_liquidacion`, cerrar periodo (bonos `definitivo`)
- [X] T022 [US3] `tecnicos/router.py` — `POST /periodos-liquidacion`, `POST /periodos-liquidacion/{id}/cerrar`, `POST /bonos/calcular`, `GET /bonos`
- [X] T023 [US3] `tecnicos/service.py` — registrar consumidor en `shared/parametros`: `recalcular_por_parametro` recalcula `bono_acumulado` de periodos abiertos
- [X] T024 [P] [US3] Frontend `tecnicos/` — `PanelBono` (preview por periodo, desglose por indicador)
- [X] T025 [P] [US3] Test `backend/tests/test_calculo_bono.py` — 22 OT + margen X → `valor_total` esperado; 0 OT → 0; prorrateo suma exactamente `valor_total`; combinación de componentes **(crítico)**
- [X] T026 [P] [US3] Test `backend/tests/test_recalculo_bono.py` — cambiar `horas_productivas_estandar_mes` recalcula periodos abiertos, no los cerrados; auditoría **(crítico)**

## Phase 6: User Story 4 — Costo de MO para el costeo del servicio (P2)

- [X] T027 [US4] Verificar/estabilizar el contrato `POST /_internal/costeo/costo-mo-ot` para 008 (respuesta con `costo_mo`, `tarifa_hora`, `base`)
- [X] T028 [P] [US4] Test `backend/tests/test_contrato_costeo.py` — forma y valores del contrato; el costo no se filtra a respuestas públicas

## Phase 7: User Story 5 — Vista operativa de productividad (P2)

- [X] T029 [US5] `tecnicos/service.py` — `productividad(periodo, tecnico?)`: OT completadas, tiempo promedio, margen generado, bono alcanzado
- [X] T030 [US5] `tecnicos/router.py` — `GET /productividad`
- [X] T031 [P] [US5] Frontend `tecnicos/` — `PanelProductividad` + exportación CSV/Excel/PDF
- [X] T032 [P] [US5] Test `backend/tests/test_productividad.py` — coincide con las OT de fixtures

## Phase 8: Polish & Cross-Cutting

- [X] T033 [P] Catálogo `especialidad` inicial (Rolex, Omega, complicaciones…)
- [X] T034 [P] Nota en `CONVENCIONES.md`: comisiones de vendedores fuera de alcance (§8) pero el modelo de incentivos no lo impide
- [X] T035 Ejecutar `quickstart.md` V1–V7 y registrar resultados; confirmar cobertura del cálculo de bono

## Dependencies & Execution Order

- Setup → Foundational (T004–T007) → US1 + US2 (MVP) → US3 → US4/US5 → Polish.
- US3 usa fixtures de OT hasta que 008 exista; US4 expone el contrato que 008 consume.

## Parallel Execution Examples

- Foundational: T005, T006 en paralelo.
- MVP: US1 (T008–T014) || US2 (T015–T018).
- US3 tests T025, T026 en paralelo con T019–T023.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US2 → fichas de técnico con costeo y esquema de bono definible.
2. **Incremento 2**: US3 (motor de bono + recálculo) validado con fixtures.
3. **Incremento 3**: US4 (contrato para 008) + US5 (productividad) + Polish.

---

## Notas de implementación (2026-09-10)

- **Migración renumerada**: `0010_tecnicos` → **`0016_tecnicos`** (0010 lo tomó la feature 004). Encadenada tras `0015`.
- **Fuente de OT**: como 008 aún no existe, `tecnicos.registrar_proveedor_ot(fn)` es el punto donde 008 conectará la fuente de OT cerradas (patrón `registrar_receptor_inventario`). Sin proveedor registrado, no hay OT → todos los bonos e indicadores son 0. Los tests inyectan un proveedor de `backend/tests/fixtures/ordenes_trabajo.json`.
- **FR-010 reforzado**: un periodo **sin OT** arroja bono 0 aunque un indicador por defecto lo supere (la calidad sin reprocesos = 100 ≥ umbral). El motor corta antes de evaluar la regla.
- **Permiso administrativo**: se reutiliza el patrón `_ROLES_VER_COSTOS` / `_ROLES_JEFE` (rol por nombre: "Técnico Jefe", "Gerencia General", "Contador"…), no una 5ª operación RBAC (las operaciones siguen fijas en 4).
- **`combinacion`**: componente que paga `valor` como monto fijo **y** `valor` como fracción del margen, ambos si el indicador supera el umbral. Un componente nunca resta (se acota a ≥ 0); el total también.
- **Parámetros nuevos** (`0016`): `horas_productivas_estandar_mes = 160`, `tiempo_estimado_horas_default = 2`. El primero registra su consumidor de recálculo en cascada (`tecnicos.recalculo_bonos`).
- Tests: `test_tecnico_costo.py`, `test_regla_bono.py`, `test_calculo_bono.py`, `test_recalculo_bono.py`, `test_contrato_costeo.py`, `test_productividad.py` (17 tests) — backend **129 pasan**.
