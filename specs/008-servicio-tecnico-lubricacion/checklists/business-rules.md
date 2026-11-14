# Business Rules Quality Checklist: Costeo y Margen del Servicio

**Purpose**: Checklist adicional para las reglas de negocio críticas de la feature 008 (costeo y margen del servicio, margen mínimo tras descuentos, consumo de insumos), con cobertura de pruebas obligatoria (Const. Ppio IX).
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Costo interno del servicio — Completitud

- [x] BR001 ¿Se define cada componente del costo interno (mano de obra, piezas, insumos) y su fuente? [Completeness, research D3]
- [x] BR002 ¿Se define el fallback de mano de obra cuando no hay horas registradas (tiempo estimado del tipo de reparación)? [Completeness, Spec §FR-010; research D3]
- [x] BR003 ¿Se define cómo y cuándo el bono prorrateado (005) se suma al costo de mano de obra en los reportes de margen? [Gap, Spec §FR-004a de 005]
- [x] BR004 ¿Se define la valoración de insumos de lubricación (a costo del lote)? [Clarity, research D5]

## Precio y margen — Claridad

- [x] BR005 ¿`precio_sugerido = costo_interno × (1 + margen_objetivo)` está explícito y el margen objetivo es parámetro por ámbito? [Clarity, Spec §FR-011, §FR-012]
- [x] BR006 ¿`margen_real = precio_cobrado − costo_interno` está explícito? [Clarity, Spec §FR-013]
- [x] BR007 ¿Se permite fijar el precio manualmente y se valida que no deje margen negativo (o se advierte)? [Edge Case, Spec Edge Cases]
- [x] BR008 ¿El cambio de `margen_objetivo_servicio` recalcula el precio/margen de OT no entregadas y no de las entregadas? [Consistency, Spec §FR-011; Const. "Parámetros configurables"]

## Margen mínimo tras descuentos — Consistencia

- [x] BR009 ¿La aplicación de descuento en la OT llama al mismo `shared/descuentos.aplicar` que 009? [Consistency, Spec §FR-014]
- [x] BR010 ¿La OT NO se confirma/entrega si `decision = requiere_autorizacion` sin autorización registrada? [Consistency, Spec §FR-014]
- [x] BR011 ¿La base del margen para el servicio incluye MO + piezas + insumos (no solo costo de pieza)? [Clarity, Esp. §5, §4.8.2]

## Consumo de insumos — Cobertura

- [x] BR012 ¿Cada `producto_usado` en un punto descuenta el stock de la pieza-insumo correspondiente? [Coverage, research D5]
- [x] BR013 ¿El consumo de insumos perecederos aplica FEFO y valora a costo del lote? [Coverage, Spec §FR-009]
- [x] BR014 ¿La desviación (recomendado ≠ usado) se registra sin bloquear y alimenta el reporte operativo? [Coverage, Spec §FR-008]

## Confidencialidad

- [x] BR015 ¿Costo de mano de obra, costo interno y margen están ausentes del `documento_ot` y del certificado? [Security, Spec §FR-026, §FR-019]
- [x] BR016 ¿El endpoint de costeo devuelve 403 / oculta valores para roles no administrativos? [Security, Contracts /ordenes-trabajo/{id}/costeo]
