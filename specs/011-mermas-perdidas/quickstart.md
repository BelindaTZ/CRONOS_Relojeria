# Quickstart: Mermas y Pérdidas

**Feature**: `011-mermas-perdidas` | **Phase**: 1

## Prerrequisitos

- 000–010 implementadas; migración `0016_mermas`; parámetro `umbral_merma_autorizacion` y cuenta de pérdida extraordinaria sembrados
- Un reloj y una pieza en stock; usuarios: Técnico, Gerente de Sucursal, Gerencia General

## Escenarios

### V1 — Reportar una merma (US1) 🔒
```bash
curl -XPOST /mermas -d '{"bien_tipo":"reloj","reloj_id":12,"causa":"dano_tienda","fecha_evento":"2026-09-08","sucursal_id":1}'
```
- **Esperado**: estado `en_evaluacion`; `costo_perdida` = `reloj.costo_adquisicion` (oculto sin rol administrativo); merma sobre un reloj vendido → 409; merma de pieza > stock → 422.

### V2 — Soporte documental (US1)
```bash
curl -XPOST /mermas/1/documentos -F 'tipo=acta' -F 'archivo=@acta.pdf'
```
- **Esperado**: guardado en bucket `documentos`, recuperable solo autenticado.

### V3 — Autorización de baja sobre umbral (US2)
```bash
curl -XPOST /mermas/1/estado -d '{"estado":"dado_de_baja"}' -H "Authorization: Bearer <gerente_suc>"   # 409 si costo > umbral
curl -XPOST /mermas/1/autorizar-baja -H "Authorization: Bearer <gerencia>" -d '{"observacion":"acta revisada"}'
curl -XPOST /mermas/1/estado -d '{"estado":"dado_de_baja"}'
```
- **Esperado**: sobre el umbral, `dado_de_baja` sin autorización → 409; con `autorizacion_baja` de Gerencia General → procede; registra quién autorizó y cuándo.

### V4 — Baja y asiento (US3) 🔒
```bash
curl /mermas/1
curl "/asientos?origen=merma" -H "Authorization: Bearer <contador>"
curl /relojes/<serie>/historial
```
- **Esperado**: reloj `dado_de_baja` + `evento_serie(baja)`; historial conservado; asiento de **pérdida extraordinaria** en 010 (cuenta separada de gastos operativos).

### V5 — Ciclo y reingreso (US4)
```bash
curl -XPOST /mermas/2/estado -d '{"estado":"reparado_reingresado"}'
```
- **Esperado**: el bien vuelve al inventario activo + `evento_serie(reingreso)`; la merma queda en el historial.

### V6 — Merma derivada de servicio / transferencia (US5)
```bash
# desde 008
curl -XPOST /ordenes-trabajo/5/reportar-dano -d '{"descripcion":"rayón"}'   # devuelve payload
curl -XPOST /mermas -d '<payload con causa dano_servicio, orden_trabajo_id, tecnico_id>'
```
- **Esperado**: merma vinculada a la OT y al técnico, sin sanción automática; análogamente `dano_transito` desde 004.

### V7 — Reclamo (US4)
```bash
curl -XPOST /mermas/1/reclamo -d '{"destino":"proveedor","proveedor_id":1}'
curl -XPATCH /mermas/1/reclamo -d '{"estado":"aceptado","monto_recuperado":300}'
```

### V8 — Reporte de mermas (US6)
```bash
curl "/reportes/mermas?desde=2026-09-01&hasta=2026-09-30"
```
- **Esperado**: agrupado por causa con monto y frecuencia; exportable; una merma `insumo_caducado` generada desde la alerta de 003 aparece con su lote.

## Contratos

- [`contracts/mermas.openapi.yaml`](./contracts/mermas.openapi.yaml)

## Criterio de "listo"

V1–V8 pasan; **pruebas de registro/costeo, umbral de autorización y baja + asiento verdes (Const. Ppio IX)**.
