# Requirements Quality Checklist: Clientes, Fidelización y Descuentos

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 006.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están todos los datos de la ficha de cliente de §4.8, más número de afiliado y consentimiento? [Completeness, Spec §FR-001, §FR-001a, §FR-001b]
- [x] CHK002 ¿Se define el modelo de niveles (nombre, criterio, umbrales, beneficios, base)? [Completeness, Spec §FR-004]
- [x] CHK003 ¿Se define cuándo se recalcula el nivel individual y cuándo el masivo? [Completeness, Spec §FR-005, §FR-025; research D4]
- [x] CHK004 ¿Están completos los datos de un descuento general y de un cupón (§4.8.2)? [Completeness, Spec §FR-008, §FR-009]
- [x] CHK005 ¿Se define el servicio de margen mínimo con sus tres decisiones (permitir/bloquear/autorizar)? [Completeness, Spec §FR-011, §FR-012]
- [x] CHK006 ¿Se define qué reportes operativos entrega la feature? [Completeness, Spec §FR-017, §FR-018, §FR-019]

## Requirement Clarity

- [x] CHK007 ¿El criterio del nivel (monto/frecuencia/combinación y ventana) está cuantificado? [Clarity, Spec §FR-004; research D3]
- [x] CHK008 ¿"Margen mínimo" está definido por ámbito y con precedencia (producto→marca→global)? [Clarity, Spec §FR-010; research D5]
- [x] CHK009 ¿"Mutuamente excluyentes" descuento/cupón es una regla verificable (422)? [Clarity, Spec §FR-015]
- [x] CHK010 ¿"Se valida siempre en backend" está afirmado explícitamente para nivel y margen? [Clarity, Spec §FR-022]
- [x] CHK011 ¿"Consumidor final" está definido (fila genérica, sin fidelización, solo piezas bajo un monto)? [Clarity, research D9]

## Requirement Consistency

- [x] CHK012 ¿El recálculo de nivel es consistente con la regla de la constitución (cascada, historial conservado)? [Consistency, Spec §FR-025]
- [x] CHK013 ¿La aplicación de descuento es consistente entre 006 (servicio) y sus consumidores 008/009? [Consistency, Contracts /_internal/descuentos/aplicar]
- [x] CHK014 ¿`aplicacion_descuento` y `autorizacion_margen_minimo` se registran en la venta/OT de forma consistente con 008/009? [Consistency, Data-model]

## Acceptance Criteria Quality

- [x] CHK015 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-007]
- [x] CHK016 ¿"El motor de nivel clasifica correctamente un set de clientes de prueba" es verificable con fixtures? [Measurability, Spec §SC-003]
- [x] CHK017 ¿El criterio del margen mínimo (bloqueo salvo autorización) es objetivamente testeable? [Measurability, Spec §SC-004]

## Scenario & Edge Case Coverage

- [x] CHK018 ¿Se cubre el cambio de umbrales con muchos clientes clasificados? [Edge Case, Spec Edge Cases]
- [x] CHK019 ¿Se cubre el margen resultante exactamente en el mínimo? [Edge Case, Spec Edge Cases]
- [x] CHK020 ¿Se cubre la concurrencia sobre un cupón de uso único? [Coverage, Spec Edge Cases; research D6]
- [x] CHK021 ¿Se cubre el cliente jurídico sin fecha de nacimiento para el cupón de cumpleaños? [Edge Case, Spec Edge Cases]
- [x] CHK022 ¿Se cubre eliminar un nivel con clientes asignados? [Edge Case, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK023 ¿Se exige cobertura de pruebas de nivel y margen mínimo (módulos críticos)? [Testing, Spec §SC-003, §SC-004; Const. Ppio IX]
- [x] CHK024 ¿La autorización de margen mínimo queda auditada con quién/cuándo/qué? [Security, Spec §FR-013]
- [x] CHK025 ¿El consentimiento LOPDP se registra con fecha y versión? [Compliance, Spec §FR-001b]

## Dependencies & Assumptions

- [x] CHK026 ¿Se documenta que 008/009 disparan el recálculo y la aplicación, validados con fixtures hasta entonces? [Dependency, Spec Assumptions]
- [x] CHK027 ¿Se documenta que las campañas de email son de 014? [Dependency, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK028 ¿Se resolvió si descuento+cupón se acumulan? [Ambiguity → resuelto: NO, decisión del negocio, Spec §FR-015]
- [x] CHK029 ¿Se resolvió la reclasificación al cambiar umbrales? [Ambiguity → resuelto: recálculo masivo, decisión del negocio]
- [x] CHK030 ¿Se resolvió la venta a consumidor final? [Ambiguity → resuelto: solo piezas bajo un monto, decisión del negocio → detalle en 009]
