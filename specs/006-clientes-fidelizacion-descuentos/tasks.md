# Tasks: Clientes, Fidelización y Descuentos

**Feature**: `006-clientes-fidelizacion-descuentos` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: **cobertura obligatoria (Const. Ppio IX)** de cálculo de nivel y margen mínimo protegido. Fixtures en `backend/tests/fixtures/transacciones_cliente.json`.

**MVP** = User Story 1 + User Story 4 (cliente + margen mínimo — la protección financiera es prioritaria).

## Phase 1: Setup

- [X] T001 Crear módulo `backend/src/clientes/` (`router.py service.py nivel.py repository.py schemas.py`), `backend/src/shared/descuentos/` (`aplicar.py margen_minimo.py`) y `frontend/src/clientes/`
- [X] T002 [P] Declarar módulo `clientes_fidelizacion` en el catálogo RBAC
- [X] T003 [P] Fixtures `backend/tests/fixtures/transacciones_cliente.json` y `clientes_prueba.json`

## Phase 2: Foundational

- [X] T004 Migración `0011_clientes` — todas las tablas de `data-model.md`
- [X] T005 [P] Migración de datos — nivel base "Bronce"; parámetros `margen_minimo` (global), `texto_consentimiento_lopdp` v1, `monto_max_consumidor_final`; fila `cliente` genérica `es_consumidor_final`
- [X] T006 [P] `clientes/repository.py` + `clientes/schemas.py`
- [X] T007 `clientes/router.py` — esqueleto con `require_perm("clientes_fidelizacion", <op>)`
- [X] T008 Secuencia de `numero_afiliado` (`AF-######`)

## Phase 3: User Story 1 — Ficha de cliente (P1) 🎯 MVP

- [X] T009 [P] [US1] `clientes/service.py` — crear cliente (valida identificación única, consentimiento aceptado), `numero_afiliado` autogenerado, nivel base
- [X] T010 [US1] `clientes/service.py` — editar cliente (identificación solo rol elevado), auditoría; no DELETE con transacciones
- [X] T011 [US1] `clientes/router.py` — `GET/POST /clientes`, `GET/PATCH /clientes/{id}`
- [X] T012 [P] [US1] Frontend `clientes/` — `FichaCliente` (con casilla de consentimiento LOPDP mostrando el texto versionado), `ListaClientes` con búsqueda multi-criterio
- [X] T013 [P] [US1] Test `backend/tests/test_cliente_crud.py` — sin consentimiento → 422; identificación duplicada → 409; edición de identificación con rol normal → 403; búsqueda multi-criterio

## Phase 4: User Story 4 — Margen mínimo protegido (P1) 🎯 MVP 🔒

- [X] T014 [US4] `shared/descuentos/margen_minimo.py` — `evaluar(margen_resultante, ambito, ref)` → `permitir|bloquear|requiere_autorizacion` con precedencia producto→marca→global (parámetro de 001)
- [X] T015 [US4] `shared/descuentos/aplicar.py` — `aplicar(item_ref, costo, precio_lista, descuento|cupon)` → `{precio_final, monto_descontado, margen_resultante, decision}`; 422 si vienen descuento y cupón
- [X] T016 [US4] `clientes/router.py` — `GET/PUT /margen-minimo`, `POST /_internal/descuentos/aplicar`, `POST /_internal/descuentos/autorizar`
- [X] T017 [US4] `clientes/service.py` — `autorizar_margen_minimo(documento, motivo)`: solo Gerencia General; crea `autorizacion_margen_minimo`; auditoría
- [X] T018 [P] [US4] Frontend — pantalla de configuración de margen mínimo (Gerencia General) + modal de autorización
- [X] T019 [P] [US4] Test `backend/tests/test_margen_minimo.py` — descuento bajo mínimo → `bloquear`/`requiere_autorizacion`; con autorización → `permitir` + registro; margen == mínimo; cálculo siempre de backend; descuento+cupón → 422 **(crítico)**

## Phase 5: User Story 2 — Configurar niveles (P1)

