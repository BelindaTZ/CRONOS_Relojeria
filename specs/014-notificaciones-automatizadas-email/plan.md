# Implementation Plan: Notificaciones Automatizadas por Email

**Branch**: `014-notificaciones-automatizadas-email` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Módulo completo de notificaciones automatizadas sobre la **capacidad compartida de correo introducida en 001**. Disparadores: **cambio de estado de la orden de trabajo** (008), **cupones y cambios de nivel de fidelización** (006), **recordatorios de citas confirmadas** (007). Gestiona **todas las plantillas** del sistema con identidad visual (incluidas las que disparan 001 —inactivación de sucursal, contraseña temporal— y 008 —técnico asignado—). **Cola con reintentos**, **seguimiento del estado de cada envío** (encolado/enviado/entregado/rebotado/fallido), **opt-out por tipo de comunicación**, **deduplicación**, y **desacople total del camino transaccional** (confirmar venta/OT/cita nunca falla por el email). Sin procesamiento de correo entrante. Recordatorios de mantenimiento preventivo fuera de alcance (§8).

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: `shared/correo` (001, envío + Jinja2), SendGrid SDK (o SMTP), un worker/cola (APScheduler o tabla-cola con poller — **sin** Airflow, que es 012); `shared/guard`, `shared/auditoria`, `shared/parametros` (antelación, reintentos); webhooks de estado de entrega de SendGrid

**Storage**: PostgreSQL (plantillas, envíos, cola, preferencias)

**Testing**: `pytest` (disparadores, cola/reintentos, dedup, opt-out, desacople), `vitest`

**Project Type**: Web — módulo `notificaciones`

**Performance Goals**: un cambio de estado de OT genera el email en < 1 min; el disparo no añade latencia perceptible al flujo transaccional

**Constraints**: envío asíncrono y desacoplado (nunca bloquea la transacción); sin correo entrante; sin recordatorios de mantenimiento preventivo; plantillas con identidad visual (Ppio XI/XII)

**Scale/Scope**: decenas de envíos/día

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan Const. "Stack", §4.7, §4.8.1, §4.8.2, §4.1, §6, §8. ✅ |
| II | Cada envío, plantilla y preferencia es un registro real. ✅ |
| III | PostgreSQL OLTP; sin ClickHouse. ✅ |
| IV | Módulo `notificaciones` / bajo Configuración; plantillas solo Gerencia General o delegado. ✅ |
| V | Lógica de disparo/cola/dedup en backend. ✅ |
| VI | Referencia 001 (`shared/correo`), 006, 007, 008; no los redefine. ✅ |
| VII | Cola simple (tabla + poller), sin broker; sin Airflow. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | Credenciales `.env`; cola con reintentos; ningún disparo se pierde en silencio; desacople del camino crítico. ✅ |
| X | Módulo `notificaciones/` con capas; reutiliza `shared/correo`. ✅ |
| XI | Panel de envíos con reintento (acción real); plantillas con identidad visual; reporte operativo. ✅ |
| XII | Plantillas construidas con `ui-ux-pro-max` y la paleta. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/notificaciones/
├── router.py     # /plantillas, /envios, /envios/{id}/reintentar, /preferencias, /reportes/envios, /webhooks/email
├── service.py    # disparadores, encolado, dedup, opt-out, reintentos, estado
├── worker.py     # poller de la cola (envía y actualiza estado); reintentos con backoff
├── plantillas/   # HTML Jinja2 que heredan el layout de shared/correo (identidad visual)
├── repository.py
└── schemas.py

frontend/src/notificaciones/
├── components/ (PanelEnvios, EditorPlantilla, PreferenciasCliente, ReporteEnvios)
├── composables/ stores/ services/
```

**Structure Decision**: Un módulo. Los disparadores son **suscripciones a eventos de dominio** que 006/007/008 emiten (venta confirmada, OT cambió de estado, cupón emitido, cita confirmada); 014 los traduce a `envio` encolado. El worker es un poller in-proceso (o job del compose existente), nunca Airflow.

## Complexity Tracking

| Elemento | Por qué | Alternativa más simple rechazada porque |
|---|---|---|
| Cola + worker con reintentos | Const. "Stack" (envíos automatizados) + Ppio IX (ningún disparo se pierde) | Envío síncrono en el request: acoplaría el email al camino transaccional (viola Spec §FR-017) |
| Webhooks de estado de entrega | Spec §FR-007 (estado real: entregado/rebotado) | Marcar "enviado" y asumir entrega: no permite gestionar rebotes |
