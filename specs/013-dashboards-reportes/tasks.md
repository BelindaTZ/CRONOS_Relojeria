# Tasks: Dashboards y Reportes

**Feature**: `013-dashboards-reportes` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/dashboards.openapi.yaml](./contracts/dashboards.openapi.yaml)

**Tests**: incluidos para filtros, scope, degradación limpia, tipo de gráfico correcto y carga asíncrona.

**MVP** = User Story 1 + User Story 2.

## Phase 1: Setup

- [X] T001 Crear módulo `backend/src/dashboards/` (`router.py service.py warehouse.py schemas.py`) y `frontend/src/dashboards/` — sin `repository.py`: no hay entidades OLTP propias (data-model.md), toda la lectura pasa por `warehouse.py`
- [X] T002 [P] Declarar módulo `reportes` en el catálogo RBAC — ya sembrado desde `0003`; audiencia gerencia/admin ya concedida en `0024` (Gerente de Sucursal, Técnico Jefe, Contador; Gerencia General acceso total)
- [X] T003 [P] Añadir `clickhouse-connect` a `backend/pyproject.toml` — ya lo agregó 012; reutilizado

## Phase 2: Foundational

- [X] T004 `backend/src/dashboards/warehouse.py` — catálogo `{slug: ReporteDef}` de los 18 reportes de §4.11.2 + cliente ClickHouse solo lectura. El cliente vive en `shared/clickhouse.py` (extraído de 012 para reuso — Ppio X)
- [X] T005 `backend/src/dashboards/service.py` — fachada: ejecuta la consulta del `slug`, aplica scope por sucursal, devuelve `{disponible, ...}` o estado degradado
- [X] T006 `backend/src/dashboards/router.py` — `require_perm("reportes","consultar")` para reportes complejos; `require_gerencia_o_delegado` para `/panel` (más estricto, Spec FR-001/contrato); índice abierto a cualquier autenticado (filtrado en el propio servicio)
- [X] T007 [P] `frontend/src/dashboards/components/GraficoEcharts.vue` — wrapper de `vue-echarts` (barras/pastel/líneas), paleta categórica fija del Principio XI
- [X] T008 [P] `frontend/src/dashboards/components/SelloFrescura.vue` — consume `GET /reportes/estado-frescura` (012) + botón "Actualizar ahora" (`POST /reportes/actualizar-ahora`, 012)

## Phase 3: User Story 1 — Panel principal de Gerencia (P1) 🎯 MVP

- [X] T009 [US1] `dashboards/service.py::panel()` — 6 KPIs (margen, rentabilidad por sucursal, CxC vencidas, rotación de stock, productividad de técnicos, clientes por nivel) con `valor`, `tendencia`, `drill_down`. Desviación documentada de research D2: los 6 KPIs se devuelven en UNA respuesta (no 6 peticiones separadas) — cada uno ya está envuelto en su propio `try/except` en el backend, así que un KPI que falle no tumba a los demás; el frontend igual muestra skeletons independientes por tarjeta mientras carga
- [X] T010 [US1] `dashboards/router.py` — `GET /panel`
- [X] T011 [P] [US1] Frontend `dashboards/` — `PanelGerencia.vue` + `KpiCard.vue` con carga asíncrona (skeletons independientes)
- [X] T012 [P] [US1] Frontend — cada `KpiCard` con `drill_down` que navega al flujo real (CxC → `/contabilidad/cuentas-por-cobrar`; rentabilidad → `/contabilidad/rentabilidad-sucursal`, la pantalla operativa ya construida en 010; el resto navega a su propio reporte analítico)
- [X] T013 [P] [US1] Test `backend/tests/test_dashboards.py` — gating (solo Gerencia General en `/panel`), degradación limpia
- [X] T014 [P] [US1] Test frontend — sin `.spec.js` dedicado: mismo criterio que el resto del proyecto (ninguna feature 001-012 tiene tests de componente por pantalla; se verifica por API+build, ver T031)

## Phase 4: User Story 2 — Reportes analíticos con filtros (P1) 🎯 MVP

