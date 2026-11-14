# Quickstart: Notificaciones Automatizadas por Email

**Feature**: `014-notificaciones-automatizadas-email` | **Phase**: 1

## Prerrequisitos

- 000, 001, 006, 007, 008 implementadas; migración `0017_notificaciones`; plantillas y parámetros sembrados
- MailHog (o SendGrid sandbox) configurado en `.env`; `worker.py` corriendo (o job del compose)

## Escenarios

### V1 — Aviso de cambio de estado de OT (US1)
```bash
# en 008: cambiar una OT a "listo"
curl /envios?tipo=ot_estado&disparo_origen_id=<ot>
# esperar el poller del worker
```
- **Esperado**: se crea un `envio` `encolado`; el worker lo envía (MailHog muestra el correo con plantilla); estado → `enviado` → `entregado` (webhook). Cliente sin email → `sin_destinatario` sin reintentos. Dos cambios rápidos al mismo estado → un solo envío (dedup).

### V2 — Cupón / cambio de nivel (US2)
```bash
# en 006: emitir un cupón a un cliente
curl /envios?tipo=cupon
```
- **Esperado**: email con código y vigencia; al subir de nivel, email con los beneficios del nuevo nivel.

### V3 — Recordatorio de cita (US3)
```bash
# en 007: confirmar una cita para dentro de 2 días
curl /envios?tipo=recordatorio_cita
```
- **Esperado**: `envio` `encolado` con `proxima_ejecucion = fecha_confirmada − 24h` (parámetro). Al cumplirse el plazo, el worker lo envía. Si la cita se cancela antes → el `envio` pasa a `cancelado` (`motivo_estado = cita_cancelada`).

### V4 — Seguimiento y reintento (US4)
```bash
curl /envios?estado=rebotado
curl -XPOST /envios/5/reintentar
```
- **Esperado**: el panel muestra el estado de cada envío; reintento manual disponible para `fallido`/`rebotado`. Con el proveedor caído, los `encolado` se acumulan y se envían al recuperarse (0 pérdidas).

### V5 — Plantillas (US5)
```bash
curl -XPUT /plantillas/recordatorio_cita -d '{"asunto":"Tu cita en {{tienda}}","cuerpo":"<h1>...</h1>"}'
curl -XPOST /plantillas/recordatorio_cita/preview -d '{"contexto":{"tienda":"CRONOS","fecha":"..."}}'
```
- **Esperado**: solo Gerencia General / delegado edita; preview con datos de ejemplo; versión incrementa; auditado.

### V6 — Opt-out (US5)
```bash
curl -XPUT /preferencias/cliente/1 -d '{"tipo_comunicacion":"cupon","opt_in":false}'
# emitir un cupón a ese cliente
curl /envios?cliente_id=1&tipo=cupon
```
- **Esperado**: el cupón se crea igual, pero el `envio` queda `cancelado` (`motivo_estado = opt_out`). Un tipo crítico (`password_temporal`) ignora el opt-out.

### V7 — Desacople del camino transaccional (US)
```bash
# apagar el proveedor de email, confirmar una venta en 009
```
- **Esperado**: la venta se confirma normal y rápido; el `envio` queda `encolado`; nada falla.

### V8 — Reporte de envíos (US7)
```bash
curl "/reportes/envios?desde=2026-09-01&hasta=2026-09-30"
```
- **Esperado**: envíos por tipo y estado; filtros reactivos; paginado.

## Contratos

- [`contracts/notificaciones.openapi.yaml`](./contracts/notificaciones.openapi.yaml)

## Criterio de "listo"

V1–V8 pasan; pruebas de disparadores, cola/reintentos, dedup, opt-out y desacople verdes.
