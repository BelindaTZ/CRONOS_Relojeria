# Requirements Quality Checklist: Proveedores y Órdenes de Compra

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 002.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están todos los datos obligatorios del proveedor de §4.2 recogidos en requisitos? [Completeness, Spec §FR-001..§FR-004]
- [x] CHK002 ¿Se define el ciclo completo de una orden de compra (borrador → emitida → parcial → recibida → cancelada)? [Completeness, Data-model; Spec §FR-005, §FR-006]
- [x] CHK003 ¿Están definidas las frecuencias válidas de compra programada y su comportamiento (generación, pausa, cancelación)? [Completeness, Spec §FR-011a]
- [x] CHK004 ¿Se especifica qué campos son editables con rol normal vs. rol elevado en proveedor y en compras recibidas? [Completeness, Spec §FR-011b, §FR-011c]
- [x] CHK005 ¿Se define qué datos de la obligación a pagar registra 002 para que 010 los consuma? [Completeness, Spec §FR-012]
- [x] CHK006 ¿Hay requisitos para capturar lote y caducidad al recibir perecederos? [Completeness, Spec §FR-011d]

## Requirement Clarity

- [x] CHK007 ¿"Retroalimenta automáticamente la calificación" está definido con precisión (qué criterio, cómo se deriva)? [Clarity, Spec §FR-009, §FR-010]
- [x] CHK008 ¿"Rol elevado" está definido (qué roles concretos)? [Clarity, Spec §FR-011b → research D5]
- [x] CHK009 ¿El prellenado de la orden de compra especifica qué parámetros acepta y qué devuelve? [Clarity, Spec §FR-011; Contracts]
- [x] CHK010 ¿Está claro qué es una recepción "parcial" y cuándo la orden pasa a "recibida"? [Clarity, Data-model]

## Requirement Consistency

- [x] CHK011 ¿La responsabilidad "002 registra la obligación, 010 construye la CxP" es consistente en spec y assumptions? [Consistency, Spec §FR-012, Assumptions]
- [x] CHK012 ¿La captura de lote/caducidad es consistente entre 002 (recepción) y 003 (piezas perecederas)? [Consistency, Spec §FR-011d]
- [x] CHK013 ¿El scheduler de compras programadas respeta que solo 000/012 tocan `docker-compose.yml`? [Consistency, Plan Complexity Tracking]

## Acceptance Criteria Quality

- [x] CHK014 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-006]
- [x] CHK015 ¿Hay criterio objetivo para "la orden prellenada llega con los datos puestos"? [Measurability, Spec §SC-004]

## Scenario & Edge Case Coverage

- [x] CHK016 ¿Se cubre recibir más cantidad que la pedida? [Edge Case, Spec Edge Cases]
- [x] CHK017 ¿Se cubre cancelar una orden con recepción parcial? [Edge Case, Spec Edge Cases]
- [x] CHK018 ¿Se cubre el cambio de condiciones de pago con órdenes abiertas? [Edge Case, Spec Edge Cases]
- [x] CHK019 ¿Se cubre la concurrencia en recepciones de la misma orden? [Coverage, Spec Edge Cases]
- [x] CHK020 ¿Se cubre el cálculo del indicador cuando no hubo fecha pactada? [Edge Case, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK021 ¿Se exige búsqueda multi-criterio y minimización de texto libre? [Completeness, Spec §FR-015]
- [x] CHK022 ¿Toda corrección y cambio de calificación/condiciones queda auditado? [Security, Spec §FR-017, §FR-011b]
- [x] CHK023 ¿Se aclara que retenciones no incluyen cálculo fiscal ni SRI en esta fase? [Clarity, Spec §FR-013, Assumptions]

## Dependencies & Assumptions

- [x] CHK024 ¿Se documenta que el alta efectiva en inventario la hace 003? [Dependency, Spec Assumptions]
- [x] CHK025 ¿Se documenta la dependencia del bucket `documentos` (000) para certificados? [Dependency, Spec Assumptions]
- [x] CHK026 ¿Se valida la suposición de que las líneas se validan contra texto controlado hasta que 003 exista? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK027 ¿Queda claro si la recurrencia usa Airflow o un scheduler propio? [Ambiguity → resuelto: scheduler in-proceso, research D1; Airflow es 012]
- [x] CHK028 ¿"Historial de compras" está definido como qué muestra exactamente (órdenes + recepciones)? [Ambiguity, Spec §FR-007]