- [X] T020 [P] [US2] `clientes/service.py` — CRUD `nivel_fidelizacion` + `regla_nivel`; vigencia; auditoría
- [X] T021 [US2] `clientes/router.py` — `GET/POST /niveles`, `PUT /niveles/{id}/regla`
- [X] T022 [P] [US2] Frontend `clientes/` — `ConfigNiveles` (criterio, umbral, beneficios con selectores)

## Phase 6: User Story 3 — Recálculo del nivel (P1) 🔒

- [X] T023 [US3] `clientes/nivel.py` — `calcular_nivel(cliente, transacciones, reglas)` función pura (ventana, criterio, mayor orden que cumple)
- [X] T024 [US3] `clientes/service.py` — `recalcular_nivel(cliente_id, hecho, documento_id)`: si cambia, `historial_nivel_cliente`
- [X] T025 [US3] `clientes/router.py` — `POST /_internal/fidelizacion/recalcular` (consumido por 008/009)
- [X] T026 [US3] `clientes/service.py` — job diferido `recalcular_masivo()` al cambiar `regla_nivel`; registrar consumidor en `shared/parametros`
- [X] T027 [P] [US3] Test `backend/tests/test_calculo_nivel.py` — set de clientes con históricos diversos → nivel correcto; sube tras venta; no duplica si no cambia; recálculo masivo conserva historial **(crítico)**

## Phase 7: User Story 5 — Descuentos generales y cupones (P1)

- [X] T028 [P] [US5] `clientes/service.py` — CRUD `descuento`; resolución del descuento aplicable a (cliente, ítem, momento)
- [X] T029 [US5] `clientes/service.py` — CRUD `cupon`; `consumir_cupon(codigo, documento)` con lock; estados (activo/usado/vencido); `usos ≤ max_usos`
- [X] T030 [US5] `clientes/router.py` — `GET/POST /descuentos`, `PATCH /descuentos/{id}`, `GET/POST /cupones`, `POST /_internal/cupones/consumir`
- [X] T031 [P] [US5] Frontend `clientes/` — `PanelDescuentos`, `PanelCupones`
- [X] T032 [P] [US5] Test `backend/tests/test_cupones.py` — uso único no se consume dos veces (concurrencia); vencido → 409; alcance producto/marca/tienda; límites de uso

## Phase 8: User Story 6 — Reportes de clientes (P2)

- [X] T033 [P] [US6] `clientes/service.py` — `clientes_por_nivel()`, `mejores_clientes(top, desde)`, `historial_cliente(id)`
- [X] T034 [US6] `clientes/router.py` — `GET /reportes/clientes-por-nivel`, `GET /reportes/mejores-clientes`, `GET /clientes/{id}/historial`
- [X] T035 [P] [US6] Frontend `clientes/` — `HistorialCliente` + exportación CSV/Excel/PDF

## Phase 9: Polish & Cross-Cutting

- [X] T036 [P] Estabilizar `contracts/descuentos.openapi.yaml` como contrato para 008 y 009 (pruebas de contrato)
- [X] T037 [P] Registrar consumidores en `shared/parametros` (niveles, margen mínimo, texto de consentimiento)
- [X] T038 [P] `aplicacion_descuento` — helper para que 008/009 registren la aplicación en la venta/OT
- [X] T039 Ejecutar `quickstart.md` V1–V8; confirmar cobertura de nivel y margen mínimo
- [X] T040 [P] Revisar `checklists/business-rules.md` (cerrar BR002, BR004, BR009)

## Dependencies & Execution Order

- Setup → Foundational (T004–T008) → US1 + US4 (MVP) → US2 → US3 → US5 → US6 → Polish.
- US3 usa fixtures de transacciones; 008/009 invocarán `recalcular` y `aplicar` cuando existan.

## Parallel Execution Examples

- Foundational: T005, T006 en paralelo.
- MVP: US1 (T009–T013) || US4 (T014–T019).
- US3 test T027 en paralelo con T023–T026; US5 test T032 con T028–T031.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US4 → clientes con la protección de margen mínimo operativa.
2. **Incremento 2**: US2 + US3 (niveles + motor de recálculo) validados con fixtures.
3. **Incremento 3**: US5 (descuentos/cupones) + US6 (reportes) + Polish.

