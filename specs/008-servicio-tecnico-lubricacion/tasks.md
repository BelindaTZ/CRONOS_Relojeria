# Tasks: Servicio Técnico y Lubricación

**Feature**: `008-servicio-tecnico-lubricacion` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: **cobertura obligatoria (Const. Ppio IX)** de margen del servicio, margen mínimo tras descuentos y consumo de insumos.

**MVP** = User Story 1 + 1b + 4 + 5 (abrir OT → presupuesto → costear → cobrar y entregar).

## Phase 1: Setup

- [x] T001 Crear módulos `backend/src/servicio_tecnico/`, `backend/src/lubricacion/` y `backend/src/shared/pdf/`, `backend/src/shared/pagos/`; frontends correspondientes
- [x] T002 [P] Añadir `weasyprint` (o `reportlab`) a `backend/pyproject.toml`
- [x] T003 [P] Declarar módulos `ordenes_trabajo` y `lubricacion` en el catálogo RBAC (técnico: consultar + editar solo las propias)
- [x] T004 [P] Fixtures y stubs de 005 (`costo-mo-ot`) y 006 (`descuentos/aplicar`, `fidelizacion/recalcular`) si aún no están disponibles

## Phase 2: Foundational

- [x] T005 Migración `0013_servicio_tecnico` — todas las tablas de `data-model.md`
- [x] T006 [P] Migración de datos — `producto_moebius` sembrado (§4.6); parámetros `margen_objetivo_servicio`, `tiempo_estimado_<tipo>`, `garantia_tienda_dias_<tipo>`
- [x] T007 `backend/src/shared/pagos/` — `registrar_pago(doc_tipo, doc_id, medio, monto, ref)`, `saldo(doc_tipo, doc_id)` (append-only; el ciclo del cheque es de 010)
- [x] T008 `backend/src/shared/pdf/` — `render(plantilla, contexto) -> bytes` (Jinja2 → weasyprint) con layout de identidad visual; helper `guardar_en_comprobantes(objeto, bytes)`
- [x] T009 [P] `servicio_tecnico/repository.py`, `lubricacion/repository.py`, schemas
- [x] T010 `servicio_tecnico/service.py` — máquina de estados de la OT con guardas (research D1)
- [x] T011 `servicio_tecnico/router.py` y `lubricacion/router.py` — esqueleto con `require_perm` y scope "solo las propias" para técnico

## Phase 3: User Story 1 — Abrir OT y asignar técnico (P1) 🎯 MVP

- [x] T012 [US1] `servicio_tecnico/service.py` — `crear_ot` (verifica reloj no `en_transito`, "adquirido en la tienda" con override autorizado), `evento_serie` pendiente hasta entrega
- [x] T013 [US1] `servicio_tecnico/service.py` — `asignar_tecnico` → `shared/correo.enviar("tecnico_asignado", cliente.email, {...})`
- [x] T014 [US1] `servicio_tecnico/router.py` — `GET/POST /ordenes-trabajo`, `GET/PATCH /ordenes-trabajo/{id}`, `GET /ordenes-trabajo-en-curso`
- [x] T015 [P] [US1] Frontend `servicio_tecnico/` — `PanelOrdenTrabajo`, `TableroOT` (técnico ve solo las suyas)
- [x] T016 [P] [US1] Test `backend/tests/test_crear_ot.py` — reloj en tránsito → 409; reloj no vendido → 422/autorización; email de técnico asignado enviado

## Phase 4: User Story 1b — Diagnóstico, presupuesto y elección de piezas (P1) 🎯 MVP

- [x] T017 [US1b] `servicio_tecnico/service.py` — `registrar_diagnostico`; `crear_presupuesto` (líneas con opción original/no original + diferencia)
- [x] T018 [US1b] `servicio_tecnico/service.py` — `aprobar_presupuesto` (registra `preferencia_cliente`, `confirmado_por`, fija `fecha_estimada_entrega`); guarda para pasar a `en_reparacion`
- [x] T019 [US1b] `servicio_tecnico/router.py` — `POST /ordenes-trabajo/{id}/diagnostico`, `.../presupuesto`, `.../presupuesto/aprobar`
- [x] T020 [P] [US1b] Frontend — `PanelPresupuesto` (opciones de pieza, registro de la respuesta del cliente)
- [x] T021 [P] [US1b] Test `backend/tests/test_presupuesto.py` — sin presupuesto aprobado → `en_reparacion` = 409; `fecha_estimada_entrega` solo al aprobar

