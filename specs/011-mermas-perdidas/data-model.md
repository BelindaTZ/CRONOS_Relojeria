# Data Model: Mermas y Pérdidas

**Feature**: `011-mermas-perdidas` | **Phase**: 1 | **Date**: 2026-09-10

Migración `0016_mermas`. Reutiliza `reloj`, `pieza`, `stock_pieza`, `lote_pieza`, `evento_serie` (003); `orden_trabajo`, `tecnico` (008/005); `transferencia` (004); `proveedor` (002); `parametro_configuracion`, `usuario`, `registro_auditoria` (001); asiento automático (010).

## `categoria_merma` (catálogo editable, migración 0026)
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| nombre | varchar(120) | único |
| causa | varchar(20) | grupo de causa (`dano_tienda`, `dano_transito`, `robo_perdida`, `defecto_fabrica`, `dano_servicio`, `insumo_caducado`) |
| activo | boolean | default true |

Siembra 17 motivos iniciales (Caída accidental, Rotura de cristal, Defecto de fábrica, etc.).

## `merma`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| numero | varchar(20) | secuencial visible |
| bien_tipo | varchar(8) | `reloj` \| `pieza` |
| reloj_id | bigint FK → reloj | null si pieza |
| pieza_id | bigint FK → pieza | null si reloj |
| lote_id | bigint FK → lote_pieza | null salvo `insumo_caducado` |
| cantidad | int | 1 para relojes |
| causa | varchar(20) | `dano_tienda` \| `dano_transito` \| `robo_perdida` \| `defecto_fabrica` \| `dano_servicio` \| `insumo_caducado` |
| fecha_evento | date | |
| sucursal_id | bigint FK | |
| responsable_usuario_id | bigint FK → usuario | reporta el hecho |
| costo_perdida | numeric(14,2) | **a costo de adquisición**; restringido a rol administrativo |
| estado | varchar(24) | `en_evaluacion` \| `dado_de_baja` \| `en_reclamo_proveedor` \| `en_reclamo_seguro` \| `reparado_reingresado` |
| orden_trabajo_id | bigint FK → orden_trabajo | null salvo `dano_servicio` |
| tecnico_id | bigint FK → tecnico | null salvo `dano_servicio` (trazabilidad, sin sanción) |
| transferencia_id | bigint FK → transferencia | null salvo `dano_transito` |
| autorizacion_baja_id | bigint FK → autorizacion_baja | null hasta autorizar |
| asiento_id | bigint FK | null hasta dar de baja |
| creado_en, actualizado_en | timestamptz | |

**Transiciones**: ver `research.md` D2. `dado_de_baja` es terminal para el bien (salvo dato histórico); `reparado_reingresado` devuelve el bien al stock.

## `autorizacion_baja`
`id`, `merma_id` FK, `autorizador_usuario_id` FK (rol Gerencia General), `fecha` timestamptz, `observacion` varchar(255).

## `documento_soporte_merma`
`id`, `merma_id` FK, `tipo` (`acta` | `fotografia` | `denuncia` | `otro`), `objeto` (clave en bucket `documentos`), `nombre`, `subido_por`.

## `reclamo_merma`
`id`, `merma_id` FK, `destino` (`proveedor` | `seguro`), `proveedor_id` FK nullable, `aseguradora` varchar(120) nullable, `estado` varchar(24), `monto_recuperado` numeric(14,2) default 0, `creado_en`.

## `historial_estado_merma` (append-only)
`id`, `merma_id` FK, `estado`, `actor_usuario_id` FK, `timestamp`.

## Reglas de negocio (backend)

