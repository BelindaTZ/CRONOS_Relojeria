# Tasks: Ventas, Comprobantes y Garantías

**Feature**: `009-ventas-facturacion-comprobantes-garantias` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/ventas.openapi.yaml](./contracts/ventas.openapi.yaml)

**Tests**: **cobertura obligatoria (Const. Ppio IX)** de margen de venta y margen mínimo tras descuentos/cupones.

**MVP** = User Story 1 + User Story 2 + User Story 4.

## Phase 1: Setup

- [x] T001 Crear módulo `backend/src/ventas/` (`router.py service.py margen.py repository.py schemas.py`) y `frontend/src/ventas/`
- [x] T002 [P] Declarar módulo `ventas` en el catálogo RBAC

## Phase 2: Foundational

- [x] T003 Migración `0014_ventas` — todas las tablas de `data-model.md` (incluye `cuenta_por_cobrar`)
- [x] T004 [P] Migración de datos — parámetros de garantía y `monto_max_consumidor_final`
- [x] T005 [P] `ventas/repository.py` + `ventas/schemas.py`
- [x] T006 `ventas/service.py` — ciclo `borrador → confirmada → anulada` con guardas
- [x] T007 `ventas/router.py` — esqueleto con `require_perm("ventas", <op>)` y `scope_sucursal`
- [x] T008 Verificar disponibilidad de `shared/pdf`, `shared/pagos` (008) y `shared/descuentos` (006); stubs si se desarrolla en paralelo

## Phase 3: User Story 1 — Registrar y confirmar una venta (P1) 🎯 MVP

- [x] T009 [US1] `ventas/service.py` — `crear_venta` (líneas, valida cliente identificado salvo consumidor final D8), `agregar_pago` (shared/pagos)
- [x] T010 [US1] `ventas/service.py` — `confirmar_venta` (transacción atómica): baja de stock (relojes → `vendido` + `evento_serie(venta)`; piezas → `movimiento_stock_pieza`), garantías, CxC del saldo
- [x] T011 [US1] `ventas/service.py` — al confirmar: `POST /_internal/fidelizacion/recalcular` (006); vincular cita (007, `PUT /_internal/citas/{id}/vincular`)
- [x] T012 [US1] `ventas/router.py` — `GET/POST /ventas`, `GET /ventas/{id}`, `POST /ventas/{id}/pagos`, `POST /ventas/{id}/confirmar`
- [x] T013 [P] [US1] Frontend `ventas/` — `PanelVenta`, `LineasVenta` (selectores de reloj/pieza), `PagosVenta` (multimedios)
- [x] T014 [P] [US1] Test `backend/tests/test_confirmar_venta.py` — reloj en tránsito → 409; confirmación atómica; CxC por saldo; recálculo de nivel disparado; venta concurrente de última unidad → solo 1 pasa

## Phase 4: User Story 2 — Margen de la venta y margen mínimo (P1) 🎯 MVP 🔒

- [x] T015 [US2] `ventas/margen.py` — `margen_venta(orden)` = Σ (precio_final − costo) por línea
- [x] T016 [US2] `ventas/service.py` — `aplicar_descuento` vía `shared/descuentos` (un descuento O un cupón; 422 si ambos); consumo de cupón con lock; `autorizacion_margen_minimo` si `requiere_autorizacion`
- [x] T017 [US2] `ventas/router.py` — `POST /ventas/{id}/descuento`
- [x] T018 [US2] Serializador que oculta `margen_venta`, `costo`, `margen` de línea a roles no administrativos y de los comprobantes
- [x] T019 [P] [US2] Test `backend/tests/test_margen_venta.py` — margen = Σ(precio_final − costo) sobre casos de prueba; descuento bajo mínimo → bloqueo/autorización; descuento+cupón → 422; margen oculto sin rol admin **(crítico)**
- [x] T020 [P] [US2] Registrar consumidor en `shared/parametros` (`margen_minimo` recalcula ventas en borrador)

## Phase 5: User Story 3 — Garantías de fábrica y de tienda (P1)

- [x] T021 [US3] `ventas/service.py` — al confirmar, crear `garantia_venta` (`fabrica`, `tienda`) con periodos de parámetros
- [x] T022 [US3] `ventas/router.py` — `GET /ventas/{id}/garantias`
- [x] T023 [P] [US3] Frontend `ventas/` — `PanelGarantias`
- [x] T024 [P] [US3] Test `backend/tests/test_garantias_venta.py` — dos filas con fechas correctas

## Phase 6: User Story 4 — Comprobante y certificado (P1) 🎯 MVP

- [x] T025 [US4] `ventas/service.py` — al confirmar, `shared/pdf` renderiza `comprobante_venta` y `certificado_garantia_autenticidad` (vinculado al número de serie) → `comprobantes-venta`; sin costos/márgenes; campos compatibles con SRI
- [x] T026 [US4] `ventas/router.py` — `GET /ventas/{id}/comprobantes` (URLs firmadas, autenticado + permiso)
- [x] T027 [P] [US4] Plantillas de `shared/pdf` para comprobante y certificado con `ui-ux-pro-max`
- [x] T028 [P] [US4] Test `backend/tests/test_comprobantes_venta.py` — PDFs generados; acceso anónimo → 403; sin costos/márgenes en el contenido

