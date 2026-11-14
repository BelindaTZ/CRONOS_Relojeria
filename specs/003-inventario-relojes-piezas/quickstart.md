# Quickstart: Inventario de Relojes y Piezas

**Feature**: `003-inventario-relojes-piezas` | **Phase**: 1

## Prerrequisitos

- 000, 001, 002 implementadas; migración `0008_inventario` aplicada; parámetros sembrados
- Usuario con permisos en `inventario_relojes` y `piezas`; un usuario con permiso `ver_costos`; un rol elevado

## Escenarios

### V1 — Alta de unidad con foto (US1)
```bash
curl -XPOST /relojes -F 'data={"numero_serie":"ABC123","marca":"Omega","referencia":"310.30.42","calibre_codigo":"3861","estado_producto":"nuevo","precio_venta":8500,"proveedor_id":1,"sucursal_actual_id":1}' -F 'foto=@reloj.jpg'
curl /relojes/ABC123
```
- **Esperado**: creado; `evento_serie` tipo `ingreso`; foto recuperable desde `reloj-imagenes`; `numero_serie` duplicado → 409.

### V2 — Estado de inventario (US2)
```bash
curl "/relojes?marca=Omega&sucursal_id=1&disponibilidad=disponible&page=1"
```
- **Esperado**: solo unidades disponibles de la sucursal 1, paginado; búsqueda por serie/calibre también filtra.

### V3 — Restricción de costo (US6)
```bash
curl /relojes/ABC123 -H "Authorization: Bearer <sin_ver_costos>"   # sin campo costo_adquisicion
curl /relojes/ABC123 -H "Authorization: Bearer <con_ver_costos>"   # con costo_adquisicion
```

### V4 — Piezas y stock no negativo (US3)
```bash
curl -XPOST /piezas -d '{"codigo":"9010","descripcion":"Moebius 9010","tipo":"original","perecedera":true,"stock_minimo":2}'
curl -XPOST /piezas/9010/movimientos -d '{"sucursal_id":1,"tipo":"consumo_ot","cantidad":-1}'   # sin stock → 409
```
- **Esperado**: consumo sin stock → 409; el stock nunca queda negativo (probar concurrencia).

### V5 — Lote y caducidad (US4b)
```bash
curl -XPOST /piezas/9010/movimientos -d '{"sucursal_id":1,"tipo":"ingreso","cantidad":10,"lote":"L-2411","fecha_caducidad":"2026-10-05"}'
curl /alertas-stock?tipo=caducidad_proxima
```
- **Esperado**: ingreso sin lote/fecha para pieza perecedera → 422; con umbral 30 días y caducidad cercana → alerta `caducidad_proxima`; consumir lote vencido advierte y ofrece merma (011).

### V6 — Alertas de stock y reposición (US4)
- Llevar un modelo a 1 unidad (vender/transferir/merma mock).
- **Esperado**: alerta `ultima_unidad`; su acción "Reponer" llama `POST /ordenes-compra/prellenar` (002) y abre el borrador con proveedor/modelo/cantidad; superar el máximo → alerta `cerca_maximo` sin bloquear.

### V7 — Historial por número de serie (US5)
```bash
curl /relojes/ABC123/historial
```
- **Esperado**: eventos en orden cronológico; intento de editar un evento → no existe endpoint (append-only).

### V8 — Corrección con rol elevado (US6)
```bash
curl -XPATCH /relojes/ABC123 -H "Authorization: Bearer <vendedor>" -d '{"numero_serie":"ABC124","motivo":"tipeo"}'   # 403
curl -XPATCH /relojes/ABC123 -H "Authorization: Bearer <gerencia>" -d '{"numero_serie":"ABC124","motivo":"tipeo"}'   # 200
```
- **Esperado**: 403 rol normal; 200 + `evento_serie(correccion)` + auditoría; el historial previo se conserva bajo la nueva serie.

## Contratos

- [`contracts/inventario.openapi.yaml`](./contracts/inventario.openapi.yaml)
- [`contracts/piezas.openapi.yaml`](./contracts/piezas.openapi.yaml)

## Criterio de "listo"

V1–V8 pasan; pruebas de stock no negativo (concurrencia), alertas e inmutabilidad del historial verdes.