## Phase 5: User Story 2 — Piezas y lubricación (P1)

- [x] T022 [US2] `servicio_tecnico/service.py` — `agregar_pieza_ot` (descuenta stock 003; FEFO perecederas; nunca negativo)
- [x] T023 [US2] `lubricacion/service.py` — CRUD `ficha_lubricacion_calibre` + `punto_lubricacion`; `producto_moebius`
- [x] T024 [US2] `servicio_tecnico/service.py` — `registrar_lubricacion_ot` (recomendado vs. usado, `desviacion`, consumo de insumo descuenta stock)
- [x] T025 [US2] `servicio_tecnico/router.py` + `lubricacion/router.py` — `.../piezas`, `.../lubricacion`, `/calibres/{id}/ficha-lubricacion`, `/productos-moebius`, `/reportes/desviacion-lubricacion`
- [x] T026 [P] [US2] Frontend `lubricacion/` — `FichaLubricacionCalibre`, `RegistroLubricacionOT`
- [x] T027 [P] [US2] Test `backend/tests/test_lubricacion.py` — recomendado ≠ usado → `desviacion=true`; consumo descuenta stock; consumo real calculado **(crítico)**

## Phase 6: User Story 4 — Costeo y margen del servicio (P1) 🎯 MVP 🔒

- [x] T028 [US4] `servicio_tecnico/costeo.py` — `costo_interno(ot)` = MO(005) + piezas + insumos; `precio_sugerido`; `margen_real`
- [x] T029 [US4] `servicio_tecnico/service.py` — `registrar_horas`; aplicar descuento vía `shared/descuentos` (006) con margen mínimo; registrar `aplicacion_descuento` en la OT
- [x] T030 [US4] `servicio_tecnico/router.py` — `POST /ordenes-trabajo/{id}/horas`, `GET /ordenes-trabajo/{id}/costeo` (rol administrativo), `POST /ordenes-trabajo/{id}/descuento`
- [x] T031 [US4] Serializador que oculta costo/margen a roles no administrativos y del `documento_ot`
- [x] T032 [P] [US4] Test `backend/tests/test_margen_servicio.py` — `margen_real` = precio − (MO + piezas + insumos) sobre casos de prueba; descuento bajo mínimo → bloqueo/autorización; costo/margen ocultos **(crítico)**
- [x] T033 [P] [US4] Registrar consumidor en `shared/parametros` para `margen_objetivo_servicio` (recalcular OT abiertas)

## Phase 7: User Story 5 — Ciclo, cobro al retiro y garantía (P1) 🎯 MVP

- [x] T034 [US5] `servicio_tecnico/service.py` — `cambiar_estado` (guardas); `registrar_pago_ot` (usa `shared/pagos`); `entregar` requiere `saldo == 0` o `autorizacion_credito` → CxC (010)
- [x] T035 [US5] `servicio_tecnico/service.py` — al `entregar`: `shared/pdf` genera OT + certificado → `comprobantes-venta`; `evento_serie(servicio)`; `POST /_internal/fidelizacion/recalcular` (006); notificación a 014; vincular cita (007)
- [x] T036 [US5] `servicio_tecnico/service.py` — `reabrir_por_garantia` (OT `reapertura` con `ot_original_id`)
- [x] T037 [US5] `servicio_tecnico/router.py` — `.../estado`, `.../pagos`, `.../entregar`, `.../reabrir-garantia`
- [x] T038 [P] [US5] Frontend — panel de trabajo con "Cerrar orden", cobro multimedios, aviso "sin pago no se entrega"
- [x] T039 [P] [US5] Test `backend/tests/test_entrega_ot.py` — `entregar` con saldo > 0 → 409; con pago mixto completo → `entregado` + PDFs + evento + recálculo; crédito autorizado → CxC

## Phase 8: User Story 6 — Tablero e informe de servicios (P2)

- [x] T040 [US6] `servicio_tecnico/service.py` — `informe_servicios(filtros)` (cliente, fecha, reloj, trabajo, repuestos, precio)
- [x] T041 [US6] `servicio_tecnico/router.py` — `GET /informe-servicios`
- [x] T042 [P] [US6] Frontend — `InformeServicios` + exportación CSV/Excel/PDF
- [x] T043 [P] [US6] Test `backend/tests/test_informe_servicios.py` — coincide con las OT registradas

