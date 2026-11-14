# Requirements Quality Checklist: Plataforma de Datos (ELT)

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 012.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Se define exactamente qué servicios y bucket agrega esta feature al compose? [Completeness, Spec §FR-001, §FR-002]
- [x] CHK002 ¿Se define el flujo ELT con sus cuatro fases y su orden? [Completeness, Spec §FR-003, §FR-005]
- [x] CHK003 ¿Se enumeran los 18 reportes analíticos que el modelo debe soportar? [Completeness, Spec §FR-008]
- [x] CHK004 ¿Se define el mecanismo de incrementalidad (watermark) y de reprocesamiento? [Completeness, Spec §FR-007]
- [x] CHK005 ¿Se define el estado de frescura y quién lo consume? [Completeness, Spec §FR-010]
- [x] CHK006 ¿Se define la frecuencia, el disparo manual y la configurabilidad? [Completeness, Spec §FR-017]
- [x] CHK007 ¿Se define el respaldo del warehouse y de los DAGs? [Completeness, Spec §FR-015]

## Requirement Clarity

- [x] CHK008 ¿"ELT (no ETL)" está definido paso a paso (transformación in-warehouse)? [Clarity, Spec §FR-003]
- [x] CHK009 ¿"`landing-zone` nunca fuente de negocio" es una regla verificable? [Clarity, Spec §FR-004]
- [x] CHK010 ¿"Extracción read-only" está afirmado y verificable? [Clarity, Spec §FR-006]
- [x] CHK011 ¿"Un reintento no duplica datos" está definido con un mecanismo (ReplacingMergeTree / dedup)? [Clarity, Spec §FR-007; research D3]
- [x] CHK012 ¿"La app operativa no depende de estos servicios" es verificable (health de 000 no toca ClickHouse)? [Clarity, Spec §FR-011; research D7]

## Requirement Consistency

- [x] CHK013 ¿El reparto de infraestructura (000 provisiona MinIO, 012 agrega ClickHouse/Airflow/`landing-zone`) es consistente con la constitución? [Consistency, Spec §FR-001, §FR-002]
- [x] CHK014 ¿La lista de reportes coincide con §4.11.2 de la especificación? [Consistency, Spec §FR-008]
- [x] CHK015 ¿El estado de frescura que expone 012 es el que 013 espera? [Consistency, Contracts pipeline-estado]

## Acceptance Criteria Quality

- [x] CHK016 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-007]
- [x] CHK017 ¿"Cada reporte devuelve resultados coherentes con el operativo" es objetivamente verificable? [Measurability, Spec §SC-002]

## Scenario & Edge Case Coverage

- [x] CHK018 ¿Se cubre ClickHouse caído durante una corrida? [Edge Case, Spec Edge Cases]
- [x] CHK019 ¿Se cubren dos corridas solapadas del mismo DAG? [Coverage, Spec Edge Cases]
- [x] CHK020 ¿Se cubre el crecimiento sin límite de `landing-zone` (retención)? [Edge Case, Spec §FR-012]
- [x] CHK021 ¿Se cubre la aparición de tablas/columnas nuevas en el origen? [Coverage, Spec §FR-018]
- [x] CHK022 ¿Se cubren datos con fecha futura / zona horaria distinta? [Edge Case, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK023 ¿Todas las credenciales (Airflow, ClickHouse) provienen de `.env`? [Security, Spec §FR-014]
- [x] CHK024 ¿Hay objetivo de rendimiento para la corrida y para la consulta de un modelo? [Performance, Plan Technical Context]
- [x] CHK025 ¿Se excluye explícitamente forecasting/ML? [Scope, Spec §FR-016]

## Dependencies & Assumptions

- [x] CHK026 ¿Se documenta que 012 puede desarrollarse en paralelo pero necesita datos operativos para validar? [Assumption, Spec Assumptions]
- [x] CHK027 ¿Se documenta que la visualización es responsabilidad de 013? [Dependency, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK028 ¿Se resolvió la frecuencia de actualización? [Ambiguity → resuelto: horaria por defecto, configurable, con disparo manual]
- [x] CHK029 ¿Está claro dónde vive la metadata de Airflow (DB separada, no la operativa)? [Ambiguity → resuelto: DB separada, research D1]
