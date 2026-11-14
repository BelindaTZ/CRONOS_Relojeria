# Requirements Quality Checklist: Contabilidad, Gastos, CxC y CxP

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 010.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Se definen todos los libros y estados de §4.10 (diario, mayor, balance, estado de resultados)? [Completeness, Spec §FR-001..§FR-004]
- [x] CHK002 ¿Se define caja/bancos por sucursal con apertura, cierre y arqueo? [Completeness, Spec §FR-005]
- [x] CHK003 ¿Se define el ciclo del cheque (incluido protesto)? [Completeness, Spec §FR-006, §FR-007]
- [x] CHK004 ¿Se definen los subledgers de CxC y CxP y su aging? [Completeness, Spec §FR-008, §FR-009, §FR-010]
- [x] CHK005 ¿Se define el registro **manual** de gastos por sucursal y categoría con soporte? [Completeness, Spec §FR-012]
- [x] CHK005a ¿Se define la elección "pagado ahora" vs. "por pagar" al registrar un gasto y su efecto (movimiento de caja/banco vs. CxP)? [Completeness, Spec §FR-012, §FR-009]
- [x] CHK005b ¿Se define el catálogo de beneficiarios/acreedores de servicios para las CxP que no son de proveedores de mercadería? [Completeness, Spec §FR-009a]
- [x] CHK005c ¿Se define el gasto recurrente (frecuencia, generación de borrador, confirmación, pausa)? [Completeness, Spec §FR-012a]
- [x] CHK006 ¿Se define el motor de asiento automático y sus eventos? [Completeness, Spec §FR-014; research D7]
- [x] CHK007 ¿Se define el cierre de periodo y la inmutabilidad? [Completeness, Spec §FR-016]

## Requirement Clarity

- [x] CHK008 ¿"Compatible con NIIF para PYMES" se traduce en una estructura de plan de cuentas concreta? [Clarity, Spec §FR-001; research D1]
- [x] CHK009 ¿"Asiento descuadrado nunca se guarda" es una regla verificable? [Clarity, Spec §FR-002]
- [x] CHK010 ¿El aging define los tramos exactos? [Clarity, research D5]
- [x] CHK011 ¿"Pérdida extraordinaria separada de los gastos operativos" está definido con cuenta propia? [Clarity, Spec §FR-013; research D7]
- [x] CHK012 ¿"Rentabilidad neta por sucursal" tiene fórmula explícita? [Clarity, Spec §FR-015; research D8]

## Requirement Consistency

- [x] CHK013 ¿Las CxC/CxP consumen los datos generados por 009/008 y 002 de forma consistente? [Consistency, Spec §FR-008, §FR-009]
- [x] CHK013a ¿La CxP originada en un gasto usa el mismo subledger/aging/pagos que la originada en una compra de 002? [Consistency, Spec §FR-009; Data-model cuenta_por_pagar]
- [x] CHK013b ¿El scheduler de gastos recurrentes respeta que solo 000/012 tocan `docker-compose.yml`? [Consistency, Plan Complexity Tracking]
- [x] CHK014 ¿El posteo del costo de mermas es consistente con lo que 011 dispara? [Consistency, Spec §FR-013]
- [x] CHK015 ¿El catálogo `categoria_gasto` y `medio_pago` provienen de 001? [Consistency, Spec §FR-012]
- [x] CHK016 ¿La regla "periodo cerrado no se recalcula por cambio de parámetro" es consistente con la constitución? [Consistency, Spec §FR-016]

## Acceptance Criteria Quality

- [x] CHK017 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-008]
- [x] CHK018 ¿"El balance cuadra en todo momento" es objetivamente verificable? [Measurability, Spec §SC-003]

## Scenario & Edge Case Coverage

- [x] CHK019 ¿Se cubre cobro parcial seguido de cheque protestado? [Edge Case, Spec Edge Cases]
- [x] CHK020 ¿Se cubre la retención mayor que el pago? [Edge Case, Spec Edge Cases]
- [x] CHK021 ¿Se cubre el cambio de categoría de un gasto ya registrado? [Coverage, Spec Edge Cases]
- [x] CHK022 ¿Se cubre un ajuste sobre periodo cerrado y un asiento con fecha en periodo cerrado? [Coverage, Spec Edge Cases]
- [x] CHK023 ¿Se cubre el cierre de caja concurrente? [Edge Case, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK024 ¿El RBAC del módulo `contable` restringe correctamente por rol, incluido que registrar/confirmar gastos y pagar CxP es solo de Gerencia General? [Security, Spec §FR-018]
- [x] CHK025 ¿El scope por sucursal se aplica a todas las consultas? [Security, Spec §FR-017]
- [x] CHK026 ¿Todo asiento/cobro/pago/gasto queda auditado? [Security, Spec §FR-019]
- [x] CHK027 ¿La exportación limita a solo CSV para > 5 000 filas? [Completeness, Spec §FR-020]

## Dependencies & Assumptions

- [x] CHK028 ¿Se documenta que el posteo de mermas lo dispara 011? [Dependency, Spec Assumptions]
- [x] CHK029 ¿Se documenta que SRI y forecasting quedan fuera de alcance? [Assumption, Spec Assumptions]
- [x] CHK030 ¿Se documenta que la nómina se registra como gasto y su cálculo queda fuera? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK031 ¿Está claro que mayor/balance son consultas y no tablas materializadas? [Ambiguity → resuelto: consultas, research D2]
- [x] CHK032 ¿Las CxC de OT a crédito (008) y de ventas (009) usan el mismo subledger? [Ambiguity → resuelto: sí, Data-model + Assumptions]
- [x] CHK033 ¿Se resolvió cómo se registra un gasto de servicio no pagado (agua/wifi)? [Ambiguity → resuelto: gasto "por pagar" → CxP a proveedor o beneficiario libre, decisión del negocio, research D11]
- [x] CHK034 ¿Se resolvió si hay gastos recurrentes? [Ambiguity → resuelto: sí, gasto recurrente configurable, research D12]
