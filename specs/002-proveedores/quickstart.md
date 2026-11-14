# Quickstart: Proveedores y Órdenes de Compra

**Feature**: `002-proveedores` | **Phase**: 1

## Prerrequisitos

- 000 y 001 implementadas y corriendo; migraciones `0007_*` aplicadas
- Un usuario con permisos en el módulo `proveedores` y un usuario "Gerencia General" (rol elevado)

## Escenarios

### V1 — Ficha de proveedor (US1)
```bash
curl -XPOST /proveedores -d '{"razon_social":"Moebius EC","ruc_nit":"1790011223001","tipos":["lubricantes"],"condiciones_pago":"30 días","plazo_entrega_dias":15}'
curl /proveedores?q=moebius
```
- **Esperado**: creado; búsqueda por nombre/RUC/email lo encuentra. Adjuntar un PDF de certificado → se guarda en `documentos` y se recupera solo autenticado.

### V2 — Orden de compra y recepción (US2)
```bash
curl -XPOST /ordenes-compra -d '{"proveedor_id":1,"sucursal_destino_id":1,"fecha_pactada":"2026-09-25","lineas":[{"item_tipo":"pieza","item_ref":"9010","cantidad":5,"costo_unitario":45.00}]}'
curl -XPOST /ordenes-compra/1/emitir
curl -XPOST /ordenes-compra/1/recepciones -d '{"fecha_real":"2026-09-27","lineas":[{"linea_orden_compra_id":1,"cantidad_recibida":3}]}'
```
- **Esperado**: orden `parcial` (3 de 5); historial de compras del proveedor la muestra; `desfase_dias = 2`.

### V3 — Cumplimiento de plazos → calificación (US4)
- Registrar 3 recepciones (a tiempo, +2 días, +5 días).
- **Esperado**: `proveedor.indicador_plazos_dias` = promedio; `calificacion.nota_plazos` derivada; `nota_calidad`/`nota_soporte` editables manualmente.

### V4 — Compra programada (US5)
```bash
curl -XPOST /compras-programadas -d '{"proveedor_id":1,"sucursal_destino_id":1,"frecuencia":"mensual","plantilla_lineas":[{"item_tipo":"pieza","item_ref":"9010","cantidad":10,"costo_unitario":45}]}'
# forzar el scheduler (endpoint interno de prueba o avanzar el reloj)
curl -XPOST /_internal/scheduler/tick
curl /ordenes-compra?tipo=programada&estado=borrador
```
- **Esperado**: se genera una orden en `borrador`; `proxima_generacion` avanza un mes; pausar la programada detiene la generación.

### V5 — Prellenado para reposición (US7)
```bash
curl -XPOST /ordenes-compra/prellenar -d '{"proveedor_id":1,"item_tipo":"pieza","item_ref":"9010","cantidad_sugerida":10}'
```
- **Esperado**: devuelve el borrador con proveedor, ítem y cantidad puestos, editable. (003 invocará esto desde su alerta.)

### V6 — Corrección con rol elevado (US6)
```bash
curl -XPATCH /ordenes-compra/1 -H "Authorization: Bearer <vendedor>" -d '{"lineas":[{"id":1,"costo_unitario":50}],"motivo":"error de digitación"}'   # 403
curl -XPATCH /ordenes-compra/1 -H "Authorization: Bearer <gerencia>" -d '{"lineas":[{"id":1,"costo_unitario":50}],"motivo":"error de digitación"}'   # 200
```
- **Esperado**: 403 para rol no elevado; 200 + auditoría con antes/después para rol elevado.

### V7 — Perecederos con lote (US2 + 003)
- Recibir una línea de un ítem perecedero sin `lote`/`fecha_caducidad` → 422; con ambos → 200 y se propaga a 003 (`lote_pieza`).

## Contratos

- [`contracts/proveedores.openapi.yaml`](./contracts/proveedores.openapi.yaml)

## Criterio de "listo"

V1–V7 pasan; pruebas de cumplimiento de plazos y de generación de programadas verdes; toda corrección auditada.