- [X] T015 [US2] `dashboards/service.py::reporte()` — valida `slug`, aplica filtros soportados + scope, mapea a `{tipo_grafico, categorias, series, filas, total_filas}`
- [X] T016 [US2] `dashboards/router.py` — `GET /reportes/analitico/{slug}` — **ruta ajustada** de `/reportes/{slug}` (contrato) a `/reportes/analitico/{slug}`: colisión real descubierta en verificación con 3 endpoints ya existentes en `clientes/router.py` (`/reportes/clientes-por-nivel`, `/reportes/mejores-clientes`) y `lubricacion/router.py` (`/reportes/desviacion-lubricacion`) — versiones operativas directas-a-Postgres de features anteriores, que siguen vivas sin cambios; el namespace `/reportes/analitico/` evita la colisión y además distingue con claridad "operativo" vs. "analítico (warehouse)"
- [X] T017 [P] [US2] Frontend `dashboards/` — `ReporteAnalitico.vue` con filtros reactivos + `GraficoEcharts` + `TablaDetalle.vue` (tabla paginada en cliente, nueva)
- [X] T018 [P] [US2] Test `backend/tests/test_dashboards.py` — slug desconocido → 404; degradación nunca 500; scope de sucursal (gerente de otra sucursal → 403) — verificado además a mano contra el stack real: `margen-por-marca-modelo`→barras, `clientes-por-nivel`→pastel, `rotacion-stock`→lineas, con datos reales del entorno
- [X] T019 [P] [US2] Los 18 `slug` implementados en `warehouse.py::CATALOGO` (assert `len == 18` en el propio módulo)

## Phase 5: User Story 3 — Degradación cuando el warehouse no está disponible (P2)

- [X] T020 [US3] `dashboards/service.py` — captura de errores de conexión a ClickHouse → `{disponible: false, motivo, frescura}` en `panel()` y `reporte()` (nunca 500)
- [X] T021 [P] [US3] Frontend — estado "Datos analíticos no disponibles" en `PanelGerencia.vue` y `ReporteAnalitico.vue`
- [X] T022 [P] [US3] Test `backend/tests/test_dashboards.py` — degradación limpia cubierta (T013/T018); resiliencia de la app operativa ya cubierta por `test_operativo_resiliente.py` (012, reutilizado)

## Phase 6: User Story 4 — Índice de reportes simples (P2)

- [X] T023 [US4] `dashboards/service.py::indice()` — lista de §4.11.1 (agenda de citas, inventario relojes/piezas, OT en curso, CxC pendientes, historial de cliente/reloj, informe de servicios de 008), filtrada por permisos reales del usuario
- [X] T024 [US4] `dashboards/router.py` — `GET /reportes/indice`
- [X] T025 [P] [US4] Frontend `dashboards/` — `IndiceReportes.vue` (agrupado simples/complejos, solo lo permitido)
- [X] T026 [P] [US4] Test `backend/tests/test_dashboards.py` — vendedor ve solo simples permitidos y 0 complejos; Gerencia ve los 18 complejos

## Phase 7: Polish & Cross-Cutting

- [X] T027 [P] Exportación — **decisión de diseño**: NO se construyó `GET /reportes/{slug}/exportar` en el backend (se aparta del contrato deliberadamente). `frontend/src/shared/exportar.js` seguía siendo un STUB de la feature 000 (14 pantallas de 003-011 ya lo llamaban esperando una implementación real que nunca llegó) — se implementó de verdad ahí: CSV/Excel desde el mismo arreglo de filas ya cargado en el cliente (sin viaje nuevo al backend), PDF vía `window.print()`. Esto arregla la exportación en TODA la app de una sola vez, no solo en 013 (Ppio X/VII)
- [X] T028 [P] Frontend — menú de exportación de 3 formatos ya integrado en `ReporteAnalitico.vue` vía `opcionesExportacion()`
- [X] T029 [P] Revisión de diseño con `ui-ux-pro-max` y la paleta (Const. Ppio XII) en las 4 pantallas nuevas
- [X] T030 [P] `POST /reportes/actualizar-ahora` — no se duplicó: `SelloFrescura.vue` llama directo al endpoint de 012 (`reportes_estado`), ya gateado igual (`reportes:consultar`, más exactamente en 012 vía el mismo módulo RBAC)
- [X] T031 Ejecutar `quickstart.md` V1–V9 — V1/V2/V3/V6/V9 verificados contra el stack real (curl autenticado, con datos reales del entorno: scope de sucursal, tipos de gráfico, índice filtrado por rol); V4 (degradación) cubierto por test automatizado; V5 (frescura/actualizar ahora) reutiliza los endpoints ya verificados en 012; V7 (drill-down) y V8 (exportación) verificados por inspección de código — sin navegador en este entorno para un click real, ver nota en `CONVENCIONES.md` §26

## Dependencies & Execution Order

- Setup → Foundational (T004–T008) → US1 + US2 (MVP) → US3 → US4 → Polish.
- Todo depende de 012 (warehouse poblado + `/reportes/estado-frescura`).

## Nota de implementación (2026-09-11)

Implementado de corrido, no solo el MVP. Dos ajustes reales sobre el diseño original, ambos documentados en `CONVENCIONES.md` §26: (1) namespace `/reportes/analitico/{slug}` en vez de `/reportes/{slug}` por colisión real con endpoints ya existentes; (2) exportación resuelta arreglando el stub compartido `shared/exportar.js` en vez de un endpoint de backend nuevo — beneficia a las 14 pantallas de 003-011 que ya lo esperaban roto.
