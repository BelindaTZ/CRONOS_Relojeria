# Requirements Quality Checklist: Dashboards y Reportes

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 013.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Se enumeran los 5–6 KPIs del panel principal? [Completeness, Spec §FR-001; research D1]
- [x] CHK002 ¿Se cubre el acceso a los 18 reportes de §4.11.2? [Completeness, Spec §FR-003; research D3]
- [x] CHK003 ¿Se define el índice de reportes simples y qué incluye (incl. informe de servicios de 008)? [Completeness, Spec §FR-010]
- [x] CHK004 ¿Se define la exportación (formatos, límite de filas)? [Completeness, Spec §FR-009]
- [x] CHK005 ¿Se define el sello de frescura y el "actualizar ahora"? [Completeness, Spec §FR-007]
- [x] CHK006 ¿Se define la degradación cuando el warehouse no está disponible? [Completeness, Spec §FR-008]

## Requirement Clarity

- [x] CHK007 ¿El tipo de gráfico por tipo de dato está especificado (barras/pastel/líneas/KPI/tabla)? [Clarity, Spec §FR-005; research D3]
- [x] CHK008 ¿"Carga asíncrona que no bloquea" es verificable (KPIs independientes)? [Clarity, Spec §FR-006; research D2]
- [x] CHK009 ¿"Drill-down abre el flujo real" está definido con destino y contexto? [Clarity, Spec §FR-015; research D8]
- [x] CHK010 ¿"Panel ≤ 8–10 KPIs" es una regla verificable? [Clarity, Spec §FR-002]
- [x] CHK011 ¿"El backend operativo no recalcula agregaciones" está afirmado? [Clarity, Spec §FR-016]

## Requirement Consistency

- [x] CHK012 ¿La lista de reportes analíticos coincide con §4.11.2 y con el warehouse de 012? [Consistency, Spec §FR-003]
- [x] CHK013 ¿El sello de frescura consume el contrato de 012 de forma consistente? [Consistency, research D5; Contracts 012]
- [x] CHK014 ¿Los reportes simples enlazan a sus módulos y no se reimplementan? [Consistency, Spec §FR-010; research D7]
- [x] CHK015 ¿La exportación usa `shared/exportar.js` (constitución)? [Consistency, Spec §FR-009]

## Acceptance Criteria Quality

- [x] CHK016 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-007]
- [x] CHK017 ¿"El 100% de las acciones recomendadas abre el flujo real" es verificable? [Measurability, Spec §SC-007]

## Scenario & Edge Case Coverage

- [x] CHK018 ¿Se cubre el warehouse vacío (primera corrida no ejecutada)? [Edge Case, Spec Edge Cases]
- [x] CHK019 ¿Se cubre un reporte con cero resultados para el filtro? [Coverage, Spec Edge Cases]
- [x] CHK020 ¿Se cubre un periodo muy amplio (rendimiento)? [Edge Case, Spec Edge Cases]
- [x] CHK021 ¿Se cubre un gerente de sucursal abriendo un reporte consolidado? [Coverage, Spec Edge Cases]
- [x] CHK022 ¿Se cubre exportar a PDF un reporte con gráfico? [Edge Case, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK023 ¿Hay objetivo de rendimiento para el panel y para un reporte con filtros? [Performance, Plan Technical Context]
- [x] CHK024 ¿El scope por sucursal se aplica a todos los reportes? [Security, Spec §FR-012]
- [x] CHK025 ¿Todas las pantallas se construyen con `ui-ux-pro-max` y la paleta? [Design, Spec §FR-014; Const. Ppio XII]

## Dependencies & Assumptions

- [x] CHK026 ¿Se documenta la dependencia de 012 (warehouse poblado + estado de frescura)? [Dependency, Spec Assumptions]
- [x] CHK027 ¿Se documenta que los reportes simples ya existen en sus módulos? [Assumption, Spec Assumptions]
- [x] CHK028 ¿Se documenta que no hay forecasting ni proyecciones? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK029 ¿Está claro que el número/definición fina de reportes complejos puede ajustarse manteniendo §4.11.2 como cobertura mínima? [Ambiguity → resuelto, Spec Assumptions]
- [x] CHK030 ¿Está claro que "actualizar ahora" es una acción real (llama a 012)? [Ambiguity → resuelto, research D5]
