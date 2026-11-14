# Quickstart: Servicio Técnico y Lubricación

**Feature**: `008-servicio-tecnico-lubricacion` | **Phase**: 1

## Prerrequisitos

- 000–007 implementadas; migración `0013_servicio_tecnico` aplicada; `producto_moebius` y parámetros sembrados
- Un reloj vendido por la tienda; un técnico con costo y especialidad; un cliente; MailHog para ver correos

## Escenarios

### V1 — Abrir OT y asignar técnico (US1)
```bash
curl -XPOST /ordenes-trabajo -d '{"numero_serie":"ABC123","cliente_id":1,"motivo":"no da cuerda","tipo_reparacion":"servicio_completo"}'
curl -XPATCH /ordenes-trabajo/1 -d '{"tecnico_id":3}'
```
- **Esperado**: estado `recibido`, sin `fecha_estimada_entrega`; serie de un reloj nunca vendido → advertencia + requiere autorización; reloj `en_transito` → 409; al asignar técnico, el cliente recibe email `tecnico_asignado` (MailHog).

### V2 — Diagnóstico y presupuesto (US1b)
```bash
curl -XPOST /ordenes-trabajo/1/diagnostico -d '{"diagnostico":"barrilete gastado","horas_estimadas":3}'
curl -XPOST /ordenes-trabajo/1/presupuesto -d '{"precio_servicio":180,"lineas":[{"pieza_original_id":50,"pieza_no_original_id":51,"cantidad":1}]}'
curl -XPOST /ordenes-trabajo/1/presupuesto/aprobar -d '{"preferencias":[{"linea":1,"preferencia":"no_original"}],"confirmado_por":"cliente por WhatsApp"}'
```
- **Esperado**: al aprobar se registra `fecha_estimada_entrega`; sin presupuesto aprobado, pasar a `en_reparacion` → 409.

### V3 — Reparación: piezas y lubricación (US2, US3)
```bash
curl -XPOST /ordenes-trabajo/1/piezas -d '{"pieza_id":51,"tipo_elegido":"no_original","cantidad":1}'
curl -XPOST /calibres/10/ficha-lubricacion -d '{"puntos":[{"nombre":"áncora","producto_moebius_codigo":"9415"}]}'
curl -XPOST /ordenes-trabajo/1/lubricacion -d '{"registros":[{"punto":"áncora","producto_usado_codigo":"9010"}]}'
```
- **Esperado**: stock de pieza descontado (nunca negativo); registro de lubricación con `producto_recomendado=9415`, `producto_usado=9010`, `desviacion=true`; consumo de insumo descontado del stock.

### V4 — Costeo y margen (US4) 🔒
```bash
curl -XPOST /ordenes-trabajo/1/horas -d '{"horas":3}'
curl /ordenes-trabajo/1/costeo -H "Authorization: Bearer <admin>"
```
- **Esperado**: `costo_interno = MO(10×3) + piezas + insumos`; `precio_sugerido = costo × (1+margen_objetivo)`; `margen_real = precio_cobrado − costo_interno`. Sin rol admin, el endpoint de costeo no expone estos valores.

### V5 — Descuento con margen mínimo (US4) 🔒
```bash
curl -XPOST /ordenes-trabajo/1/descuento -d '{"cupon_codigo":"PLATA10"}'
```
- **Esperado**: usa `shared/descuentos`; si el margen cae bajo el mínimo → bloquea o requiere autorización de Gerencia General; `aplicacion_descuento` registrada en la OT.

### V6 — Cobro al retiro y entrega (US5)
```bash
curl -XPOST /ordenes-trabajo/1/estado -d '{"estado":"listo"}'
curl -XPOST /ordenes-trabajo/1/entregar -d '{}'                          # 409: saldo > 0
curl -XPOST /ordenes-trabajo/1/pagos -d '{"medio_pago":"efectivo","monto":100}'
curl -XPOST /ordenes-trabajo/1/pagos -d '{"medio_pago":"tarjeta","monto":80}'
curl -XPOST /ordenes-trabajo/1/entregar -d '{}'                          # 200
```
- **Esperado**: sin saldo 0 → 409; con pago completo (mixto) → `entregado`, `fecha_real_entrega`, `documento_ot` + `certificado_garantia` en `comprobantes-venta` (sin costos), `evento_serie(servicio)`, recálculo de nivel (006), notificación a 014. Entrega a crédito solo con autorización de Gerencia General → CxC (010).

### V7 — Daño en servicio (US7)
```bash
curl -XPOST /ordenes-trabajo/1/reportar-dano -d '{"descripcion":"rayón en la caja","costo_estimado":120}'
```
- **Esperado**: payload para `POST /mermas` (011, `dano_servicio`) vinculado a OT y técnico.

### V8 — Informe de servicios (US6)
```bash
curl "/informe-servicios?tecnico_id=3&desde=2026-09-01&hasta=2026-09-30"
```
- **Esperado**: filas con cliente, fecha, reloj, trabajo, repuestos, precio; exportable CSV/Excel/PDF.

## Contratos

- [`contracts/servicio-tecnico.openapi.yaml`](./contracts/servicio-tecnico.openapi.yaml)
- [`contracts/lubricacion.openapi.yaml`](./contracts/lubricacion.openapi.yaml)

## Criterio de "listo"

V1–V8 pasan; **pruebas de margen del servicio, margen mínimo tras descuentos y consumo de insumos verdes (Const. Ppio IX)**.
