# Research: Contabilidad, Gastos, CxC y CxP

**Feature**: `010-contabilidad-gastos-cxc-cxp` | **Phase**: 0 | **Date**: 2026-09-10

## D1 — Plan de cuentas

- **Decisión**: `cuenta_contable` jerárquica (código, nombre, tipo ∈ {activo, pasivo, patrimonio, ingreso, gasto}, `cuenta_padre_id`, `imputable` bool). Plan inicial sembrado compatible con NIIF para PYMES (estructura mínima: caja/bancos, inventario, CxC, CxP, capital, ventas, costo de ventas, gastos operativos por categoría, pérdidas extraordinarias).
- **Rationale**: §7, §4.10.
- **Alternativas**: catálogo plano — dificulta reportes por rubro.

## D2 — Libro diario y derivados

- **Decisión**: `asiento` + `linea_asiento` (cuenta, debe, haber). Validación: Σ debe = Σ haber (≠ ⇒ 422, no se guarda). Libro mayor y balance de comprobación son **consultas** sobre `linea_asiento` (no tablas materializadas; el volumen lo permite). Estado de resultados = agregación de cuentas de ingreso/gasto por periodo.
- **Rationale**: §4.10; Ppio VII.

## D3 — Caja y bancos por sucursal

- **Decisión**: `caja` (1 por sucursal) y `sesion_caja` (apertura con `saldo_inicial`, cierre con `efectivo_contado`, `diferencia` = contado − esperado). `movimiento_caja` (entrada/salida, referencia al documento). Un movimiento con fecha de una sesión cerrada ⇒ rechazado o exige ajuste. `cierre` toma lock (dos cierres concurrentes: el segundo ve cerrada).
- **Rationale**: §4.9, §4.10; Const. Ppio XI.

## D4 — Cheques

- **Decisión**: `cheque` (tipo emitido/recibido, banco, numero, monto, `estado` ∈ {en_cartera, depositado, cobrado, protestado}). Un cheque recibido nace como medio de pago en 008/009 (`pago_ot`/`pago_venta`). `protestar` ⇒ revierte el cobro asociado y reactiva la CxC (o marca la venta impaga).
- **Rationale**: §4.10.

## D5 — CxC y CxP (subledger + aging)

- **Decisión**: `cuenta_por_cobrar` (creada por 009/008) y `cuenta_por_pagar` (derivada de `orden_compra` de 002). `cobro_cxc` / `pago_cxp` (parcial/total). `aging(cuentas)` clasifica el `saldo` por tramos (0-30, 31-60, 61-90, +90). `retencion_fuente` por pago a proveedor (campos, sin cálculo fiscal).
- **Rationale**: §4.10, §4.11.2 (aging), §7 (retenciones).

## D6 — Gastos operativos

- **Decisión**: `gasto` (sucursal, `categoria_gasto_id` (001), monto, fecha, `documento_soporte` en bucket `documentos`, descripcion). Tipos por categoría: local/operativos, personal, otros, mermas_perdidas. Genera asiento automático (D7).
- **Rationale**: §4.10.1.

## D7 — Motor de asiento automático

- **Decisión**: `regla_asiento_automatico` (evento ∈ {venta_confirmada, compra_pagada, gasto_registrado, merma_confirmada, cobro_cxc, pago_cxp}, `cuenta_debe_id`, `cuenta_haber_id`, condición opcional). Al ocurrir el evento (llamada interna de la feature de origen), `asientos_auto.generar(evento, payload)` crea el `asiento`. El de merma usa una cuenta de **pérdida extraordinaria** separada de los gastos operativos.
- **Rationale**: §4.10, §4.12, §5.
- **Alternativas**: hardcodear los asientos — no configurable, viola Ppio VII.

## D8 — Rentabilidad neta por sucursal

- **Decisión**: `rentabilidad_sucursal(periodo, sucursal)` = ingresos (ventas + servicios) − costo de ventas/servicios − gastos operativos de esa sucursal. Versión operativa; el comparativo entre periodos/sucursales es 013.
- **Rationale**: §4.11.2, §4.11.3.

## D9 — Cierre de periodo

- **Decisión**: `periodo_contable` (rango, estado abierto/cerrado). Tras cerrar, un asiento con fecha en el periodo requiere `asiento_ajuste` (nuevo, fechado, auditado); no se edita el original. Un cambio de parámetro configurable **no** recalcula asientos de periodos cerrados.
- **Rationale**: §7 (NIIF), §6 (auditoría); Const. "Parámetros configurables".

## D11 — Gastos: pagado ahora vs. por pagar; CxP genérica

- **Decisión**: `gasto.estado_pago ∈ {pagado, por_pagar}`.
  - `pagado`: se registra un `movimiento_caja` (efectivo) o un movimiento de banco con el `medio_pago`; asiento: debe `gasto`, haber `caja/bancos`.
  - `por_pagar`: se crea una `cuenta_por_pagar` con `origen_tipo = gasto`; asiento: debe `gasto`, haber `cuentas por pagar`. El pago posterior (`pago_cxp`) hace el asiento debe `cuentas por pagar`, haber `caja/bancos`.
- La `cuenta_por_pagar` admite `proveedor_id` (registrado en 002) **o** `beneficiario_id` (acreedor de servicios libre: EMAPA, CNT, arrendador…). Nuevo catálogo `beneficiario`.
- **Rationale**: §4.10 ("Cuentas por pagar a proveedores", "Control de caja y bancos") + §4.10.1 (agua/wifi/arriendo son gastos que a menudo se pagan a crédito); decisión del negocio.
- **Alternativas**: (a) solo asiento manual sin subledger — pierde aging y pagos parciales de esos servicios; (b) modelar los servicios como proveedores en 002 con "orden de compra de servicio" — fuerza el flujo de compras de mercadería sobre un recibo de agua, poco natural.

## D12 — Gastos recurrentes

- **Decisión**: `gasto_recurrente` (categoría, `proveedor_id`|`beneficiario_id`, `monto_estimado`, `frecuencia ∈ {mensual, bimestral, trimestral}`, `proxima_generacion`, `estado ∈ {activo, pausado, cancelado}`). Un scheduler in-proceso (APScheduler, mismo patrón que `compra_programada` de 002 — **sin Airflow**) crea, al llegar `proxima_generacion`, un `gasto` en estado `borrador` con `monto = monto_estimado`, y avanza `proxima_generacion`. Gerencia General ajusta el monto real, elige `pagado`/`por_pagar` y **confirma**; solo al confirmar se generan el asiento y (si aplica) la CxP.
- **Rationale**: agua/wifi/arriendo/teléfono se repiten; da previsibilidad de caja y evita olvidos. §4.10.1.
- **Alternativas**: registro 100% manual cada mes — el negocio pidió automatizar.

## D10 — Alcance

- **Decisión**: sin integración real con el SRI (modelo compatible), sin motor de forecasting/ML, sin nómina detallada (la nómina se registra como gasto de categoría "personal"; solo el bono de técnicos, calculado en 005, se refleja como costo).
- **Rationale**: Const. "Stack"; §7 pendiente; §4.10 ("sin llegar a un ERP contable completo").
