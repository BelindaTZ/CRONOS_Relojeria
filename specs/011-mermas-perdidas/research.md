# Research: Mermas y Pérdidas

**Feature**: `011-mermas-perdidas` | **Phase**: 0 | **Date**: 2026-09-10

Sin `NEEDS CLARIFICATION` (bucket de soporte y causa "insumo caducado" resueltos).

## D1 — Costeo de la merma

- **Decisión**: `costo_perdida` = `reloj.costo_adquisicion` o `pieza.costo_adquisicion × cantidad` (para un lote, el costo del lote). Nunca a precio de venta. Restringido a rol administrativo en la lectura.
- **Rationale**: §4.12, §4.10.1.

## D2 — Ciclo de estados

- **Decisión**: `en_evaluacion → dado_de_baja | reparado_reingresado`; `en_evaluacion` ↔ `en_reclamo_proveedor` / `en_reclamo_seguro`. Solo `dado_de_baja` retira definitivamente del inventario y genera el asiento. `reparado_reingresado` devuelve el bien al stock.
- **Rationale**: §4.12 (lista de estados).

## D3 — Umbral de autorización

- **Decisión**: parámetro `umbral_merma_autorizacion` (monto). Si `costo_perdida > umbral`, la transición a `dado_de_baja` exige `autorizacion_baja` (usuario con rol Gerencia General; registra quién y cuándo). Por debajo del umbral, un Gerente de Sucursal puede dar de baja.
- **Rationale**: §4.12, §9.2; Const. Ppio XI ("Autorizar baja").

## D4 — Baja del inventario y asiento

- **Decisión**: al `dado_de_baja`:
  - reloj → `disponibilidad = dado_de_baja`, `evento_serie(baja)`; ficha e historial persisten.
  - pieza → `movimiento_stock_pieza(merma, −cantidad)` (nunca deja negativo el stock; si ya no hay stock ⇒ rechazo).
  - `POST` interno a 010 → `asientos_auto.generar("merma_confirmada", {costo_perdida, ...})` con cuenta de **pérdida extraordinaria** (separada de gastos operativos).
- **Rationale**: §4.12, §4.10.1.

## D5 — Documentos de soporte

- **Decisión**: `documento_soporte_merma` (tipo acta/fotografía/denuncia, `objeto` en bucket `documentos`, `nombre`). Servidos vía endpoint autenticado.
- **Rationale**: §4.12; Const. Ppio III.

## D6 — Orígenes derivados

- **Decisión**: endpoints de otras features producen un payload para `POST /mermas`:
  - 008 `reportar-dano` → causa `dano_servicio`, `orden_trabajo_id`, `tecnico_id`.
  - 004 discrepancia → causa `dano_transito`, `transferencia_id`.
  - 003 alerta de lote vencido → causa `insumo_caducado`, `pieza_id`, `lote_id`, `cantidad`.
- **Rationale**: §4.12, §4.9, §4.6.

## D7 — Reclamos

- **Decisión**: `reclamo_merma` (destino `proveedor`|`seguro`, `proveedor_id` FK opcional, `aseguradora` varchar, `estado`, `monto_recuperado`). Seguimiento de estado; sin integración externa.
- **Rationale**: §4.12; Ppio VII.

## D8 — Vínculo técnico

- **Decisión**: la merma `dano_servicio` guarda `tecnico_id` para trazabilidad interna; **sin efecto disciplinario automático**.
- **Rationale**: §4.12 explícito.

## D9 — Reporte

- **Decisión**: `GET /reportes/mermas?desde=&hasta=&causa=&sucursal_id=` agrupa por causa con monto y frecuencia. Versión operativa; el comparativo entre periodos es 013.
- **Rationale**: §4.11.2.
