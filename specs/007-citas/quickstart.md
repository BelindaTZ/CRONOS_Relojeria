# Quickstart: Gestión de Citas

**Feature**: `007-citas` | **Phase**: 1

## Prerrequisitos

- 000, 001, 006 implementadas; migración `0012_citas` aplicada; catálogo `canal_cita` con `correo_electronico` y `presencial`
- Un cliente creado; usuario con permisos en `citas`

## Escenarios

### V1 — Registrar una cita (US1)
```bash
curl -XPOST /citas -d '{"cliente_id":1,"sucursal_id":1,"canal_cita_id":1,"motivo":"servicio_tecnico","fecha_preferida":"2026-09-15T10:00:00","observaciones":"cambio de correa"}'
```
- **Esperado**: estado `pendiente`; sin `cliente_id` existente → 422; canal fuera del catálogo → 422.

### V2 — Confirmar / cancelar / atender (US2)
```bash
curl -XPOST /citas/1/confirmar -d '{"fecha_confirmada":"2026-09-15T10:30:00"}'
curl -XPOST /citas/1/cancelar -d '{"motivo":"cliente reprograma"}'   # sobre una confirmada
```
- **Esperado**: `confirmar` fija fecha; `cancelar` exige motivo (modal); no se puede cancelar una `atendida`; historial de estados registrado.

### V3 — Solape (US2)
- Confirmar dos citas de la misma sucursal a las 10:00 y 10:15.
- **Esperado**: la segunda confirmación devuelve `warning: solape` sin bloquear.

### V4 — Agenda (US3)
```bash
curl "/agenda?rango=dia&fecha=2026-09-15"
curl "/agenda?rango=semana&fecha=2026-09-15" -H "Authorization: Bearer <gerente_A>"
```
- **Esperado**: citas de la sucursal del usuario ordenadas por hora; Gerencia General puede pasar `sucursal_id`.

### V5 — Atender y vincular (US4)
```bash
curl -XPOST /citas/1/atender -d '{}'
```
- **Esperado**: como no hay venta/OT, la respuesta trae `accion: {tipo:"crear_ot", cliente_id:1, cita_id:1}`; el frontend abre el flujo de 008 con el cliente cargado; al cerrar la OT, 008 vincula la cita. Alternativa: `atender` con `orden_trabajo_id` existente → vínculo directo.

### V6 — Conversión operativa (US6)
```bash
curl "/citas/conversion?desde=2026-09-01&hasta=2026-09-30"
```
- **Esperado**: atendidas con transacción / atendidas.

### V7 — Datos para 014
```bash
curl "/_internal/citas/confirmadas-pendientes-recordatorio?antelacion=24h"
```
- **Esperado**: citas confirmadas dentro de la ventana; una cita cancelada después ya no aparece.

## Contratos

- [`contracts/citas.openapi.yaml`](./contracts/citas.openapi.yaml)

## Criterio de "listo"

V1–V7 pasan; pruebas de ciclo de estados, vínculo y agenda verdes; scope por sucursal verificado.
