# Data Model: Contabilidad, Gastos, CxC y CxP

**Feature**: `010-contabilidad-gastos-cxc-cxp` | **Phase**: 1 | **Date**: 2026-09-10

Migración real `0023_contabilidad` (spec inicial decía `0015`). Reutiliza `sucursal`, `categoria_gasto`, `medio_pago`, `usuario`, `parametro_configuracion`, `registro_auditoria` (001); `cuenta_por_cobrar` (009); `orden_compra` (002); `merma` (011).

## `cuenta_contable`
`id`, `codigo` varchar(20) único, `nombre` varchar(160), `tipo` (`activo`|`pasivo`|`patrimonio`|`ingreso`|`gasto`), `cuenta_padre_id` FK nullable, `imputable` boolean. Plan inicial sembrado (NIIF PYMES).

## `periodo_contable`
`id`, `fecha_inicio` date, `fecha_fin` date, `estado` (`abierto`|`cerrado`), `cerrado_por` FK, `cerrado_en`.

## `asiento`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| fecha | date | dentro de un periodo abierto (o `asiento_ajuste`) |
| glosa | varchar(255) | |
| origen | varchar(24) | `manual` \| `venta` \| `compra` \| `gasto` \| `merma` \| `cobro` \| `pago` \| `ajuste` |
| origen_id | bigint | nullable |
| ajuste_de_asiento_id | bigint FK | nullable (asiento de ajuste) |
| creado_por | bigint FK | |
| creado_en | timestamptz | |

## `linea_asiento`
`id`, `asiento_id` FK, `cuenta_contable_id` FK, `debe` numeric(14,2) default 0, `haber` numeric(14,2) default 0.
**Invariante**: por asiento, `Σ debe = Σ haber`; no se guarda si no cuadra.

## `caja`
`id`, `sucursal_id` FK único, `nombre` varchar(80).

## `sesion_caja`
`id`, `caja_id` FK, `abierta_por` FK, `saldo_inicial` numeric, `abierta_en` timestamptz, `cerrada_por` FK nullable, `efectivo_contado` numeric nullable, `efectivo_esperado` numeric nullable, `diferencia` numeric nullable, `cerrada_en` timestamptz nullable, `estado` (`abierta`|`cerrada`).

## `movimiento_caja`
`id`, `sesion_caja_id` FK, `tipo` (`entrada`|`salida`), `monto` numeric, `medio_pago_id` FK, `documento_tipo`, `documento_id`, `creado_en`.

## `cheque`
`id`, `tipo` (`emitido`|`recibido`), `banco` varchar(80), `numero` varchar(40), `monto` numeric, `fecha` date, `estado` (`en_cartera`|`depositado`|`cobrado`|`protestado`), `documento_origen_tipo`, `documento_origen_id`.

## `beneficiario`
`id`, `nombre` varchar(160) único, `identificacion` varchar(20) nullable, `tipo_servicio` varchar(60) (agua, energía, telecom, arriendo, otro), `activo` boolean. Acreedor de servicios que no es un proveedor de mercadería (002).

## `cuenta_por_pagar`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| origen_tipo | varchar(12) | `orden_compra` \| `gasto` |
| orden_compra_id | bigint FK → orden_compra | null si origen `gasto` |
| gasto_id | bigint FK → gasto | null si origen `orden_compra` |
| proveedor_id | bigint FK → proveedor | contraparte (uno de proveedor/beneficiario) |
| beneficiario_id | bigint FK → beneficiario | contraparte alternativa |
| monto_original | numeric(14,2) | |
| saldo | numeric(14,2) | |
| estado | varchar(10) | `pendiente` \| `saldada` \| `anulada` |
| creado_en | timestamptz | |

- **Invariante**: exactamente uno de `proveedor_id` / `beneficiario_id` no nulo; exactamente uno de `orden_compra_id` / `gasto_id` no nulo.

## `cobro_cxc` / `pago_cxp`
`id`, `cxc_id`|`cxp_id` FK, `monto` numeric, `medio_pago_id` FK, `fecha` date, `cheque_id` FK nullable, `retencion_fuente` jsonb nullable (solo `pago_cxp`).

## `gasto`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| sucursal_id | bigint FK | |
| categoria_gasto_id | bigint FK | obligatoria |
| proveedor_id | bigint FK → proveedor | nullable (contraparte) |
| beneficiario_id | bigint FK → beneficiario | nullable (contraparte) |
| monto | numeric(14,2) | |
| fecha | date | dentro de periodo abierto |
| descripcion | varchar(255) | |
| documento_soporte_objeto | varchar(255) | bucket `documentos` |
| estado_pago | varchar(10) | `pagado` \| `por_pagar` |
| medio_pago_id | bigint FK → medio_pago | requerido si `pagado` |
| movimiento_caja_id | bigint FK | si `pagado` en efectivo/caja |
| cuenta_por_pagar_id | bigint FK → cuenta_por_pagar | si `por_pagar` |
| gasto_recurrente_id | bigint FK → gasto_recurrente | nullable |
| estado | varchar(10) | `borrador` (generado por recurrente) \| `confirmado` |
| asiento_id | bigint FK | al confirmar |
| creado_por | bigint FK | |

