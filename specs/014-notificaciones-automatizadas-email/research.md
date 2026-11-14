# Research: Notificaciones Automatizadas por Email

**Feature**: `014-notificaciones-automatizadas-email` | **Phase**: 0 | **Date**: 2026-09-10

## D1 — Disparadores

- **Decisión**: tres disparadores automáticos (Const. "Stack"):
  1. **OT cambió de estado** (008) → `envio` tipo `ot_estado` al cliente.
  2. **Cupón emitido** o **cambio de nivel** (006) → `envio` tipo `cupon` / `nivel`.
  3. **Cita confirmada** (007) → `envio` tipo `recordatorio_cita`, **programado** para `fecha_confirmada − antelacion` (parámetro, def. 24 h).
  Además, 014 gestiona las plantillas de los disparos de 001 (`inactivacion_sucursal`, `password_temporal`) y 008 (`tecnico_asignado`), que esas features envían vía `shared/correo`.
- **Rationale**: Const. "Stack"; §4.7, §4.8.1, §4.8.2, §4.1.
- **Alternativas**: polling de cambios — frágil; se prefieren eventos de dominio emitidos por la feature de origen.

## D2 — Cola y worker

- **Decisión**: tabla `envio` con `estado ∈ {encolado, enviando, enviado, entregado, rebotado, fallido, sin_destinatario, cancelado}` y `proxima_ejecucion`. `worker.py` (poller cada N segundos, o job del compose existente) toma los `encolado` con `proxima_ejecucion ≤ now()`, llama a `shared/correo`, y actualiza el estado. Reintentos con backoff exponencial hasta `max_reintentos` (parámetro).
- **Rationale**: Ppio IX ("ningún disparo se pierde"); Ppio VII (sin broker).

## D3 — Desacople del camino transaccional

- **Decisión**: la feature de origen solo hace `INSERT` en `envio` (encolado) dentro de su transacción — operación local y barata. El envío real ocurre después en el worker. Confirmar venta/OT/cita **nunca** falla ni se ralentiza por el proveedor de email.
- **Rationale**: Spec §FR-017; Const. Ppio IX ("sin bloquear la interfaz").

## D4 — Estado de entrega

- **Decisión**: `POST /webhooks/email` recibe los eventos de SendGrid (delivered, bounce, dropped) y actualiza `envio.estado`. Sin webhook (SMTP simple), el estado máximo es `enviado`.
- **Rationale**: Spec §FR-007.

## D5 — Deduplicación

- **Decisión**: `envio` tiene `clave_idempotencia` = hash(`tipo` + `disparo_origen_tipo` + `disparo_origen_id` + `hito`). Un segundo disparo con la misma clave no crea otro `envio`. Para `ot_estado`, el `hito` es el estado destino, así varios cambios rápidos no generan duplicados del mismo estado.
- **Rationale**: Spec §FR-012.

## D6 — Opt-out

- **Decisión**: `preferencia_comunicacion` (cliente, `tipo_comunicacion`, `opt_in` bool). Antes de encolar, se consulta; si `opt_in = false` para ese tipo, el disparo se marca `cancelado` con motivo `opt_out` (visible, no perdido). Los correos operativos críticos (contraseña temporal) no admiten opt-out.
- **Rationale**: Ppio IX (seguridad/privacidad); §6.

## D7 — Sin destinatario

- **Decisión**: si el cliente no tiene email, el `envio` se marca `sin_destinatario` (visible en el panel), sin reintentos en bucle.
- **Rationale**: Spec §FR-013.

## D8 — Recordatorio de cita cancelada/reprogramada

- **Decisión**: el `envio` de recordatorio está `encolado` con `proxima_ejecucion` futura. Si la cita se cancela/reprograma antes, 007 emite un evento que 014 usa para `cancelar` (o reprogramar) el `envio` pendiente.
- **Rationale**: Spec §FR-010; §4.1.

## D9 — Plantillas

- **Decisión**: `plantilla_email` (tipo, asunto, cuerpo Jinja2, variables, version). Editables por Gerencia General / delegado. Todas heredan el layout de `shared/correo` con la paleta del Principio XI (`ui-ux-pro-max`). Preview con datos de ejemplo antes de guardar.
- **Rationale**: Spec §FR-006, §FR-004a; Const. Ppio XI/XII.

## D10 — Fuera de alcance

- **Decisión**: sin lectura de correo entrante (Gmail se gestiona manualmente, §4.1); sin recordatorios de mantenimiento preventivo (§8, propuesta abierta); sin campañas masivas de marketing.
- **Rationale**: Spec §FR-005, §FR-018; §8.