## Phase 7: User Story 5 — Venta a crédito y CxC (P2)

- [x] T029 [US5] `ventas/service.py` — pago parcial ⇒ `cuenta_por_cobrar` por el saldo exacto
- [x] T030 [US5] `ventas/router.py` — `GET /cuentas-por-cobrar`
- [x] T031 [P] [US5] Test `backend/tests/test_venta_credito.py` — venta 5000 con pago 3000 → CxC 2000

## Phase 8: User Story 6 — Anulación o devolución (P2)

- [x] T032 [US6] `ventas/service.py` — `anular` (reingreso de stock + `evento_serie(reingreso)`, reversa de margen y nivel, CxC `anulada`, `anulacion_venta`); bloqueada si el reloj está en OT
- [x] T033 [US6] `ventas/router.py` — `POST /ventas/{id}/anular`
- [x] T034 [P] [US6] Frontend `ventas/` — `AnularVenta` con modal de motivo
- [x] T035 [P] [US6] Test `backend/tests/test_anular_venta.py` — reingreso 100%; nivel y margen revertidos; reloj en OT → 409

## Phase 9: Polish & Cross-Cutting

- [x] T036 [P] `GET /ventas-dia` (total + margen del día, margen solo rol administrativo)
- [x] T037 [P] Venta de piezas sueltas y validación de consumidor final (D8)
- [x] T038 [P] Exportación CSV/Excel/PDF de la consulta de ventas
- [x] T039 Ejecutar `quickstart.md` V1–V8; confirmar cobertura de margen de venta y margen mínimo
- [x] T040 [P] Revisar `checklists/requirements.md`

## Dependencies & Execution Order

- Setup → Foundational (T003–T008) → US1 + US2 + US4 (MVP) → US3 → US5 → US6 → Polish.
- Depende de `shared/pdf`, `shared/pagos` (008), `shared/descuentos`, `fidelizacion/recalcular` (006), `citas/vincular` (007) y `cuenta_por_cobrar` que 010 consume.

## Parallel Execution Examples

- MVP: US1 (T009–T014) → US2 (T015–T020) || US4 (T025–T028) tras US1.
- Tests T014, T019, T024, T028, T031, T035 en paralelo con sus servicios.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US2 + US4 → venta confirmada con margen protegido y documentos.
2. **Incremento 2**: US3 (garantías) + US5 (CxC).
3. **Incremento 3**: US6 (anulación) + Polish (ventas del día, piezas sueltas, exportación).

## Notas de implementación (2026-09-10)

Feature IMPLEMENTADA. Desviaciones respecto a este documento:

- **Migración `0021_ventas`** (no `0014` — numeración incremental real; la anterior es `0020_servicio_tecnico`). Tablas: `orden_venta`, `linea_venta`, `garantia_venta`, `comprobante_venta` (`tipo` VARCHAR(40)), `anulacion_venta`, `cuenta_por_cobrar`. **Sin `pago_venta`**: se usa la `pago` de `shared/pagos` (`documento_tipo='venta'`). Seed: `garantia_fabrica_dias_default=730` (los otros params ya existían).
- **`shared/pdf`** gana `comprobante_venta(ctx)` y `certificado_garantia_autenticidad(ctx)` — reportlab, sin costo/margen.
- **Descuento a nivel de orden**: `shared/descuentos.aplicar` se llama con el total y el costo agregados; el resultado se **prorratea** entre líneas por peso de `precio_lista`. `bloquear` → 409 al aplicar; `requiere_autorizacion` → `confirmar` exige `autorizacion_margen_minimo_id`.
- **Garantías**: una fila `fabrica` + una `tienda` **por línea de reloj** (`linea_venta_id`). Las piezas sueltas no generan garantía.
- **CxC**: `ventas` la crea y la expone a 010 vía `ventas/public.py` (`cuentas_por_cobrar_abiertas`, `marcar_cxc_saldada`). La entrega a crédito de una OT (008) sigue solo logueando hasta que 010 exista.
- **Anulación**: bloqueada si un reloj de la venta tiene OT abierta (`servicio_tecnico.tiene_ot_activa_para_reloj`).
- **APIs públicas nuevas** en `inventario` (`reloj_para_venta`, `marcar_reloj_vendido`, `revertir_reloj_venta`), `piezas` (`datos_pieza_venta`, `vender_pieza`, `revertir_venta_pieza`), `clientes` (`descuento_por_id`, `cupon_datos`), `servicio_tecnico` (`tiene_ot_activa_para_reloj`).
- **`shared/parametros.get_parametro`** ya traía `fallback_global` (de 008); 009 lo usa para la garantía de fábrica por marca.
- Tests (Ppio IX): `backend/tests/test_ventas.py` (9). Suite backend total **187**.
- Checklist `requirements.md`: cubierto por el flujo implementado + los tests; queda informativo.