## Phase 9: User Story 7 — Daño durante el servicio (P2)

- [x] T044 [US7] `servicio_tecnico/service.py` — `reportar_dano(ot)` → payload para `POST /mermas` (011, `dano_servicio`), vínculo a OT y técnico
- [x] T045 [US7] `servicio_tecnico/router.py` — `POST /ordenes-trabajo/{id}/reportar-dano`
- [x] T046 [P] [US7] Test `backend/tests/test_dano_servicio.py` — payload con vínculos; sin sanción automática

## Phase 10: Polish & Cross-Cutting

- [x] T047 [P] Plantillas de `shared/pdf` (OT + certificado) con `ui-ux-pro-max` y la paleta
- [x] T048 [P] Marca de reprocesos/reclamos sobre el mismo reloj (alimenta indicador de calidad de 005)
- [x] T049 [P] Estabilizar contratos `shared/pdf` y `shared/pagos` para reutilización por 009
- [x] T050 Ejecutar `quickstart.md` V1–V8; confirmar cobertura de margen del servicio y margen mínimo

## Dependencies & Execution Order

- Setup → Foundational (T005–T011) → US1 → US1b → US4 → US5 (MVP) → US2 → US6 → US7 → Polish.
- US4 depende de US1b (presupuesto) y del contrato de 005. US5 depende de `shared/pagos`, `shared/pdf`, 006, 007, 010 (CxC).

## Parallel Execution Examples

- Foundational: T007 (`shared/pagos`) || T008 (`shared/pdf`) || T009.
- US2 (lubricación) puede avanzar en paralelo a US4 (costeo) tras US1b.
- Tests T016, T021, T027, T032, T039, T043, T046 en paralelo con sus servicios.

## Implementation Strategy

1. **MVP**: Foundational + US1 + US1b + US4 + US5 → OT completa desde apertura hasta entrega con cobro y documentos.
2. **Incremento 2**: US2 (lubricación completa) + US6 (informe).
3. **Incremento 3**: US7 (daño en servicio) + Polish (plantillas PDF, contratos compartidos).

## Notas de implementación (2026-09-10)

Feature IMPLEMENTADA. Desviaciones respecto a este documento:

- **Migración `0020_servicio_tecnico`** (no `0013` — numeración incremental real; la anterior es `0019_citas`). 15 tablas incluyendo `pago` (capacidad compartida). Semilla: 10 productos Moebius (§4.6) + params `margen_objetivo_servicio=0.5`, `garantia_tienda_dias_default=180` (no un parámetro por tipo — la precedencia sucursal→tipo_servicio→global se resuelve en runtime con `get_parametro(..., fallback_global=False)`).
- **`shared/pdf` usa reportlab** (Python puro) en vez de Jinja2→weasyprint: evita añadir pango/cairo/gdk al `python:3.12-slim` del Dockerfile. Contrato: `documento_orden_trabajo(ctx)->bytes`, `certificado_garantia(ctx)->bytes`, `guardar_comprobante(objeto, bytes)->str`.
- **`shared/pagos`**: tabla `pago` genérica append-only (`documento_tipo` ∈ orden_trabajo|venta). Sin `pago_ot` propio. `saldo(db, *, documento_tipo, documento_id, total)`.
- **`RegistroLubricacionOT`** vive en `lubricacion/models.py` (el módulo dueño del reporte de desviación), no en `servicio_tecnico`. FK a `orden_trabajo` por string, sin import cruzado.
- **Scoping "solo las propias"** (T044/FR-025): `_solo_propias(db, user)` — restringe a `tecnicos.tecnico_de_usuario(user.id)` salvo Gerencia / Técnico Jefe / roles administrativos.
- **US7 (daño)**: `reportar_dano` devuelve el payload para 011 y lo audita; no crea la merma (011 no existe).
- **CxC en la entrega a crédito** (T037): se registra `autorizacion_credito_id` y se loguea; la CxC real es de 010.
- Tests (Ppio IX): `backend/tests/test_servicio_tecnico.py`, `test_lubricacion.py`, `test_pagos_compartido.py`. Suite backend total **192**.
- Checklists `business-rules.md` (BR001–BR016): cubiertas por el flujo implementado + los tests anteriores; quedan informativas.