1. `costo_perdida` a costo de adquisición; nunca a precio de venta.
2. No se registra merma sobre un bien `vendido` o `dado_de_baja`.
3. Merma de pieza ≤ stock disponible en la sucursal; lote vencido consume del lote.
4. `costo_perdida > umbral_merma_autorizacion` ⇒ `dado_de_baja` exige `autorizacion_baja` (Gerencia General).
5. Al `dado_de_baja`: retiro del inventario activo (reloj `dado_de_baja` + `evento_serie(baja)`; pieza `movimiento_stock_pieza(merma)`), historial conservado, `asiento` de pérdida extraordinaria en 010.
6. `reparado_reingresado`: reloj → `disponible` + `evento_serie(reingreso)`; pieza → `movimiento_stock_pieza(ingreso)`; la merma queda en el historial.
7. `dano_servicio` guarda `tecnico_id` sin efecto disciplinario.
8. Todo cambio de estado y toda autorización ⇒ `historial_estado_merma` + `registro_auditoria`.
9. `costo_perdida` oculto para roles no administrativos.

## Migración

- `0016_mermas` — `merma`, `autorizacion_baja`, `documento_soporte_merma`, `reclamo_merma`, `historial_estado_merma`
- Datos: parámetro `umbral_merma_autorizacion`; cuenta contable de pérdida extraordinaria + `regla_asiento_automatico` para `merma_confirmada`

## Notas de implementación

- Migración real **`0025_mermas`** (spec decía `0016`; renumerada por orden de features implementadas). La cuenta contable de pérdida extraordinaria (`6.04`) y la regla `merma_confirmada` **ya existían desde `0023_contabilidad`** (010 las sembró previendo esta feature) — nada que resembrar aquí. `reloj.disponibilidad` ya admitía `'dado_de_baja'` desde `0009_inventario` (003 lo anticipó); `asiento.origen` ya admitía `'merma'` desde `0023`.
- `merma` usa el mismo truco de CHECK booleano→entero que 010 para "exactamente un bien" (`ck_merma_un_bien`: `(reloj_id is not null)::int + (pieza_id is not null)::int = 1`).
- `dado_de_baja` se trata como **estado terminal** en `cambiar_estado` (ninguna transición posterior, incluida `reparado_reingresado`) — el escenario de aceptación de US4 en `spec.md` parte explícitamente de "en evaluación", no de una baja ya confirmada; una vez posteado el asiento de pérdida extraordinaria, revertirlo exigiría un asiento de ajuste (fuera de alcance de 011). El "undo" de inventario (`inventario.revertir_reloj_baja`/`piezas.reingresar_pieza`) sigue existiendo por simetría de API, aunque el estado-máquina de mermas no lo alcanza hoy.
- Providers nuevos: `inventario.reloj_para_merma`/`marcar_reloj_baja`/`revertir_reloj_baja`; `piezas.dar_baja_pieza`/`reingresar_pieza`; `traslados.discrepancia_para_merma`/`vincular_merma` (el módulo `traslados` ganó su primer `__init__.py` con API pública — antes no exponía nada).
- El reingreso de pieza perecedera reutiliza la deducción FEFO genérica (no apunta a un `lote_id` específico) — simplificación consciente (Const. Ppio VII): el lote vencido suele ser también el más próximo en FEFO.
- `contabilidad.generar_asiento` se invoca envuelto en `try/except` (mismo patrón que 009/008): un fallo contable nunca bloquea la baja del inventario.
- RBAC: `autorizar-baja` usa `require_perm("mermas", "eliminar")` (no un chequeo de rol hardcodeado) — coincide literalmente con FR-015 ("Gerencia General también Eliminar (autoriza bajas)"); ningún rol de negocio de `0024_roles_negocio` tiene `eliminar` en `mermas` salvo Gerencia General (vía el seed de `scripts/seed_gerencia.py`), así que el efecto práctico es el mismo que el research.md D3 describe.
- Integración con 008/004 (T034/US5, Polish): `servicio_tecnico.reportar_dano` (ya existía) y `traslados.discrepancia_para_merma` (nuevo) producen el payload; el frontend los encadena directo a `MermaFormModal` (reexportado desde `@/mermas`) en vez de dejarlos como texto suelto — el botón "Registrar merma" de `ListaTransferencias.vue` estaba deshabilitado desde 004 esperando esta feature.
- Suite backend tras esta feature: **219** tests (+15 de `test_mermas.py`).
