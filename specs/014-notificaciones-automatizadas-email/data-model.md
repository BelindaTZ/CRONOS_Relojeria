# Data Model: Notificaciones Automatizadas por Email

**Feature**: `014-notificaciones-automatizadas-email` | **Phase**: 1 | **Date**: 2026-09-10

Migración real `0030_notificaciones` (spec inicial decía `0017`). Reutiliza `cliente` (006), `usuario`, `parametro_configuracion`, `registro_auditoria` (001); `shared/correo` (001).

## `plantilla_email`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| tipo | varchar(30) | `ot_estado` \| `cupon` \| `nivel` \| `recordatorio_cita` \| `tecnico_asignado` \| `inactivacion_sucursal` \| `password_temporal` |
| asunto | varchar(200) | Jinja2 (variables) |
| cuerpo | text | HTML Jinja2 que hereda el layout de `shared/correo` |
| variables | jsonb | nombres esperados en el contexto |
| version | int | incremental |
| activa | boolean | |
| actualizado_por | bigint FK | |
| actualizado_en | timestamptz | |

- **Edición**: solo Gerencia General / delegado; auditada.

## `envio`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| tipo | varchar(30) | = `plantilla_email.tipo` |
| destinatario_email | varchar(160) | nullable (→ `sin_destinatario`) |
| cliente_id | bigint FK → cliente | nullable (correos a usuarios internos) |
| usuario_id | bigint FK → usuario | nullable |
| disparo_origen_tipo | varchar(24) | `orden_trabajo` \| `cupon` \| `nivel_cliente` \| `cita` \| `sucursal` \| `restablecimiento` |
| disparo_origen_id | bigint | |
| hito | varchar(40) | p. ej. estado destino de la OT |
| clave_idempotencia | varchar(80) | **única** (dedup) |
| contexto | jsonb | datos para render |
| estado | varchar(16) | `encolado` \| `enviando` \| `enviado` \| `entregado` \| `rebotado` \| `fallido` \| `sin_destinatario` \| `cancelado` |
| motivo_estado | varchar(120) | p. ej. `opt_out`, `bounce`, `cita_cancelada` |
| intentos | int | default 0 |
| max_reintentos | int | parámetro |
| proxima_ejecucion | timestamptz | inmediata o programada (recordatorio) |
| proveedor_message_id | varchar(120) | del SendGrid, para conciliar webhooks |
| creado_en, actualizado_en | timestamptz | |

**Transiciones**: `encolado → enviando → enviado → (entregado | rebotado)`; `encolado/enviando → fallido` (tras `max_reintentos`); `encolado → cancelado` (opt-out, cita cancelada); `encolado → sin_destinatario`.

## `preferencia_comunicacion`
`id`, `cliente_id` FK, `tipo_comunicacion` varchar(30), `opt_in` boolean default true, único (`cliente_id`, `tipo_comunicacion`).
- Los tipos operativos críticos (`password_temporal`) no admiten opt-out.

## `evento_webhook_email` (append-only)
`id`, `proveedor_message_id`, `evento` (`delivered` | `bounce` | `dropped` | `deferred`), `payload` jsonb, `recibido_en`.

## Reglas de negocio (backend)

1. La feature de origen solo hace `INSERT` en `envio` (encolado), dentro de su transacción; el envío real es del worker (desacople).
2. `clave_idempotencia` única ⇒ un segundo disparo idéntico no crea otro `envio`.
3. Antes de encolar, se consulta `preferencia_comunicacion`; `opt_in = false` ⇒ `cancelado` con `motivo_estado = opt_out` (salvo tipos críticos).
4. Cliente sin email ⇒ `sin_destinatario`, sin reintentos.
5. Cita cancelada/reprogramada ⇒ `envio` de recordatorio pendiente pasa a `cancelado` (o se reprograma).
6. Reintentos con backoff hasta `max_reintentos`; luego `fallido` (reintentable manualmente desde el panel).
7. Webhooks de SendGrid actualizan `estado` (`entregado`/`rebotado`).
8. Todo envío queda auditable (destinatario, tipo, origen, timestamps, estado).
9. Confirmar venta/OT/cita nunca falla por el email.

## Migración

- `0017_notificaciones` — `plantilla_email`, `envio`, `preferencia_comunicacion`, `evento_webhook_email`
- Datos: plantillas sembradas (7 tipos) con identidad visual; parámetros `antelacion_recordatorio_cita` (24 h), `max_reintentos_email` (5), `backoff_email`
