# Requirements Quality Checklist: Ventas, Comprobantes y Garantías

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 009.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Se define la orden de venta con líneas de reloj y de pieza y su ciclo (borrador/confirmada/anulada)? [Completeness, Data-model; Spec §FR-001, §FR-012]
- [x] CHK002 ¿Se define qué ocurre exactamente al confirmar (stock, evento de serie, pagos, CxC, PDFs, nivel, cita)? [Completeness, Spec §FR-002, §FR-006, §FR-008, §FR-010, §FR-011]
- [x] CHK003 ¿Se definen las dos garantías (fábrica y tienda) por transacción con periodos configurables? [Completeness, Spec §FR-007]
- [x] CHK004 ¿Se define la anulación con todas sus reversas? [Completeness, Spec §FR-012]
- [x] CHK005 ¿Se define el caso "consumidor final" y sus límites? [Completeness, Spec §FR-022; research D8]

## Requirement Clarity

- [x] CHK006 ¿La fórmula del margen de la venta está explícita (precio final − costo)? [Clarity, Spec §FR-004; research D2]
- [x] CHK007 ¿"Un descuento o un cupón" está definido como regla verificable (422 si ambos)? [Clarity, Spec §FR-003]
- [x] CHK008 ¿"Sin pasarela de pago en línea" y multimedios está claro? [Clarity, Spec §FR-005]
- [x] CHK009 ¿"Compatible con SRI" enumera los campos necesarios sin exigir transmisión? [Clarity, Spec §FR-021; research D6]

## Requirement Consistency

- [x] CHK010 ¿La aplicación de descuento usa el mismo servicio de 006 que 008? [Consistency, Spec §FR-003]
- [x] CHK011 ¿El PDF usa `shared/pdf` de 008 y va a `comprobantes-venta`? [Consistency, Spec §FR-008]
- [x] CHK012 ¿Los pagos usan `shared/pagos` de 008? [Consistency, Spec §FR-005]
- [x] CHK013 ¿La CxC generada aquí es consistente con el subledger/aging de 010? [Consistency, Data-model cuenta_por_cobrar]
- [x] CHK014 ¿El recálculo de nivel invoca el endpoint de 006? [Consistency, Spec §FR-010]

## Acceptance Criteria Quality

- [x] CHK015 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-008]
- [x] CHK016 ¿"El margen coincide con la fórmula en el 100% de casos de prueba" es verificable? [Measurability, Spec §SC-003]

## Scenario & Edge Case Coverage

- [x] CHK017 ¿Se cubre la venta concurrente de la última unidad? [Coverage, Spec Edge Cases]
- [x] CHK018 ¿Se cubre el cheque que rebota (delegado a 010)? [Coverage, Spec Edge Cases]
- [x] CHK019 ¿Se cubre el certificado de una unidad sin foto? [Edge Case, Spec Edge Cases]
- [x] CHK020 ¿Se cubre anular una venta que ya subió el nivel de fidelización? [Coverage, Spec Edge Cases]
- [x] CHK021 ¿Se cubre la venta a consumidor final que supera el monto? [Edge Case, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK022 ¿Se exige cobertura de pruebas del margen de venta y del margen mínimo (críticos)? [Testing, Spec §SC-003, §SC-004; Const. Ppio IX]
- [x] CHK023 ¿Los comprobantes solo son accesibles autenticados y sin costos/márgenes? [Security, Spec §FR-008, §FR-009]
- [x] CHK024 ¿Cambios de precio y anulaciones quedan auditados? [Security, Spec §FR-015]

## Dependencies & Assumptions

- [x] CHK025 ¿Se documenta la reutilización de `shared/pdf`, `shared/pagos` (008), `shared/descuentos` (006), `medio_pago` (001)? [Dependency, Spec Assumptions]
- [x] CHK026 ¿Se documenta que el subledger/aging de CxC es de 010? [Dependency, Spec Assumptions]
- [x] CHK027 ¿Se documenta que el SRI queda fuera de alcance (modelo compatible)? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK028 ¿Se resolvió la venta a consumidor final? [Ambiguity → resuelto: solo piezas bajo un monto, decisión del negocio]
- [x] CHK029 ¿Se resolvió que la venta absorbe "ventas" (la ex-010)? [Consistency → Const. "Flujo de Trabajo" 009]
