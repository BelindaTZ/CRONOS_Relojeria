# Requirements Quality Checklist: Gestión de Citas

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 007.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están todos los datos por cita de §4.1 recogidos como requisito? [Completeness, Spec §FR-001]
- [x] CHK002 ¿Se define el ciclo de estados completo con transiciones válidas y terminales? [Completeness, Data-model; Spec §FR-002]
- [x] CHK003 ¿Se define el comportamiento de "atender" cuando existe y cuando no existe la transacción? [Completeness, Spec §FR-006, §FR-007]
- [x] CHK004 ¿Se define la agenda (día/semana) y su filtro por sucursal? [Completeness, Spec §FR-008]
- [x] CHK005 ¿Se define qué datos se exponen a 014 para recordatorios? [Completeness, Spec §FR-016]

## Requirement Clarity

- [x] CHK006 ¿"Vincularse automáticamente a una venta o a una orden de trabajo generada" está definido como mecanismo concreto? [Clarity, Spec §FR-006; research D2]
- [x] CHK007 ¿"Abre el flujo de creación con el contexto ya cargado" especifica qué contexto? [Clarity, Spec §FR-007]
- [x] CHK008 ¿La advertencia de solape está definida como no bloqueante y con ventana configurable? [Clarity, Spec §FR-017; research D5]
- [x] CHK009 ¿La tasa de conversión operativa tiene fórmula explícita? [Clarity, Spec §FR-010; research D6]

## Requirement Consistency

- [x] CHK010 ¿El vínculo cita↔venta/OT es consistente con lo que 008 y 009 harán al confirmar? [Consistency, research D2]
- [x] CHK011 ¿El canal de origen usa el catálogo de 001 de forma consistente (sin texto libre)? [Consistency, Spec §FR-004]
- [x] CHK012 ¿La exposición de datos a 014 es consistente con que 014 no envía si la cita se canceló? [Consistency, Spec §FR-016; research D7]

## Acceptance Criteria Quality

- [x] CHK013 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-006]
- [x] CHK014 ¿"0 mensajes sin efecto" al atender es objetivamente verificable? [Measurability, Spec §SC-003]

## Scenario & Edge Case Coverage

- [x] CHK015 ¿Se cubren dos citas confirmadas solapadas? [Edge Case, Spec Edge Cases]
- [x] CHK016 ¿Se cubre registrar una cita con fecha en el pasado? [Edge Case, Spec Edge Cases]
- [x] CHK017 ¿Se cubre deshabilitar un canal con citas históricas de ese canal? [Edge Case, Spec Edge Cases]
- [x] CHK018 ¿Se cubre cancelar una cita con OT abierta vinculada? [Edge Case, Spec Edge Cases]
- [x] CHK019 ¿Se cubre la cita para una sucursal distinta a la del vendedor que registra? [Coverage, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK020 ¿Todo cambio de estado queda auditado y en el historial? [Security, Spec §FR-015]
- [x] CHK021 ¿Se aplica el scope por sucursal a listados y agenda? [Consistency, Spec §FR-014]
- [x] CHK022 ¿Hay objetivo de rendimiento para la agenda del día? [Performance, Plan Technical Context]

## Dependencies & Assumptions

- [x] CHK023 ¿Se documenta que el sistema no lee Gmail y la gestión de entrada es manual? [Assumption, Spec Assumptions]
- [x] CHK024 ¿Se documenta que 008/009 completan el vínculo y 014 los recordatorios? [Dependency, Spec Assumptions]
- [x] CHK025 ¿Se documenta que no hay gestión de slots? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK026 ¿Queda claro qué campo de fecha ordena la agenda (preferida vs. confirmada)? [Ambiguity → resuelto: confirmada si existe, si no preferida; research D4]
