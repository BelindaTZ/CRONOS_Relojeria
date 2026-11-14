# Requirements Quality Checklist: Técnicos y Productividad

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 005.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están todos los datos de la ficha de técnico de §4.3 recogidos? [Completeness, Spec §FR-001, §FR-002]
- [x] CHK002 ¿Se define el método de costeo de mano de obra por OT de forma completa (tarifa, base de horas, fallback)? [Completeness, Spec §FR-004]
- [x] CHK003 ¿Están definidos los 4 indicadores del bono y su cálculo? [Completeness, Spec §FR-005; research D4]
- [x] CHK004 ¿Se define qué tipos de componente de bono existen (monto fijo, % margen, combinación)? [Completeness, Spec §FR-006]
- [x] CHK005 ¿Se especifica el prorrateo del bono entre OT cerradas? [Completeness, Spec §FR-004a; research D2]
- [x] CHK006 ¿Se define la vista operativa de productividad y sus columnas? [Completeness, Spec §FR-012]

## Requirement Clarity

- [x] CHK007 ¿"Tarifa horaria" está definida con su denominador (horas productivas estándar) como parámetro? [Clarity, Spec §FR-004; research D1]
- [x] CHK008 ¿"El bono nunca es negativo" es una regla verificable? [Clarity, Spec §FR-010]
- [x] CHK009 ¿Está claro qué es un "periodo abierto" vs. "cerrado" para el recálculo? [Clarity, Spec §FR-011; research D5]
- [x] CHK010 ¿"Restringir a roles administrativos" se define con un permiso concreto? [Clarity, Spec §FR-014]
- [x] CHK011 ¿"El técnico puede editar solo datos de contacto" delimita exactamente los campos? [Clarity, Spec §FR-017a]

## Requirement Consistency

- [x] CHK012 ¿El costeo de MO por OT es consistente entre 005 (contrato) y 008 (consumidor)? [Consistency, Spec §FR-004; Contracts /_internal/costeo]
- [x] CHK013 ¿La regla de recálculo del bono es consistente con la de la constitución? [Consistency, Spec §FR-011]
- [x] CHK014 ¿El vínculo técnico↔usuario y el autoservicio son consistentes con 001? [Consistency, Spec §FR-002, §FR-017a]

## Acceptance Criteria Quality

- [x] CHK015 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-006]
- [x] CHK016 ¿"El motor de bono produce el mismo resultado que un cálculo manual" es objetivamente verificable con fixtures? [Measurability, Spec §SC-002]

## Scenario & Edge Case Coverage

- [x] CHK017 ¿Se cubre el cambio de fórmula a mitad de un periodo abierto? [Edge Case, Spec Edge Cases]
- [x] CHK018 ¿Se cubre el técnico en varias sucursales (atribución de OT y costo)? [Edge Case, Spec Edge Cases]
- [x] CHK019 ¿Se cubre el reproceso sobre el mismo reloj (indicador de calidad)? [Coverage, Spec Edge Cases, research D4]
- [x] CHK020 ¿Se cubre el técnico desactivado con bono pendiente? [Edge Case, Spec Edge Cases]
- [x] CHK021 ¿Se cubre el periodo sin OT / OT sin fecha de cierre? [Coverage, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK022 ¿Se exige cobertura de pruebas del cálculo de bono (módulo crítico)? [Testing, Spec §SC-002; Const. Ppio IX]
- [x] CHK023 ¿El cálculo se ejecuta siempre en backend, nunca en frontend? [Security, Const. Ppio V]
- [x] CHK024 ¿El costo/bono nunca aparece en documentos del cliente? [Security, Spec §FR-009]

## Dependencies & Assumptions

- [x] CHK025 ¿Se documenta que la acumulación "en vivo" se activa con 008 y hasta entonces se valida con fixtures? [Dependency, Spec Assumptions]
- [x] CHK026 ¿Se documenta la dependencia del parámetro `horas_productivas_estandar_mes` de 001? [Dependency, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK027 ¿Se resolvió la base de prorrateo del sueldo? [Ambiguity → resuelto: tarifa horaria, decisión del negocio, research D1]
- [x] CHK028 ¿"e inactivar no?" del spec original se resolvió (el técnico NO puede inactivarse)? [Ambiguity → resuelto, Spec §FR-017]
