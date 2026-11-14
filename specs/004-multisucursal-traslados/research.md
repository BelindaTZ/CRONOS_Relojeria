# Research: Multi-Sucursal y Traslados de Inventario

**Feature**: `004-multisucursal-traslados` | **Phase**: 0 | **Date**: 2026-09-10

## D1 — Máquina de estados de la transferencia

- **Decisión**: `en_preparacion → en_transito → recibida` (o `parcial`); desde `en_preparacion`/`en_transito` → `cancelada`. `enviar` marca ítems `en_transito`; `recibir` confirma y actualiza inventario; `cancelar` revierte a `disponible` en origen.
- **Rationale**: §4.9 (fecha de envío, recepción, responsables).
- **Alternativas**: sin estado "en tránsito" (mover el stock al enviar) — deja el inventario en un limbo sin trazabilidad del movimiento físico.

## D2 — Efecto sobre el inventario

- **Decisión**: relojes: al `enviar`, `disponibilidad = en_transito`; al `recibir`, `sucursal_actual_id = destino`, `disponibilidad = disponible`, `evento_serie(transferencia)`. Piezas: al `enviar`, `movimiento_stock_pieza(transferencia_salida)` en origen; al `recibir`, `movimiento_stock_pieza(transferencia_entrada)` en destino. Todo en transacción.
- **Rationale**: Const. Ppio II; §4.9 ("actualización automática del inventario en ambas sucursales").

## D3 — Discrepancia en recepción

- **Decisión**: si `cantidad_recibida < enviada` (piezas) o falta una unidad (relojes), se registra `discrepancia_transferencia` y se ofrece crear una merma (011, causa `dano_transito`). El faltante NO reingresa a ninguna sucursal hasta resolverse.
- **Rationale**: §4.9, §4.12.

## D4 — Ítem en tránsito no operable

- **Decisión**: los endpoints de venta (009) y de apertura de OT (008) rechazan un reloj con `disponibilidad = en_transito`; las piezas en tránsito no cuentan para el `stock_actual` de ninguna sucursal (salieron de origen, no llegaron a destino).
- **Rationale**: Const. Ppio II (registro real; nada de doble disponibilidad).

## D5 — Scoping de reportes de inventario

- **Decisión**: los endpoints `GET /relojes`, `GET /valor-inventario`, `GET /piezas` (003) y los de traslados aplican `scope_sucursal(query, user)` de 001: rol "gerente de sucursal" → solo su sucursal; Gerencia General → consolidado o filtrado por `sucursal_id`.
- **Rationale**: §4.9, §3, §6.
- **Alternativas**: reimplementar el filtro en cada módulo — viola DRY (Ppio VII/X).

## D6 — Una sola sucursal

- **Decisión**: si solo hay 1 sucursal activa, el formulario de transferencia no ofrece destino y la funcionalidad queda inerte pero disponible; el modelo no cambia al pasar a N sucursales.
- **Rationale**: §4.9 ("desde el diseño inicial, aunque se opere con una sola sucursal"), §6.

## D7 — Cancelación y concurrencia

- **Decisión**: `cancelar` solo permitido en `en_preparacion`/`en_transito`; `recibir` toma lock sobre la transferencia; dos confirmaciones simultáneas ⇒ la segunda ve estado `recibida` y no repite el efecto.
- **Rationale**: robustez; Edge Cases del spec.
