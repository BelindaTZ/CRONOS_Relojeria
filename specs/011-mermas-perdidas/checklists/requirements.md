# Requirements Quality Checklist: Mermas y Pérdidas

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 011.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están todos los datos por merma de §4.12, incluida la causa `insumo_caducado`? [Completeness, Spec §FR-001]
- [x] CHK002 ¿Se define el ciclo de estados completo? [Completeness, Data-model; Spec §FR-003]
- [x] CHK003 ¿Se define el umbral de autorización y su efecto en la transición a baja? [Completeness, Spec §FR-005, §FR-006]
- [x] CHK004 ¿Se define el efecto de la baja sobre inventario y contabilidad? [Completeness, Spec §FR-007, §FR-008]
- [x] CHK005 ¿Se define el reingreso ("reparado y reingresado")? [Completeness, Spec §FR-011]
- [x] CHK006 ¿Se definen los reclamos a proveedor y seguro? [Completeness, Spec §FR-012]
- [x] CHK007 ¿Se define el reporte de mermas y sus dimensiones? [Completeness, Spec §FR-013]

## Requirement Clarity

- [x] CHK008 ¿"A costo de adquisición" está definido para reloj, pieza y lote? [Clarity, Spec §FR-002; research D1]
- [x] CHK009 ¿"Umbral configurable" indica que es un parámetro y quién autoriza? [Clarity, Spec §FR-005, §FR-006]
- [x] CHK010 ¿"Retiro del inventario activo conservando historial" es verificable? [Clarity, Spec §FR-007]
- [x] CHK011 ¿"Pérdida extraordinaria separada" define una cuenta contable propia? [Clarity, Spec §FR-008; research D4]
- [x] CHK012 ¿"Sin sanción automática" para el técnico está afirmado? [Clarity, Spec §FR-009]

## Requirement Consistency

- [x] CHK013 ¿La causa `dano_servicio` es consistente con lo que 008 dispara? [Consistency, Spec §FR-009]
- [x] CHK014 ¿La causa `dano_transito` es consistente con lo que 004 dispara? [Consistency, Spec §FR-010]
- [x] CHK015 ¿La causa `insumo_caducado` es consistente con las alertas de lote de 003? [Consistency, Spec §FR-001a]
- [x] CHK016 ¿El asiento de baja usa la API de 010 de forma consistente? [Consistency, Spec §FR-008]
- [x] CHK017 ¿Los adjuntos van al bucket `documentos` provisionado por 000? [Consistency, Spec §FR-004]

## Acceptance Criteria Quality

- [x] CHK018 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-008]
- [x] CHK019 ¿"El bien dado de baja conserva su historial completo" es objetivamente verificable? [Measurability, Spec §SC-004]

## Scenario & Edge Case Coverage

- [x] CHK020 ¿Se cubre el costo exactamente en el umbral? [Edge Case, Spec Edge Cases]
- [x] CHK021 ¿Se cubre el proveedor que no repone en reclamo? [Coverage, Spec Edge Cases]
- [x] CHK022 ¿Se cubre el reingreso de un bien cuyo modelo ya superó el stock máximo? [Edge Case, Spec Edge Cases]
- [x] CHK023 ¿Se cubre autorizar una baja sin el permiso correspondiente? [Coverage, Spec Edge Cases]
- [x] CHK024 ¿Se cubre intentar merma sobre un bien vendido / dado de baja? [Coverage, Spec §FR-018]

## Non-Functional Requirements

- [x] CHK025 ¿Se exige cobertura de pruebas del registro/costeo de mermas (módulo crítico)? [Testing, Spec §SC-008; Const. Ppio IX]
- [x] CHK026 ¿El `costo_perdida` está restringido a rol administrativo? [Security, Spec Data-model]
- [x] CHK027 ¿Todo cambio de estado y autorización queda auditado? [Security, Spec §FR-017]
- [x] CHK028 ¿Se aplica el scope por sucursal? [Security, Spec §FR-014]

## Dependencies & Assumptions

- [x] CHK029 ¿Se documenta que el asiento se genera vía la API de 010? [Dependency, Spec Assumptions]
- [x] CHK030 ¿Se documenta que los reclamos son solo seguimiento de estado, sin integración externa? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK031 ¿Se resolvió dónde se guardan los documentos de soporte? [Ambiguity → resuelto: bucket `documentos`]
- [x] CHK032 ¿Se resolvió si "insumo caducado" es causa de merma? [Ambiguity → resuelto: sí, decisión del negocio]
