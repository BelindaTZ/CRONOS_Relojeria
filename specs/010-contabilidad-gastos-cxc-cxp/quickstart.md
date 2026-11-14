# Quickstart: Contabilidad, Gastos, CxC y CxP

**Feature**: `010-contabilidad-gastos-cxc-cxp` | **Phase**: 1

## Prerrequisitos

- 000–009 implementadas; migración `0015_contabilidad`; plan de cuentas y reglas de asiento sembradas
- Usuarios: "Gerencia General" (CRUD), "Gerente de Sucursal" (solo consultar), un vendedor (sin acceso)

## Escenarios

### V1 — Libro diario y derivados (US1)
```bash
curl -XPOST /asientos -d '{"fecha":"2026-09-10","glosa":"ajuste","lineas":[{"cuenta":"1101","debe":100},{"cuenta":"4101","haber":100}]}'
curl -XPOST /asientos -d '{"fecha":"2026-09-10","glosa":"malo","lineas":[{"cuenta":"1101","debe":100},{"cuenta":"4101","haber":90}]}'   # 422
curl "/balance?periodo=2026-09"
```
- **Esperado**: asiento cuadrado se guarda; descuadrado → 422; balance: Σ debe = Σ haber.

### V2 — Caja por sucursal (US2)
```bash
curl -XPOST /caja/1/sesiones -d '{"saldo_inicial":200}'
curl -XPOST /caja/1/movimientos -d '{"tipo":"entrada","monto":500,"medio_pago":"efectivo"}'
curl -XPOST /caja/1/sesiones/actual/cerrar -d '{"efectivo_contado":690}'
```
- **Esperado**: `diferencia = 690 − 700 = −10` registrada; movimiento con fecha de sesión cerrada → rechazado.

### V3 — CxC de una venta (US3)
```bash
# (009) confirmar una venta a crédito
curl "/cxc?cliente_id=1&estado=pendiente"
curl -XPOST /cxc/1/cobros -d '{"monto":1000,"medio_pago":"transferencia"}'
curl "/cxc/aging?fecha_corte=2026-09-30"
```
- **Esperado**: CxC por el saldo de la venta; cobro parcial reduce saldo; aging clasifica por tramos.

### V4 — CxP de una compra (US4)
```bash
curl "/cxp?proveedor_id=1"
curl -XPOST /cxp/1/pagos -d '{"monto":800,"medio_pago":"cheque","retencion_fuente":{"tipo":"porcentaje","valor":0.01}}'
```
- **Esperado**: CxP derivada de la orden de compra; pago con retención registrado.

### V5 — Gasto por sucursal y categoría; pagado vs. por pagar (US5)
```bash
# gasto pagado ahora
curl -XPOST /gastos -F 'data={"sucursal_id":1,"categoria_gasto_id":3,"monto":450,"fecha":"2026-09-05","descripcion":"arriendo","estado_pago":"pagado","medio_pago":"transferencia"}' -F 'soporte=@arriendo.pdf'
# gasto de agua por pagar a un beneficiario
curl -XPOST /beneficiarios -d '{"nombre":"EMAPA","tipo_servicio":"agua"}'
curl -XPOST /gastos -d '{"sucursal_id":1,"categoria_gasto_id":3,"monto":38.50,"fecha":"2026-09-04","descripcion":"agua sept","estado_pago":"por_pagar","beneficiario_id":1}'
curl -XPOST /gastos -d '{"sucursal_id":1,"monto":100}'   # 422: sin categoría
curl -XPOST /gastos -H "Authorization: Bearer <gerente_suc>" -d '{...}'   # 403
```
- **Esperado**: el arriendo genera movimiento de banco + asiento; el agua genera una **CxP** (`origen=gasto`, beneficiario EMAPA) que aparece en `GET /cxp` y en el aging; sin categoría → 422; Gerente de Sucursal → 403 (solo consulta).
```bash
curl "/cxp?estado=pendiente"
curl -XPOST /cxp/<id>/pagos -d '{"monto":38.50,"medio_pago":"efectivo"}'
```
- **Esperado**: la CxP del agua se salda con su pago.

### V5b — Gasto recurrente (US5b)
```bash
curl -XPOST /gastos-recurrentes -d '{"categoria_gasto_id":3,"beneficiario_id":2,"descripcion":"internet","monto_estimado":35,"frecuencia":"mensual","sucursal_id":1}'
curl -XPOST /_internal/scheduler/tick     # o avanzar el reloj al ciclo
curl "/gastos?estado=borrador"
curl -XPOST /gastos/<id>/confirmar -d '{"monto":36.20,"estado_pago":"por_pagar"}'
```
- **Esperado**: se genera un gasto en `borrador` con el monto estimado; Gerencia ajusta el monto real y lo confirma; recién ahí se generan el asiento y la CxP; pausar el recurrente detiene la generación.

### V6 — Asiento automático y rentabilidad (US6)
```bash
# confirmar una venta en 009 → verificar asiento
curl "/asientos?origen=venta"
curl "/rentabilidad-sucursal?periodo=2026-09&sucursal_id=1"
```
- **Esperado**: la venta generó su asiento; la rentabilidad descuenta los gastos operativos de la sucursal, no solo el margen bruto.

### V7 — Cheque protestado (US7)
```bash
curl -XPOST /cheques/5/protestar -d '{}'
```
- **Esperado**: el cobro asociado se revierte y la CxC se reactiva.

### V8 — Cierre de periodo (US9)
```bash
curl -XPOST /periodos/2026-09/cerrar -d '{}'
curl -XPOST /asientos -d '{"fecha":"2026-09-20",...}'   # requiere asiento de ajuste
```
- **Esperado**: tras cerrar, un asiento con fecha del periodo exige `ajuste_de_asiento_id`; el original no se edita.

### V9 — RBAC
```bash
curl /asientos -H "Authorization: Bearer <vendedor>"           # 403
curl -XPOST /gastos -H "Authorization: Bearer <gerente_suc>"    # 403 (solo consultar)
```

## Contratos

- [`contracts/contabilidad.openapi.yaml`](./contracts/contabilidad.openapi.yaml)

## Criterio de "listo"

V1–V9 pasan; pruebas de asientos balanceados, aging, arqueo, protesto y rentabilidad por sucursal verdes.