- **Regla**: un `gasto` en `borrador` (generado por un recurrente) no tiene asiento ni CxP hasta que Gerencia General lo `confirma` (ajustando monto y `estado_pago`).
- **Regla**: `pagado` ⇒ `medio_pago_id` + movimiento de caja/banco; `por_pagar` ⇒ `cuenta_por_pagar` (`origen_tipo = gasto`).

## `gasto_recurrente`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| categoria_gasto_id | bigint FK | |
| proveedor_id / beneficiario_id | bigint FK | uno de los dos |
| descripcion | varchar(160) | |
| monto_estimado | numeric(14,2) | |
| frecuencia | varchar(12) | `mensual` \| `bimestral` \| `trimestral` |
| sucursal_id | bigint FK | |
| proxima_generacion | date | |
| estado | varchar(10) | `activo` \| `pausado` \| `cancelado` |

## `regla_asiento_automatico`
`id`, `evento` varchar(24), `cuenta_debe_id` FK, `cuenta_haber_id` FK, `condicion` jsonb nullable, `activa` boolean.

## Consultas / vistas

- `mayor(cuenta, periodo)` — movimientos y saldo.
- `balance_comprobacion(periodo)` — Σ debe / Σ haber por cuenta; total debe = total haber.
- `estado_resultados(periodo, sucursal?)` — ingresos − costos − gastos.
- `aging(tipo, fecha_corte)` — CxC/CxP por tramos 0-30/31-60/61-90/+90.
- `rentabilidad_sucursal(periodo, sucursal)` — ingresos − costo de ventas/servicios − gastos operativos.

## Reglas de negocio (backend)

1. Asiento nunca descuadrado.
2. Periodo cerrado ⇒ ajuste solo por `asiento` con `ajuste_de_asiento_id`; original inmutable.
3. Cheque `protestado` ⇒ revierte el cobro y reactiva la CxC (o marca la venta impaga).
4. `cierre` de sesión de caja registra `diferencia`; lock ante concurrencia.
5. Gasto **confirmado** ⇒ asiento automático (`pagado` → haber caja/bancos; `por_pagar` → haber cuentas por pagar + `cuenta_por_pagar` con `origen_tipo = gasto`); merma ⇒ asiento a cuenta de **pérdida extraordinaria**.
6. Un `gasto` en `borrador` (de un recurrente) no tiene asiento ni CxP hasta confirmarse.
7. Scope por sucursal en toda consulta.
8. Un cambio de parámetro configurable no recalcula asientos de periodos cerrados.
9. Todo asiento/cobro/pago/gasto ⇒ auditoría.
10. Registro/confirmación de gastos, gastos recurrentes y pagos de CxP: solo rol Gerencia General.
11. `cuenta_por_pagar`: exactamente uno de proveedor/beneficiario y uno de orden_compra/gasto.

## Migración

- `0015_contabilidad` — todas las tablas anteriores (incluye `beneficiario`, `gasto_recurrente`; `cuenta_por_pagar` con `origen_tipo`, `gasto`.`estado_pago`/`estado`)
- Datos: plan de cuentas NIIF PYMES; `regla_asiento_automatico` inicial para venta/compra/gasto_pagado/gasto_por_pagar/merma/cobro/pago
- Un scheduler in-proceso (APScheduler) genera los `gasto` en borrador de los `gasto_recurrente` vencidos (mismo patrón que 002; sin Airflow)

## Notas de implementación

- Migración real **`0023_contabilidad`** (la spec decía `0015`; renumerada por orden de features implementadas). 15 tablas nuevas + siembra de `categoria_gasto` (tabla de `0005`, antes vacía).
- Plan de cuentas semilla: 22 cuentas (activo/pasivo/patrimonio/ingreso/gasto, jerárquico vía `cuenta_padre_id`). 15 `regla_asiento_automatico` semilla, con `condicion` JSONB para desambiguar `pago_cxp`/`gasto_pagado`/`gasto_por_pagar` por `origen_tipo`/`categoria_tipo`.
- `cuenta_por_pagar` valida "exactamente un origen" y "exactamente una contraparte" con **CHECK constraints** a nivel de BD (`ck_cxp_un_origen`, `ck_cxp_una_contraparte`, truco booleano→entero), no solo en el service.
- No existe columna `sucursal_id` en `asiento`/`linea_asiento` (el libro mayor es transversal); `rentabilidad_sucursal` se calcula aparte, agregando `ventas.resumen_periodo` + `servicio_tecnico.resumen_periodo` (nuevas APIs públicas) menos gastos del rango — la "versión operativa" que describe research.md D8, no un cruce contra el mayor.
- Una venta o entrega de OT con pago inmediato dispara `generar_asiento` (100% a CxC) **y** `cobro_cxc` (la porción pagada) en el mismo flujo, en vez de una regla multi-línea configurable — simplifica `regla_asiento_automatico` a un único par debe/haber por evento.
- Registro/confirmación de gastos y pagos de CxP: check `es_gerencia(user)` en el service (mismo patrón `NoAutorizadoError`/403 que 005/006), no `require_gerencia_o_delegado`.
- Scheduler de gastos recurrentes: `contabilidad/scheduler.py`, endpoint interno `POST /_internal/contabilidad/scheduler/tick` (ruta propia, distinta de la de `proveedores` en 002, para no colisionar).
- Suite backend total tras esta feature: **207** tests.
