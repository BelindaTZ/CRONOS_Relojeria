# Implementation Plan: Dashboards y Reportes

**Branch**: `013-dashboards-reportes` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Capa de visualización analítica sobre el warehouse de 012. **Panel principal de Gerencia General** con 5–6 KPIs críticos (§4.11.3), con carga asíncrona, sello de frescura y drill-down que abre el flujo real. **Reportes analíticos de §4.11.2** leídos desde ClickHouse con filtros reactivos (periodo/sucursal/marca/técnico) y gráficos `vue-echarts` según el tipo de dato (barras/pastel/líneas/KPI). **Índice unificado** de los reportes operativos simples de §4.11.1 (que viven en sus módulos, incluido el informe de servicios de 008), filtrado por rol. **Exportación** CSV/Excel/PDF (solo CSV si > 5 000 filas). **Degradación limpia** si el warehouse no está disponible. Scope por sucursal.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI (fachada de lectura sobre ClickHouse), Vue 3

**Primary Dependencies**: `clickhouse-connect` (backend, solo lectura del warehouse), `vue-echarts` (ya instalado), `shared/exportar.js`, `shared/guard` (scope), `shared/api/client.js`; consume 012 (`/reportes/estado-frescura`, `/reportes/actualizar-ahora`, modelos de ClickHouse)

**Storage**: solo lectura de ClickHouse (012); ningún esquema propio en PostgreSQL

**Testing**: `pytest` (fachada de reportes: filtros, scope, degradación), `vitest` (gráficos correctos por tipo de dato, carga asíncrona, drill-down)

**Project Type**: Web — módulo `dashboards`

**Performance Goals**: panel < 3 s con carga asíncrona (no bloquea); reporte con filtros < 3 s

**Constraints**: el backend operativo NO recalcula agregaciones (todo desde el warehouse); panel ≤ 8–10 KPIs; gráficos solo con `vue-echarts`; degradación sin error críptico

**Scale/Scope**: ~18 reportes complejos + panel + índice de ~10 reportes simples

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.11.1, §4.11.2, §4.11.3. ✅ |
| II | No aplica (solo lectura analítica). ✅ |
| III | Lee de ClickHouse; el backend operativo no agrega. ✅ |
| IV | Módulo `reportes`; panel para Gerencia General; complejos para gerencia/admin. ✅ |
| V | Backend expone fachada de lectura; frontend solo presenta. ✅ |
| VI | Referencia 012 y los módulos operativos; no los redefine. ✅ |
| VII | Sin librería de gráficos adicional; sin recomputar en el operativo. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | Carga asíncrona; degradación controlada; cobertura de filtros/scope. ✅ |
| X | Módulo `dashboards/` con capas; usa `shared/exportar`. ✅ |
| XI | Filtros reactivos; exportación 3 formatos; drill-down abre flujo real; sello de frescura. ✅ |
| XII | **Todas las pantallas con `ui-ux-pro-max`** y la paleta; acabado profesional. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/dashboards/
├── router.py     # /panel, /reportes/{slug}, /reportes/indice, /reportes/{slug}/exportar
├── service.py    # fachada de lectura sobre ClickHouse; aplica scope; degradación
├── warehouse.py  # cliente ClickHouse (solo lectura) + catálogo de los 18 modelos
├── repository.py
└── schemas.py

frontend/src/dashboards/
├── components/ (PanelGerencia, KpiCard, ReporteAnalitico, GraficoEcharts, IndiceReportes, SelloFrescura)
├── composables/ (usePanel, useReporte, useFrescura)
├── stores/ (dashboardsStore)
└── services/ (dashboardsApi)
```

**Structure Decision**: Un módulo `dashboards`. `warehouse.py` es la única puerta a ClickHouse desde el backend; el catálogo de modelos mapea cada `slug` de reporte a su consulta y su tipo de gráfico. Los reportes simples de §4.11.1 NO se reimplementan: el índice enlaza a los módulos que ya los tienen (003, 007, 008, 010…).

## Complexity Tracking

*Sin violaciones.* El backend actúa como fachada delgada de lectura; toda la agregación está en 012.
