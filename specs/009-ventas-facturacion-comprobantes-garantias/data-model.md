# Data Model: Ventas, Comprobantes y Garantías

**Feature**: `009-ventas-facturacion-comprobantes-garantias` | **Phase**: 1 | **Date**: 2026-09-10

Migración `0014_ventas`. Reutiliza `reloj`, `pieza`, `stock_pieza`, `evento_serie` (003); `cliente`, `aplicacion_descuento`, `autorizacion_margen_minimo`, `cupon` (006); `cita` (007); `medio_pago` (001); `pago_ot`/`shared/pagos` (008).

## `orden_venta`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| numero | varchar(20) | secuencial visible |
| cliente_id | bigint FK → cliente | obligatorio (genérico solo si aplica D8) |
| sucursal_id | bigint FK | |
| vendedor_usuario_id | bigint FK → usuario | |
| cita_id | bigint FK → cita | nullable |
| estado | varchar(10) | `borrador` \| `confirmada` \| `anulada` |
| fecha | timestamptz | |
| subtotal | numeric(14,2) | Σ precio_lista |
| total | numeric(14,2) | Σ precio_final |
| margen_venta | numeric(14,2) | calculado (**restringido**) |
| autorizacion_margen_minimo_id | bigint FK | nullable |
| identificacion_fiscal | varchar(20) | para compatibilidad SRI |
| creado_en, actualizado_en | timestamptz | |

## `linea_venta`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| orden_venta_id | bigint FK | |
| item_tipo | varchar(8) | `reloj` \| `pieza` |
| reloj_id | bigint FK | null si pieza |
| pieza_id | bigint FK | null si reloj |
| cantidad | int | 1 para relojes |
| precio_lista | numeric(14,2) | |
| precio_final | numeric(14,2) | tras descuento |
| costo | numeric(14,2) | **restringido** |
| margen | numeric(14,2) | **restringido** |

## `pago_venta` (vía `shared/pagos`)
`id`, `orden_venta_id` FK, `medio_pago_id` FK, `monto` numeric, `referencia` varchar(80), `creado_por`, `creado_en`.

## `garantia_venta`
`id`, `orden_venta_id` FK, `tipo` (`fabrica` | `tienda`), `periodo_dias` int, `fecha_inicio` date, `fecha_fin` date, `cobertura` varchar(255).

## `comprobante_venta`
`id`, `orden_venta_id` FK, `tipo` (`comprobante` | `certificado_garantia_autenticidad`), `objeto` (clave en `comprobantes-venta`), `numero_serie_vinculado` varchar(80) nullable, `generado_en`.

## `anulacion_venta`
`id`, `orden_venta_id` FK, `motivo` varchar(255), `actor_usuario_id` FK, `fecha` timestamptz, `reversas` jsonb (stock, margen, nivel, CxC).

## `cuenta_por_cobrar` (creada por 009; el subledger/aging lo maneja 010)
`id`, `origen_tipo` (`venta` | `orden_trabajo`), `origen_id`, `cliente_id` FK, `monto_original` numeric, `saldo` numeric, `estado` (`pendiente` | `saldada` | `anulada`), `creado_en`.

## Reglas de negocio (backend)

1. `confirmar` es atómico: stock, evento de serie, pagos, CxC, PDFs, recálculo de nivel, vínculo de cita.
2. Stock nunca negativo; reloj `en_transito` o ya vendido ⇒ 409.
3. Descuento **o** cupón, no ambos (006). Cupón de uso único con lock.
4. `decision = requiere_autorizacion` ⇒ venta no confirmable sin `autorizacion_margen_minimo`.
5. `margen_venta`, `costo`, `margen` de línea ocultos para roles no administrativos y ausentes de los comprobantes.
6. Pago parcial ⇒ `cuenta_por_cobrar` por el saldo.
7. Venta de reloj ⇒ cliente identificado; consumidor final solo piezas sueltas < `monto_max_consumidor_final`.
8. `anular` reingresa stock, revierte margen y nivel, marca CxC `anulada`, genera `anulacion_venta`; bloqueada si el reloj está en servicio.
9. Modelo de comprobante compatible con SRI (identificación fiscal, secuencial, impuestos desglosados); sin transmisión al SRI.
10. Todo cambio de precio/anulación ⇒ auditoría.

## Migración

- `0014_ventas` — `orden_venta`, `linea_venta`, `pago_venta`, `garantia_venta`, `comprobante_venta`, `anulacion_venta`, `cuenta_por_cobrar`
- Datos: parámetros `garantia_fabrica_dias_<marca>` (opcional), `garantia_tienda_dias_<tipo>`, `monto_max_consumidor_final`

## Notas de implementación

- Migración real **`0021_ventas`**. `pago_venta` NO existe: la tabla `pago` de `shared/pagos` con `documento_tipo='venta'`.
- `orden_venta` gana `numero` (secuencia `orden_venta_numero_seq`, `V-000001`), `descuento_aplicado` (JSONB), `identificacion_fiscal`, `creado_por`.
- `linea_venta.precio_final` y `margen` se recalculan al prorratear el descuento de la orden.
- `garantia_venta.linea_venta_id` se puebla (una fábrica + una tienda por reloj vendido).
- `comprobante_venta.tipo` es `VARCHAR(40)`.
- `cuenta_por_cobrar` es propiedad de `ventas`; 010 la lee/actualiza vía `ventas/public.py`.

## Ampliación — facturación con IVA, sucursal del vendedor, envío por correo (2026-09-10)

Migración **`0022_facturacion`**:

- **`config_facturacion`** (fila única id=1): `razon_social`, `nombre_comercial`, `ruc`, `direccion_matriz`, `obligado_contabilidad`, `contribuyente_especial`, `regimen`, `leyenda_pie`.
- **`punto_emision`** (1 por sucursal): `establecimiento_codigo`, `punto_emision_codigo`, `secuencial_actual`, `direccion_establecimiento`. La factura usa `numero_factura = EEE-PPP-NNNNNNNNN`.
- `orden_venta` gana `numero_factura`, `subtotal_sin_impuestos`, `total_descuento`, `iva_porcentaje` (snapshot al confirmar), `iva_monto`.
- `linea_venta` gana `descuento_monto`, `base_imponible`, `iva_monto`, `tarifa_iva`.
- Parámetro `iva_porcentaje` (0.15, global, configurable).
- `sucursal_id` de `VentaIn` pasa a ser **opcional** (override): la sucursal real se deriva del vendedor (`ventas.service._sucursal_para_venta`).
- `shared/pdf.comprobante_venta` fue renombrada/ampliada a `factura_venta(ctx)` (con alias retrocompatible `comprobante_venta`), con el desglose reglamentario completo.
- Plantilla de correo `factura_venta` (envío manual, `POST /ventas/{id}/enviar-factura`).
