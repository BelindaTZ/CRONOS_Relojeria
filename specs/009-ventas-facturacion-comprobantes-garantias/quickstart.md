# Quickstart: Ventas, Comprobantes y Garantías

**Feature**: `009-ventas-facturacion-comprobantes-garantias` | **Phase**: 1

## Prerrequisitos

- 000–008 implementadas; migración `0014_ventas` aplicada; parámetros de garantía y `monto_max_consumidor_final` sembrados
- Un reloj disponible con costo/precio; un cliente; MailHog; usuario con permiso administrativo (para ver margen)

## Escenarios

### V1 — Registrar y confirmar una venta (US1) 🔒
```bash
curl -XPOST /ventas -d '{"cliente_id":1,"sucursal_id":1,"lineas":[{"item_tipo":"reloj","reloj_id":10}]}'
curl -XPOST /ventas/1/pagos -d '{"medio_pago":"efectivo","monto":4000}'
curl -XPOST /ventas/1/pagos -d '{"medio_pago":"transferencia","monto":4500}'
curl -XPOST /ventas/1/confirmar -d '{}'
```
- **Esperado**: al confirmar, el reloj sale del stock (`vendido`), `evento_serie(venta)`, garantías registradas, comprobante + certificado en `comprobantes-venta` (sin costos), recálculo de nivel (006). Reloj `en_transito` → 409.

### V2 — Margen de la venta (US2) 🔒
```bash
curl /ventas/1 -H "Authorization: Bearer <admin>"     # incluye margen_venta
curl /ventas/1 -H "Authorization: Bearer <no_admin>"  # sin margen_venta
```
- **Esperado**: `margen_venta = Σ (precio_final − costo)`; oculto sin rol administrativo.

### V3 — Descuento con margen mínimo (US2) 🔒
```bash
curl -XPOST /ventas/2/descuento -d '{"descuento_id":5}'   # 30% sobre un reloj con poco margen
```
- **Esperado**: `shared/descuentos` calcula; si el margen cae bajo el mínimo → `bloquear`/`requiere_autorizacion`; con autorización de Gerencia General registrada → confirmable. Descuento + cupón a la vez → 422.

### V4 — Garantías (US3)
```bash
curl /ventas/1/garantias
```
- **Esperado**: dos filas (`fabrica`, `tienda`) con periodos y fechas; el certificado las incluye.

### V5 — Comprobante y certificado (US4)
```bash
curl /ventas/1/comprobantes -H "Authorization: Bearer <vendedor>"
curl <url_comprobante>                                 # sin token → 403
```
- **Esperado**: PDFs accesibles solo autenticado y con permiso; no muestran costos/márgenes.

### V6 — Venta a crédito y CxC (US5)
```bash
curl -XPOST /ventas -d '{"cliente_id":1,"lineas":[{"item_tipo":"reloj","reloj_id":11}]}'
curl -XPOST /ventas/3/pagos -d '{"medio_pago":"efectivo","monto":3000}'
curl -XPOST /ventas/3/confirmar -d '{}'
curl /cuentas-por-cobrar?cliente_id=1
```
- **Esperado**: CxC por el saldo exacto; 010 la consume para aging.

### V7 — Anulación (US6)
```bash
curl -XPOST /ventas/1/anular -d '{"motivo":"cliente se arrepiente"}'
```
- **Esperado**: reloj vuelve a `disponible` + `evento_serie(reingreso)`; margen revertido; nivel de fidelización recalculado; CxC `anulada`; `documento_anulacion`. Si el reloj ya está en OT → 409.

### V8 — Consumidor final (US)
```bash
curl -XPOST /ventas -d '{"cliente_id":null,"lineas":[{"item_tipo":"pieza","pieza_id":5,"cantidad":1}]}'
```
- **Esperado**: permitido si total < `monto_max_consumidor_final` y solo piezas; con un reloj en las líneas o total ≥ el monto → 422 (exige cliente identificado).

## Contratos

- [`contracts/ventas.openapi.yaml`](./contracts/ventas.openapi.yaml)

## Criterio de "listo"

V1–V8 pasan; **pruebas de margen de venta y margen mínimo tras descuentos verdes (Const. Ppio IX)**.
