# Requirements Quality Checklist: Multi-Sucursal y Traslados

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 004.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Está definida la máquina de estados completa de la transferencia? [Completeness, Data-model; Spec §FR-002, §FR-003, §FR-007]
- [x] CHK002 ¿Se especifica el efecto exacto sobre relojes y sobre stock de piezas al enviar y al recibir? [Completeness, Spec §FR-002, §FR-003]
- [x] CHK003 ¿Se define el manejo de discrepancia y su derivación a merma? [Completeness, Spec §FR-004]
- [x] CHK004 ¿Se define qué muestra el historial de transferencias (por serie y por sucursal)? [Completeness, Spec §FR-005, §FR-006]
- [x] CHK005 ¿Se especifica el comportamiento con una sola sucursal activa? [Completeness, Spec §FR-013]

## Requirement Clarity

- [x] CHK006 ¿"Fuera de disponibilidad en origen" está definido de forma verificable (estado concreto)? [Clarity, Spec §FR-002]
- [x] CHK007 ¿"Actualización automática del inventario en ambas sucursales" está definido paso a paso? [Clarity, Spec §FR-003]
- [x] CHK008 ¿Está claro que un ítem en tránsito no cuenta para el stock de ninguna sucursal? [Clarity, research D4]
- [x] CHK009 ¿"Scoping por sucursal" reutiliza el helper de 001 y no una implementación nueva? [Clarity, Spec §FR-008; research D5]

## Requirement Consistency

- [x] CHK010 ¿La derivación a merma usa la causa `dano_transito` consistente con 011? [Consistency, Spec §FR-004]
- [x] CHK011 ¿El rechazo de venta/OT de un ítem en tránsito es consistente con 008 y 009? [Consistency, research D4]
- [x] CHK012 ¿El evento de transferencia en el historial de serie es consistente con el modelo de 003? [Consistency, Data-model]

## Acceptance Criteria Quality

- [x] CHK013 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-006]
- [x] CHK014 ¿"El inventario de ambas sucursales queda correcto sin ajuste manual" es objetivamente verificable? [Measurability, Spec §SC-001]

## Scenario & Edge Case Coverage

- [x] CHK015 ¿Se cubre la recepción parcial con faltante que nunca llega? [Edge Case, Spec Edge Cases]
- [x] CHK016 ¿Se cubre intentar vender un ítem en tránsito desde el destino? [Edge Case, Spec Edge Cases]
- [x] CHK017 ¿Se cubre la doble confirmación de recepción concurrente? [Coverage, research D7]
- [x] CHK018 ¿Se cubre la inactivación de la sucursal destino con una transferencia en tránsito? [Edge Case, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK019 ¿Todos los cambios de estado quedan auditados? [Security, Spec §FR-012]
- [x] CHK020 ¿Hay objetivo de rendimiento para registrar/confirmar? [Performance, Plan Technical Context]
- [x] CHK021 ¿Se exigen filtros reactivos, paginación y exportación? [Completeness, Spec §FR-006, §FR-014]

## Dependencies & Assumptions

- [x] CHK022 ¿Se documenta que caja/gastos por sucursal son de 010 y técnicos de 005? [Dependency, Spec Assumptions]
- [x] CHK023 ¿Se documenta que la logística física queda fuera del sistema? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK024 ¿Se resolvió si el stock se mueve al enviar o al recibir? [Ambiguity → resuelto: sale al enviar, entra al recibir; research D2]
- [x] CHK025 ¿Está claro qué pasa con el faltante (no reingresa hasta resolver)? [Ambiguity → resuelto, research D3]
