# Business Rules Quality Checklist: Fidelización y Margen Mínimo

**Purpose**: Checklist adicional para las dos reglas de negocio críticas de la feature 006 (cálculo de nivel de fidelización y margen mínimo protegido), que tienen cobertura de pruebas obligatoria por Const. Ppio IX.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Nivel de fidelización — Completitud de la regla

- [x] BR001 ¿Se especifica la ventana temporal considerada para monto/frecuencia? [Completeness, research D3]
- [x] BR002 ¿Se define qué transacciones cuentan (compras 009 + servicios 008; ¿netas de devoluciones?)? [Gap, Spec §FR-005]
- [x] BR003 ¿Se define el nivel resultante cuando un cliente cumple varios niveles (el de mayor orden)? [Clarity, research D3]
- [x] BR004 ¿Se define el comportamiento al bajar de nivel (¿se permite descenso? ¿inmediato o con gracia?)? [Gap]
- [x] BR005 ¿El historial de nivel registra el hecho disparador y el documento origen? [Completeness, Data-model historial_nivel_cliente]
- [x] BR006 ¿Se define qué pasa con una venta anulada que había subido el nivel (009 revierte)? [Consistency, Spec §FR-012 de 009]

## Nivel de fidelización — Medibilidad

- [x] BR007 ¿Se puede verificar el nivel calculado contra un cálculo manual sobre fixtures? [Measurability, Spec §SC-003]
- [x] BR008 ¿El recálculo masivo tras cambio de umbral es determinista y auditable? [Measurability, Spec §FR-025]

## Margen mínimo protegido — Completitud de la regla

- [x] BR009 ¿Se define la base del margen (sobre costo de adquisición; ¿incluye mano de obra e insumos para servicio?)? [Clarity, Esp. §4.8.2, §5]
- [x] BR010 ¿Se define la precedencia de ámbitos (producto → marca → global)? [Completeness, research D5]
- [x] BR011 ¿Se define cuándo es "bloquear" y cuándo "requiere_autorizacion" (política configurable)? [Clarity, Spec §FR-012]
- [x] BR012 ¿Se define qué rol puede autorizar y qué queda registrado (quién, cuándo, sobre qué operación, margen resultante, motivo)? [Completeness, Spec §FR-013]
- [x] BR013 ¿Se define el comportamiento con margen resultante == mínimo (¿permite?)? [Edge Case, Spec Edge Cases]
- [x] BR014 ¿Se define que un cambio del parámetro `margen_minimo` recalcula operaciones abiertas pero no documentos emitidos? [Consistency, Const. "Parámetros configurables"]

## Margen mínimo protegido — Consistencia con consumidores

- [x] BR015 ¿El contrato de `aplicar` es el mismo que invocan 008 y 009 (mismos campos de entrada/salida)? [Consistency, Contracts]
- [x] BR016 ¿La operación (venta/OT) NO se confirma si `decision = requiere_autorizacion` y no hay autorización? [Consistency, Spec §FR-012]
- [x] BR017 ¿Descuento y cupón exclusivos se valida en el servicio compartido (no solo en la UI)? [Consistency, Spec §FR-015]

## Cobertura de escenarios de la regla

- [x] BR018 ¿Hay casos de prueba para descuento porcentual y monto fijo? [Coverage]
- [x] BR019 ¿Hay casos para cupón con alcance producto/marca/tienda? [Coverage]
- [x] BR020 ¿Hay casos para el límite de uso de cupón (una vez / n veces / por cliente / global)? [Coverage]
