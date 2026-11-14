# Data Model: Servicio Técnico y Lubricación

**Feature**: `008-servicio-tecnico-lubricacion` | **Phase**: 1 | **Date**: 2026-09-10

Migración `0013_servicio_tecnico`. Reutiliza `reloj`, `pieza`, `calibre`, `stock_pieza`, `lote_pieza`, `evento_serie` (003); `tecnico` (005); `cliente`, `aplicacion_descuento`, `autorizacion_margen_minimo` (006); `cita` (007); `medio_pago`, `parametro_configuracion`, `registro_auditoria` (001).

## `orden_trabajo`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| numero | varchar(20) | secuencial visible |
| reloj_id | bigint FK → reloj | reloj no `en_transito`; verificar "adquirido en la tienda" |
| cliente_id | bigint FK → cliente | |
| tecnico_id | bigint FK → tecnico | nullable hasta asignar |
| sucursal_id | bigint FK | |
| cita_id | bigint FK → cita | nullable |
| ot_original_id | bigint FK → orden_trabajo | nullable (reapertura por garantía) |
| motivo | text | |
| diagnostico | text | nullable hasta `en_diagnostico` |
| trabajo_realizado | text | |
| tipo_reparacion | varchar(40) | para tiempo estimado / margen objetivo |
| horas_trabajadas | numeric(6,2) | registradas por el técnico |
| fecha_ingreso | timestamptz | al crear |
| fecha_estimada_entrega | date | **solo al aprobar presupuesto** |
| fecha_real_entrega | timestamptz | al `entregar` |
| costo_interno | numeric(14,2) | calculado (restringido) |
| precio_cobrado | numeric(14,2) | |
| margen_real | numeric(14,2) | calculado (restringido) |
| garantia_periodo_dias | int | parámetro por tipo de servicio |
| garantia_cobertura | varchar(255) | |
| estado | varchar(16) | `recibido` \| `en_diagnostico` \| `presupuesto` \| `en_reparacion` \| `listo` \| `entregado` |
| autorizacion_credito_id | bigint FK | nullable (entrega a crédito) |
| creado_en, actualizado_en | timestamptz | |

**Transiciones**: ver `research.md` D1.

## `historial_estado_ot` (append-only)
`id`, `orden_trabajo_id` FK, `estado`, `actor_usuario_id` FK, `timestamp`.

## `presupuesto`
`id`, `orden_trabajo_id` FK, `precio_servicio` numeric, `estado` (`borrador`|`enviado`|`aprobado`|`rechazado`), `confirmado_por` varchar(160), `medio_confirmacion` varchar(40), `fecha_confirmacion` timestamptz.

## `presupuesto_linea_pieza`
`id`, `presupuesto_id` FK, `pieza_original_id` FK, `pieza_no_original_id` FK nullable, `precio_original` numeric, `precio_no_original` numeric nullable, `preferencia_cliente` (`original`|`no_original`|`mixto`), `cantidad` int.

## `pieza_usada_ot`
`id`, `orden_trabajo_id` FK, `pieza_id` FK, `tipo_elegido` (`original`|`no_original`), `cantidad` int, `costo` numeric, `lote_id` FK nullable.

## `pago_ot` (vía `shared/pagos`)
`id`, `orden_trabajo_id` FK, `medio_pago_id` FK, `monto` numeric, `referencia` varchar(80), `creado_por` FK, `creado_en`.

## `ficha_lubricacion_calibre`
`id`, `calibre_id` FK (único), `notas_generales` text.

## `punto_lubricacion`
`id`, `ficha_lubricacion_calibre_id` FK, `nombre` varchar(120), `producto_moebius_id` FK (recomendado), `notas` text, `orden` int.

## `producto_moebius`
`id`, `codigo` varchar(20) único (9010, 9104, HP-1300, 9415, 9501, 9504, 8200, 8217, 8513, 8516…), `uso_recomendado` varchar(255), `pieza_id` FK → pieza (el insumo en stock).

## `registro_lubricacion_ot` (append-only)
`id`, `orden_trabajo_id` FK, `punto_lubricacion_id` FK, `producto_recomendado_id` FK, `producto_usado_id` FK, `tecnico_id` FK, `fecha` timestamptz, `desviacion` boolean.

## `documento_ot`
`id`, `orden_trabajo_id` FK, `tipo` (`orden_trabajo` | `certificado_garantia`), `objeto` (clave en `comprobantes-venta`), `generado_en`.

## Reglas de negocio (backend)

1. OT no se abre sobre un reloj `en_transito`; verificación "adquirido en la tienda" (override autorizado si falta).
2. `fecha_estimada_entrega` solo al aprobar el presupuesto.
3. `en_reparacion` requiere `presupuesto` `aprobado`.
4. `pieza_usada_ot` descuenta stock (003); nunca negativo; perecederas por FEFO.
5. `costo_interno`, `margen_real` y el costo de MO ocultos para roles no administrativos y ausentes de `documento_ot`.
6. Descuentos vía `shared/descuentos` (006) con margen mínimo protegido.
7. `entregado` requiere `saldo(OT) == 0` o `autorizacion_credito` (Gerencia General → CxC en 010).
8. Al `entregar`: `shared/pdf` genera OT + certificado a `comprobantes-venta`; `evento_serie(servicio)`; recálculo de nivel del cliente (006); notificación a 014.
9. Registro de lubricación por punto append-only; consumo de insumos descuenta stock.
10. Daño en servicio → payload para merma (011), sin sanción automática.
11. Todo cambio de estado ⇒ `historial_estado_ot` + auditoría.

## Migración

- `0013_servicio_tecnico` — todas las tablas anteriores
- Datos: `producto_moebius` sembrado (tabla §4.6); parámetros `margen_objetivo_servicio`, `tiempo_estimado_<tipo>`, `garantia_tienda_dias_<tipo>`

## Notas de implementación

- Migración real **`0020_servicio_tecnico`**. `pago_ot` NO existe: se usa la tabla `pago` de `shared/pagos` con `documento_tipo='orden_trabajo'`.
- `presupuesto_linea_pieza.preferencia_cliente` acepta `original|no_original|mixto` (CHECK).
- `orden_trabajo` gana en implementación: `numero` (secuencia `orden_trabajo_numero_seq`, formato `OT-000001`), `adquirido_en_tienda_ok` + `override_adquisicion_motivo`, `reproceso`, `descuento_aplicado` (JSONB).
- `registro_lubricacion_ot` es propiedad del módulo `lubricacion` (no `servicio_tecnico`).
- Parámetros sembrados: `margen_objetivo_servicio` (global, porcentaje 0.5), `garantia_tienda_dias_default` (180). El margen y la garantía por tipo de servicio / sucursal se fijan como overrides de ámbito cuando el negocio los necesite.


## Horarios de Sucursal para Retiro (migración 0027)

### `horario_sucursal`
`id`, `sucursal_id` FK, `dia_semana` (0=domingo a 6=sábado), `cerrado` boolean, `hora_apertura` time nullable, `hora_cierre` time nullable, unique(`sucursal_id`, `dia_semana`). Utilizado para indicar al cliente los horarios de atención en el correo de retiro.