---

## Notas de implementación (2026-09-10)

- **Migración renumerada**: `0011_clientes` → **`0017_clientes`** (0011 lo tomó `0011_auditoria_ip`). Encadenada tras `0016`.
- **Fuente de transacciones**: como 008/009 aún no existen, `clientes.registrar_proveedor_transacciones(fn)` es el punto de conexión (patrón `registrar_receptor_inventario`). `fn(db, cliente_id) -> [TransaccionCliente{fecha, monto, tipo, documento_id?, detalle?}]`. Sin proveedor: el nivel de todos es el base y los reportes de volumen van vacíos. Tests inyectan `backend/tests/fixtures/transacciones_cliente.json`.
- **`shared/descuentos/`** (capacidad compartida, `aplicar.py` + `margen_minimo.py`): `aplicar(db, *, item_ref, costo, precio_lista, marca?, descuento?, cupon?) -> {precio_final, monto_descontado, margen_resultante, decision, margen_minimo}`. 008 y 009 la consumen. `decision` ∈ {permitir, bloquear, requiere_autorizacion}. 422 si vienen descuento **y** cupón.
- **Decisiones de la checklist `business-rules.md`** cerradas en implementación:
  - BR002: cuentan compras (venta) + servicios; montos ya netos de anulaciones (009 enviará el reverso).
  - BR004: descenso de nivel permitido e inmediato (recálculo automático, sin periodo de gracia) — decisión del negocio.
  - BR009: `margen = precio_final − costo` (absoluto). Para servicios, `costo` que entra ya incluye MO + piezas + insumos (008).
  - BR010: precedencia producto → marca → global (parámetro `margen_minimo` por ámbito).
  - BR011: política configurable `margen_minimo_politica` ∈ {bloquear, autorizar} (por defecto `autorizar`).
  - BR013: `margen == mínimo` ⇒ permitir (`>=`).
  - BR014: cambiar `margen_minimo` registra su consumidor (`clientes.recalculo_margen`); 008/009 recalcularán sus operaciones abiertas cuando existan.
- **`nivel.py`**: sin dependencia externa — `_restar_meses` propio (no `dateutil`).
- **Permiso administrativo**: config de niveles / descuentos / cupones / margen mínimo → `require_gerencia_o_delegado`. Editar `identificacion` del cliente → rol elevado (`_ROLES_ELEVADOS`). Sin 5ª operación RBAC.
- **Consumidor final**: fila `cliente` única `es_consumidor_final = true` (`AF-000000`), oculta de los listados normales, no editable, sin nivel ni cupones. `clientes.id_consumidor_final(db)` para 009.
- Tests: `test_cliente_crud.py`, `test_margen_minimo.py`, `test_calculo_nivel.py`, `test_cupones.py` (21 tests) — backend **150 pasan**.

## Ampliación implementada (2026-09-10) — FR-026..FR-030

- [X] Migración `0018` — parámetros `churn_*`.
- [X] `clientes/riesgo.py` — función pura `analizar(...)` (cadencia mediana + piso + factor + historial mínimo).
- [X] `clientes/service.py` — `clientes_en_riesgo(db)` (solo niveles no base), `emitir_cupon_reactivacion(db, datos)`; `TransaccionCliente.sucursal_id`; `historial_cliente` con sucursal.
- [X] `clientes/router.py` — `GET /reportes/clientes-en-riesgo`, `POST /cupones/reactivacion`.
- [X] Frontend — `ClientesEnRiesgoView.vue` (tabla + KPIs + exportación + modal "cupón de reactivación"), ruta `/clientes/en-riesgo`, entrada de nav "Clientes en riesgo", enlace desde `ReportesClientes`. `HistorialCliente` muestra la sucursal. `ClienteFormModal` — dirección con helper "Opcional". `ParametrosView` — 4 params `churn_*`.
- [X] Test `backend/tests/test_riesgo_abandono.py` (3 tests) — función pura + reporte solo Plata/Oro + emisión de cupón. Backend **153 pasan**.
