# Research: Gestión de Citas

**Feature**: `007-citas` | **Phase**: 0 | **Date**: 2026-09-10

## D1 — Ciclo de estados

- **Decisión**: `pendiente → confirmada → atendida`; `pendiente|confirmada → cancelada`. `confirmar` fija `fecha_confirmada`. `atender` exige (o crea) vínculo a venta/OT. No se puede cancelar una cita `atendida`.
- **Rationale**: §4.1.

## D2 — Vínculo a la transacción

- **Decisión**: `cita.venta_id` y `cita.orden_trabajo_id` FK anulables. `atender`:
  - si se pasa `venta_id`/`orden_trabajo_id` existente → se vincula.
  - si no → la respuesta incluye una acción de navegación (`crear_venta` o `crear_ot`) con `cliente_id` y `cita_id`; el frontend abre el flujo de 009/008; al confirmarse allí, esa feature vincula la cita.
- **Rationale**: §4.1 ("vincularse automáticamente a una venta o a una orden de trabajo generada"); Const. Ppio XI (nada de mensajes sin efecto).

## D3 — Canal de origen

- **Decisión**: FK a `canal_cita` (001). El personal registra la cita indicando el canal; el sistema NO lee Gmail.
- **Rationale**: §4.1, §9.3.

## D4 — Agenda

- **Decisión**: `GET /agenda?rango=dia|semana&fecha=...` devuelve las citas de la sucursal del usuario (scope) ordenadas por hora (preferida o confirmada). Gerencia General puede pasar `sucursal_id`.
- **Rationale**: §4.11.1.

## D5 — Solape

- **Decisión**: al confirmar, si existe otra cita `confirmada` en la misma sucursal con franja solapada (±30 min configurable), se devuelve una **advertencia** (no bloqueo); el personal decide.
- **Rationale**: §4.1 ("gestión manual por el personal"); no hay slots.

## D6 — Tasa de conversión operativa

- **Decisión**: `GET /citas/conversion?desde=&hasta=` = (citas atendidas con venta u OT vinculada) / (citas atendidas). El análisis por periodo/canal/sucursal es 013.
- **Rationale**: §4.11.2 (versión operativa).

## D7 — Recordatorios (014)

- **Decisión**: 007 expone `GET /_internal/citas/confirmadas-pendientes-recordatorio?antelacion=` para que 014 las tome. Si la cita se cancela/reprograma antes del envío, 014 no envía (007 solo provee el dato actualizado).
- **Rationale**: Const. "Stack"; §4.1.
