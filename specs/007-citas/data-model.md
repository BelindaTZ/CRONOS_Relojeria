# Data Model: Gestión de Citas

**Feature**: `007-citas` | **Phase**: 1 | **Date**: 2026-09-10

Migración `0012_citas`. Reutiliza `cliente` (006), `sucursal`, `canal_cita`, `usuario`, `registro_auditoria` (001).

## `cita`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| cliente_id | bigint FK → cliente | **obligatorio** (ficha existente) |
| sucursal_id | bigint FK → sucursal | |
| canal_cita_id | bigint FK → canal_cita | del catálogo, no texto libre |
| motivo | varchar(16) | `compra` \| `servicio_tecnico` \| `consulta` |
| fecha_preferida | timestamptz | |
| fecha_confirmada | timestamptz | nullable hasta `confirmar` |
| estado | varchar(12) | `pendiente` \| `confirmada` \| `cancelada` \| `atendida` |
| motivo_cancelacion | varchar(255) | obligatorio si `cancelada` |
| observaciones | text | |
| venta_id | bigint FK | nullable (009) |
| orden_trabajo_id | bigint FK | nullable (008) |
| creado_por | bigint FK → usuario | |
| creado_en, actualizado_en | timestamptz | |

**Transiciones**:
- `pendiente --confirmar--> confirmada` (fija `fecha_confirmada`; posible advertencia de solape)
- `pendiente | confirmada --cancelar(motivo)--> cancelada`
- `pendiente | confirmada --atender--> atendida` (exige o inicia vínculo a venta/OT)
- `atendida` y `cancelada` son terminales.

## `historial_estado_cita` (append-only)
`id`, `cita_id` FK, `estado`, `actor_usuario_id` FK, `timestamp`.

## Reglas de negocio (backend)

1. `cliente_id` obligatorio y debe existir.
2. `canal_cita_id` del catálogo de 001.
3. `confirmar` fija `fecha_confirmada`; advertencia (no bloqueo) si hay solape con otra `confirmada` de la misma sucursal.
4. `cancelar` exige `motivo_cancelacion`; no se cancela una cita `atendida`.
5. `atender`: si no hay `venta_id`/`orden_trabajo_id`, la respuesta trae la acción de creación con contexto (`cliente_id`, `cita_id`).
6. Scope por sucursal en listados y agenda.
7. Todo cambio de estado ⇒ `historial_estado_cita` + `registro_auditoria`.

## Vistas / consultas

- `agenda(rango, fecha, sucursal)` — citas ordenadas por hora.
- `conversion(desde, hasta)` — atendidas con transacción / atendidas.
- `confirmadas_pendientes_recordatorio(antelacion)` — para 014.

## Migración

- `0012_citas` — `cita`, `historial_estado_cita`

## Ajustes en implementación (2026-09-10)

- **Migración `0019_citas`** (no `0012`). `historial_estado_cita` gana `motivo` (varchar 255) para guardar el motivo de la cancelación en la bitácora.
- `cita.venta_id` / `orden_trabajo_id`: `bigint` **sin FK** (009/008 aún no existen).
- Parámetro sembrado: `citas_ventana_solape_min = 30`.
- `citas.vincular_transaccion(db, cita_id, *, venta_id?, orden_trabajo_id?, actor?)` — API pública para 008/009.
- Búsqueda por cliente (`q`) en `/citas` vía `clientes.ids_por_texto` (helper público de 006).
- **Migración `0027_flujo_principal`**: amplía el catálogo `canal_cita` con canales de redes sociales: `instagram`, `tiktok`, `facebook`.
