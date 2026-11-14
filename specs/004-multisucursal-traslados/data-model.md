# Data Model: Multi-Sucursal y Traslados de Inventario

**Feature**: `004-multisucursal-traslados` | **Phase**: 1 | **Date**: 2026-09-10

Migración `0009_traslados`. Reutiliza `sucursal`, `usuario` (001); `reloj`, `pieza`, `stock_pieza`, `movimiento_stock_pieza`, `evento_serie` (003).

## `transferencia`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| sucursal_origen_id | bigint FK → sucursal | ≠ destino |
| sucursal_destino_id | bigint FK → sucursal | ≠ origen |
| estado | varchar(16) | `en_preparacion` \| `en_transito` \| `recibida` \| `parcial` \| `cancelada` |
| motivo | varchar(500) | obligatorio |
| fecha_envio | timestamptz | nullable hasta `enviar` |
| fecha_recepcion | timestamptz | nullable hasta `recibir` |
| responsable_envio_id | bigint FK → usuario | |
| responsable_recepcion_id | bigint FK → usuario | nullable |
| creado_en, actualizado_en | timestamptz | |

**Transiciones**:
- `en_preparacion --enviar--> en_transito` (ítems → no disponibles en origen)
- `en_transito --recibir(completa)--> recibida`
- `en_transito --recibir(faltante)--> parcial` (+ `discrepancia_transferencia`)
- `en_preparacion | en_transito --cancelar--> cancelada` (ítems → disponibles en origen)

## `linea_transferencia`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| transferencia_id | bigint FK | |
| item_tipo | varchar(8) | `reloj` \| `pieza` |
| reloj_id | bigint FK → reloj | null si pieza |
| pieza_id | bigint FK → pieza | null si reloj |
| cantidad_enviada | int | 1 para relojes |
| cantidad_recibida | int | nullable hasta recepción |

## `discrepancia_transferencia`
`id`, `linea_transferencia_id` FK, `cantidad_faltante` int, `merma_id` bigint FK (nullable, → 011), `resuelta` boolean, `creado_en`.

## `evento_transferencia_serie` (vista/inserción en `evento_serie`)
Cada `recibir` que mueve un reloj inserta un `evento_serie` tipo `transferencia` con `detalle = {origen, destino, motivo}`.

## Reglas de negocio (backend)

1. `origen ≠ destino`; ambas sucursales `activa` al `enviar` (destino puede inactivarse luego → la transferencia en tránsito se puede recibir o cancelar).
2. Al `enviar`: relojes `disponibilidad = en_transito`; piezas `movimiento_stock_pieza(transferencia_salida)` (no cuentan para stock de nadie).
3. Al `recibir`: relojes `sucursal_actual_id = destino`, `disponibilidad = disponible`, `evento_serie(transferencia)`; piezas `movimiento_stock_pieza(transferencia_entrada)` en destino.
4. Faltante ⇒ `discrepancia_transferencia`; ofrecer merma (011); el faltante no reingresa a stock hasta resolver.
5. `cancelar` solo en `en_preparacion`/`en_transito`; revierte ítems a `disponible` en origen.
6. Un reloj `en_transito` no es vendible (009) ni entra a OT (008).
7. Todos los cambios de estado ⇒ `registro_auditoria`.
8. `recibir` toma lock de la transferencia (idempotente ante doble confirmación).

## Migración

- `0009_traslados` — `transferencia`, `linea_transferencia`, `discrepancia_transferencia`


## Ajustes en implementación (2026-09-11)

- **Migración `0010_traslados`**: esquema base de `transferencia`, `linea_transferencia`, `discrepancia_transferencia`.
- **Migración `0027_flujo_principal`**: parámetro de configuración `costo_traslado_venta` ($15) para costeo referencial de traslados a pedido de cliente.
- **Migración `0028_vendedor_traslados`**: concede permisos `multisucursal:crear` y `multisucursal:consultar` al rol `Vendedor` para iniciar traslados solicitados desde venta.
- **Endpoints de apoyo**: `GET /transferencias/costo-referencial` y `GET /transferencias/items-disponibles`.
