# Requirements Quality Checklist: Inventario de Relojes y Piezas

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 003.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están todos los campos de la ficha de §4.4 recogidos como requisito? [Completeness, Spec §FR-002]
- [x] CHK002 ¿Se define el conjunto de tipos de evento del historial de serie? [Completeness, Data-model evento_serie; Spec §FR-005]
- [x] CHK003 ¿Se especifica el comportamiento completo de piezas perecederas (marca, lote, caducidad, alerta, consumo, merma)? [Completeness, Spec §FR-006a]
- [x] CHK004 ¿Están definidos los tres tipos de alerta de stock y sus umbrales configurables? [Completeness, Spec §FR-010, §FR-011, §FR-012]
- [x] CHK005 ¿Se define qué reportes operativos entrega la feature y cuáles quedan para 013? [Completeness, Spec §FR-008, §FR-009, §FR-017]
- [x] CHK006 ¿Se especifica quién puede corregir el número de serie y con qué controles? [Completeness, Spec §FR-016a]

## Requirement Clarity

- [x] CHK007 ¿"El stock nunca queda negativo" está definido como invariante verificable (no como aspiración)? [Clarity, Spec §FR-015]
- [x] CHK008 ¿"Historial inalterable" se traduce en una regla concreta (append-only, sin endpoint de edición)? [Clarity, Spec §FR-005]
- [x] CHK009 ¿Está cuantificado "cerca del máximo" / "última unidad" / "bajo mínimo"? [Clarity, Spec §FR-012; research D5]
- [x] CHK010 ¿"Restringir información financiera sensible" se define con un permiso concreto? [Clarity, Spec §FR-019; research D9]
- [x] CHK011 ¿"Servida directo a la app" vs. papeles "vía endpoint autenticado" está claro por tipo de archivo? [Clarity, Spec §FR-004, Assumptions]

## Requirement Consistency

- [x] CHK012 ¿El origen de una unidad (recepción de compra de 002) es consistente entre spec y data-model? [Consistency, Spec §FR-003]
- [x] CHK013 ¿La alerta "Reponer" invoca exactamente el contrato de prellenado de 002? [Consistency, Spec §FR-013; Contracts]
- [x] CHK014 ¿El manejo de caducidad es consistente con la causa de merma "insumo caducado" de 011? [Consistency, Spec §FR-006a]
- [x] CHK015 ¿"Calibre lo crea 003, la ficha de lubricación 008" es consistente en spec y assumptions? [Consistency, Spec Assumptions]

## Acceptance Criteria Quality

- [x] CHK016 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-007]
- [x] CHK017 ¿"En 0 casos el stock queda negativo (pruebas de concurrencia)" es objetivamente verificable? [Measurability, Spec §SC-007]

## Scenario & Edge Case Coverage

- [x] CHK018 ¿Se cubre el alta sin recepción de compra asociada? [Edge Case, Spec Edge Cases]
- [x] CHK019 ¿Se cubre la subida de foto fallida a mitad? [Edge Case, Spec Edge Cases]
- [x] CHK020 ¿Se cubren dos ventas simultáneas sobre la última unidad? [Coverage, Spec Edge Cases]
- [x] CHK021 ¿Se cubre reducir el stock máximo por debajo del stock actual? [Edge Case, Spec Edge Cases]
- [x] CHK022 ¿Se cubre el reingreso de un bien (desde 011) y su efecto en las alertas? [Coverage, Spec §FR-014]

## Non-Functional Requirements

- [x] CHK023 ¿Se exige búsqueda multi-criterio para relojes y piezas? [Completeness, Spec §FR-020]
- [x] CHK024 ¿Los cambios de costo/precio y las correcciones de serie quedan auditados? [Security, Spec §FR-016, §FR-016a]
- [x] CHK025 ¿Hay objetivo de rendimiento para el estado de inventario? [Performance, Plan Technical Context]

## Dependencies & Assumptions

- [x] CHK026 ¿Se documenta que el historial de servicios lo puebla 008, transferencias 004, venta 009, baja 011? [Dependency, Spec Assumptions]
- [x] CHK027 ¿Se documenta la dependencia de parámetros de 001 (stock máximo, umbrales)? [Dependency, Spec §FR-010, §FR-011]

## Ambiguities & Conflicts

- [x] CHK028 ¿Se resolvió si se normaliza `modelo` o se guarda por unidad? [Ambiguity → resuelto: por unidad, research D1]
- [x] CHK029 ¿Está claro el orden de consumo de lotes (FEFO)? [Ambiguity → resuelto: FEFO, research D4]
