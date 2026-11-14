# Requirements Quality Checklist: Servicio Técnico y Lubricación

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 008.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están todos los datos de la OT de §4.7 recogidos? [Completeness, Spec §FR-001..§FR-018]
- [x] CHK002 ¿Se define la ficha de lubricación por calibre (§4.6) y el registro por punto (recomendado vs. usado)? [Completeness, Spec §FR-005, §FR-007]
- [x] CHK003 ¿Se define el paso de presupuesto y la elección de piezas originales/no originales? [Completeness, Spec §FR-003b, §FR-003c]
- [x] CHK004 ¿Se define el cobro al retiro y la condición para pasar a `entregado`? [Completeness, Spec §FR-016a]
- [x] CHK005 ¿Se define la generación del documento de OT y el certificado de garantía? [Completeness, Spec §FR-019]
- [x] CHK006 ¿Se define el informe de servicios/arreglos y sus columnas? [Completeness, Spec §FR-023a]
- [x] CHK007 ¿Se define la reapertura por garantía? [Completeness, Spec §FR-020]

## Requirement Clarity

- [x] CHK008 ¿La fórmula del costo interno y del margen real está explícita? [Clarity, Spec §FR-010, §FR-013; research D3]
- [x] CHK009 ¿"Fecha estimada solo tras diagnóstico" es una regla verificable (estado concreto)? [Clarity, Spec §FR-016]
- [x] CHK010 ¿"En reparación requiere presupuesto aprobado" está definido como guarda? [Clarity, Spec §FR-003d]
- [x] CHK011 ¿El costeo de MO por tarifa horaria consume el contrato de 005 sin recalcularlo? [Clarity, Spec §FR-004a; research D3]
- [x] CHK012 ¿"Sin pago no se entrega" define la excepción (crédito autorizado → CxC)? [Clarity, Spec §FR-016a]

## Requirement Consistency

- [x] CHK013 ¿La aplicación de descuento usa el servicio compartido de 006 con margen mínimo? [Consistency, Spec §FR-014]
- [x] CHK014 ¿El registro de pagos multimedios es el helper `shared/pagos` que también usa 009? [Consistency, Spec §FR-016b]
- [x] CHK015 ¿El PDF va a `comprobantes-venta` de forma consistente con Const. Ppio III y 009? [Consistency, Spec §FR-019]
- [x] CHK016 ¿La derivación a merma usa la causa `dano_servicio` consistente con 011? [Consistency, Spec §FR-021]
- [x] CHK017 ¿El consumo de insumos de lubricación descuenta del stock de piezas (003, perecederas)? [Consistency, Spec §FR-009; research D5]

## Acceptance Criteria Quality

- [x] CHK018 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-008]
- [x] CHK019 ¿"El margen real coincide con la fórmula en el 100% de casos de prueba" es verificable? [Measurability, Spec §SC-002]

## Scenario & Edge Case Coverage

- [x] CHK020 ¿Se cubre cambiar el técnico a mitad de la OT (prorrateo de MO)? [Edge Case, Spec Edge Cases]
- [x] CHK021 ¿Se cubre una pieza sin stock al confirmarla? [Coverage, Spec Edge Cases]
- [x] CHK022 ¿Se cubre la OT reabierta por garantía (¿se cobra?)? [Edge Case, Spec Edge Cases]
- [x] CHK023 ¿Se cubre el calibre sin ficha de lubricación? [Edge Case, Spec Edge Cases]
- [x] CHK024 ¿Se cubre el reloj `en_transito` al abrir la OT? [Coverage, Spec Edge Cases]
- [x] CHK025 ¿Se cubre el precio manual con margen negativo? [Edge Case, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK026 ¿Se exige cobertura de pruebas del margen del servicio y del margen mínimo (críticos)? [Testing, Spec §SC-002, §SC-003; Const. Ppio IX]
- [x] CHK027 ¿El costo/margen nunca aparece en el documento del cliente? [Security, Spec §FR-026]
- [x] CHK028 ¿El técnico solo puede editar sus propias OT? [Security, Spec §FR-025]
- [x] CHK029 ¿La generación de PDF es asíncrona y no bloquea? [Performance, Plan Technical Context]

## Dependencies & Assumptions

- [x] CHK030 ¿Se documenta que `shared/pdf` y `shared/pagos` los introduce esta feature y los reutiliza 009? [Dependency, Spec Assumptions]
- [x] CHK031 ¿Se documenta que la aprobación del presupuesto ocurre fuera del sistema (solo se registra el resultado)? [Assumption, Spec Assumptions]
- [x] CHK032 ¿Se documenta la política de datos históricos para "adquirido en la tienda"? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK033 ¿Se resolvió cuándo se ingresa la fecha estimada? [Ambiguity → resuelto: al aprobar presupuesto]
- [x] CHK034 ¿Se resolvió cómo se maneja el cobro? [Ambiguity → resuelto: al retiro; sin pago no se entrega]
- [x] CHK035 ¿Se resolvió dónde se genera el documento de OT (008 vs 009)? [Ambiguity → resuelto: 008 lo genera con `shared/pdf`]
