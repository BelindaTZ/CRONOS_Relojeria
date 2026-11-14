# Research: Inventario de Relojes y Piezas

**Feature**: `003-inventario-relojes-piezas` | **Phase**: 0 | **Date**: 2026-09-10

## D1 — Unidad física vs. modelo

- **Decisión**: `reloj` = una fila por unidad física (número de serie único). Los atributos de modelo (marca, referencia, calibre, materiales…) se repiten por unidad; NO se normaliza a una tabla `modelo` en esta fase (el negocio maneja ~12 unidades por modelo y las fichas pueden diferir).
- **Rationale**: §4.4 ("Ficha detallada por unidad física, no solo por modelo"); Ppio VII.
- **Alternativas**: `modelo` + `unidad` — normaliza pero añade complejidad sin beneficio claro al volumen actual; se puede refactorizar luego.

## D2 — Historial inalterable por número de serie

- **Decisión**: `evento_serie` (numero_serie, tipo ∈ {ingreso, venta, servicio, transferencia, baja, reingreso, correccion}, fecha, documento_tipo, documento_id, detalle JSON). Solo INSERT; sin UPDATE/DELETE. Una corrección de datos genera un evento `correccion` que apunta al cambio, no borra el anterior.
- **Rationale**: §6 ("historial inalterable de eventos").
- **Alternativas**: log de auditoría genérico — no da la vista cronológica por serie que pide §4.11.1.

## D3 — Stock de piezas nunca negativo

- **Decisión**: `movimiento_stock_pieza` (append-only) + columna materializada `stock_actual` por (pieza, sucursal), actualizada en la misma transacción con `SELECT ... FOR UPDATE`. Un consumo que dejaría `stock_actual < 0` aborta la transacción con error de dominio.
- **Rationale**: Const. Ppio II; §4.5.
- **Alternativas**: calcular stock sumando movimientos en cada lectura — correcto pero lento y propenso a race conditions sin lock.

## D4 — Perecederos: lote y caducidad

- **Decisión**: `pieza.perecedera` boolean. Si true, cada ingreso crea `lote_pieza` (numero_lote, fecha_caducidad, cantidad, sucursal). El consumo descuenta por FEFO (first-expire-first-out). Alerta `caducidad_proxima` cuando `fecha_caducidad − now() ≤ umbral` (parámetro, def. 30 días) y `vencido` cuando pasó. Consumir un lote vencido advierte y ofrece merma (011, causa `insumo_caducado`).
- **Rationale**: necesidad del negocio; §4.6 (lubricantes).
- **Alternativas**: sin lotes, solo fecha en la pieza — no sirve con varios ingresos de fechas distintas.

## D5 — Alertas de stock

- **Decisión**: `alerta_stock` materializada, recalculada tras cada movimiento. Tipos: `cerca_maximo` (relojes de un modelo ≥ `stock_maximo_modelo` − margen), `ultima_unidad` (relojes = 1), `bajo_minimo` (pieza ≤ mínimo). `stock_maximo_modelo` y `umbral_reposicion` son parámetros (001). La alerta NO bloquea; su acción "Reponer" llama `POST /ordenes-compra/prellenar` (002).
- **Rationale**: §4.4, §4.5, §9.2; Const. Ppio XI.
- **Alternativas**: alertas calculadas al vuelo en cada request del dashboard — más lento y sin persistencia para el panel.

## D6 — Fotos

- **Decisión**: `foto_reloj` (reloj_id, objeto en `reloj-imagenes` con clave `reloj/{serie}/{n}.jpg`, orden). Servidas directo a la app (bucket de lectura). Subida vía backend (valida tipo/tamaño), no directa del navegador a MinIO.
- **Rationale**: Const. Ppio III ("servidas directo a la app").

## D7 — Calibre

- **Decisión**: `calibre` (codigo, marca, descripcion). 003 lo crea con datos básicos; 008 añade `ficha_lubricacion_calibre` (1—1) con puntos y productos recomendados. `reloj.calibre_id` FK.
- **Rationale**: Const. "Entidades compartidas" (calibre → 003).

## D8 — Corrección con rol elevado

- **Decisión**: `PATCH /relojes/{id}` para `numero_serie` y campos de ficha requiere rol en {Gerente de Sucursal, Gerencia General} + `motivo`; genera `evento_serie` tipo `correccion` + `registro_auditoria`. Si cambia el número de serie, el historial se re-vincula preservando los eventos previos.
- **Rationale**: necesidad del negocio; §6.

## D9 — Restricción de costo/margen

- **Decisión**: los campos `costo_adquisicion` y cualquier margen se omiten de la respuesta para roles no administrativos (serializer condicional según permiso `ver_costos`, un permiso granular adicional del módulo).
- **Rationale**: §6 ("restringir información financiera sensible").
