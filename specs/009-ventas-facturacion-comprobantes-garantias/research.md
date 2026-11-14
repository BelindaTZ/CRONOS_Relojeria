# Research: Ventas, Comprobantes y Garantías

**Feature**: `009-ventas-facturacion-comprobantes-garantias` | **Phase**: 0 | **Date**: 2026-09-10

Sin `NEEDS CLARIFICATION` (consumidor final resuelto por el negocio).

## D1 — Orden de venta y confirmación

- **Decisión**: `orden_venta` (`borrador → confirmada → anulada`). En `borrador` se arman líneas, descuentos y pagos previstos. `confirmar` (transacción atómica): valida stock/disponibilidad, aplica descuento vía `shared/descuentos` (chequea margen mínimo), da de baja stock (relojes → `vendido` + `evento_serie(venta)`; piezas → `movimiento_stock_pieza(venta_suelta)`), registra pagos, genera CxC del saldo, genera PDFs, dispara recálculo de nivel (006), vincula cita (007).
- **Rationale**: Const. Ppio II; §2.2.

## D2 — Cálculo del margen de la venta

- **Decisión**: por línea, `margen_linea = precio_final − costo` (costo = `reloj.costo_adquisicion` o `pieza.costo_adquisicion × cantidad`). `margen_venta = Σ margen_linea`. `precio_final` es el ya descontado (`shared/descuentos`). Restringido a rol administrativo; nunca en el comprobante.
- **Rationale**: §4.8.2, §4.11.2 ("Margen por reloj vendido").

## D3 — Descuentos y cupones

- **Decisión**: se aplica **un** descuento **o** **un** cupón por venta (exclusivos, 006). El cupón se consume con lock (`POST /_internal/cupones/consumir`). Si `decision = requiere_autorizacion`, la venta no se confirma sin `autorizacion_margen_minimo` de Gerencia General.
- **Rationale**: §4.8.2; decisión del negocio.

## D4 — Medios de pago

- **Decisión**: catálogo `medio_pago` de 001 (efectivo, transferencia, cheque, tarjeta). `shared/pagos` (008) registra uno o varios pagos por venta. Pago total ⇒ sin CxC; pago parcial ⇒ CxC por el saldo (010). Cheque como medio; su ciclo (protesto) lo maneja 010.
- **Rationale**: Const. "Stack"; §4.10.

## D5 — Garantías

- **Decisión**: `garantia_venta` por transacción, dos filas: `fabrica` (periodo de la marca) y `tienda` (periodo configurable por tipo de producto, §9.2). Fechas de inicio/fin. El certificado de garantía/autenticidad las incluye.
- **Rationale**: §7, §2.3; Const. Ppio III (certificado adoptado).

## D6 — Comprobante y certificado

- **Decisión**: `shared/pdf` (008) renderiza `comprobante_venta` y `certificado_garantia_autenticidad` (vinculado al número de serie) a `comprobantes-venta`. Sin costos/márgenes. Modelo compatible con SRI: campos de identificación fiscal del cliente, secuencial, impuestos desglosados (aunque no se transmita al SRI en esta fase).
- **Rationale**: Const. Ppio III; §7.

## D7 — Anulación / devolución

- **Decisión**: `anular(venta, motivo)`: reingresa stock (relojes → `disponible` + `evento_serie(reingreso)`; piezas → `movimiento_stock_pieza(ajuste)`), revierte `margen_venta`, revierte el nivel de fidelización del cliente (recálculo), marca la CxC como anulada, genera `documento_anulacion`. No se puede anular si el reloj ya entró a servicio técnico (o exige resolver la OT primero).
- **Rationale**: §6, §4.8.2.

## D8 — Consumidor final

- **Decisión**: `orden_venta.cliente_id` obligatorio; para venta **solo de piezas sueltas** cuyo total < `monto_max_consumidor_final` (parámetro), se admite el cliente genérico `es_consumidor_final` (006). Venta de reloj o total ≥ el monto ⇒ cliente identificado obligatorio.
- **Rationale**: decisión del negocio.

## D9 — Consulta operativa

- **Decisión**: `GET /ventas-dia?fecha=&sucursal_id=` con total y margen del día (margen solo rol administrativo). El analítico por marca/modelo/periodo es 013.
- **Rationale**: §4.11.2 (versión operativa).
