# Quickstart: Multi-Sucursal y Traslados de Inventario

**Feature**: `004-multisucursal-traslados` | **Phase**: 1

## Prerrequisitos

- 000, 001, 003 implementadas; migración `0009_traslados` aplicada
- 2 sucursales activas con inventario; usuarios: uno "gerente de sucursal A", uno "Gerencia General"

## Escenarios

### V1 — Enviar una transferencia (US1)
```bash
curl -XPOST /transferencias -d '{"sucursal_origen_id":1,"sucursal_destino_id":2,"motivo":"balanceo de stock","lineas":[{"item_tipo":"reloj","reloj_id":10},{"item_tipo":"pieza","pieza_id":5,"cantidad_enviada":3}]}'
curl -XPOST /transferencias/1/enviar -d '{"responsable_envio_id":7}'
curl /relojes/ABC123     # disponibilidad = en_transito
```
- **Esperado**: estado `en_transito`; reloj no disponible en origen; origen == destino → 422.

### V2 — Ítem en tránsito no operable (US4-analogo)
```bash
curl -XPOST /ventas -d '{"lineas":[{"item_tipo":"reloj","reloj_id":10}]}'   # (009) → 409 en tránsito
```
- **Esperado**: venta y apertura de OT rechazan el reloj en tránsito; el stock de la pieza no cuenta para ninguna sucursal.

### V3 — Recibir (US2)
```bash
curl -XPOST /transferencias/1/recibir -d '{"responsable_recepcion_id":9,"lineas":[{"linea_transferencia_id":1,"cantidad_recibida":1},{"linea_transferencia_id":2,"cantidad_recibida":3}]}'
```
- **Esperado**: estado `recibida`; reloj con `sucursal_actual_id=2`, `evento_serie(transferencia)`; +3 al stock de la pieza en sucursal 2, ya descontado de la 1.

### V4 — Discrepancia (US2)
```bash
curl -XPOST /transferencias/2/recibir -d '{"lineas":[{"linea_transferencia_id":X,"cantidad_recibida":2}]}'   # se enviaron 3
```
- **Esperado**: estado `parcial`; `discrepancia_transferencia` con `cantidad_faltante=1`; se ofrece crear merma (011, `dano_transito`); el faltante no reingresa.

### V5 — Cancelar en tránsito (US4)
```bash
curl -XPOST /transferencias/3/cancelar -d '{"motivo":"envío suspendido"}'
```
- **Esperado**: ítems vuelven a `disponible` en origen; auditoría.

### V6 — Historial (US3)
```bash
curl /relojes/ABC123/historial | jq '.[] | select(.tipo=="transferencia")'
curl "/transferencias?sucursal_id=1&page=1"
```
- **Esperado**: cada movimiento con origen, destino, fecha, motivo; listado con filtros reactivos y paginación.

### V7 — Visibilidad por sucursal (US3/US5)
```bash
curl /relojes -H "Authorization: Bearer <gerente_A>"   # solo sucursal A
curl "/relojes?sucursal_id=2" -H "Authorization: Bearer <gerencia>"   # consolidado/filtrable
```

### V8 — Una sola sucursal
- Con solo la sucursal 1 activa: `POST /transferencias` → 422 (sin destino posible); el resto de la app funciona.

## Contratos

- [`contracts/traslados.openapi.yaml`](./contracts/traslados.openapi.yaml)

## Criterio de "listo"

V1–V8 pasan; pruebas de integridad de stock en ambas sucursales, no-operabilidad en tránsito y cancelación reversible verdes.
