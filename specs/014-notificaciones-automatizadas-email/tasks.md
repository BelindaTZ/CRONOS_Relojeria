# Tasks: Notificaciones Automatizadas por Email

**Feature**: `014-notificaciones-automatizadas-email` | **Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/notificaciones.openapi.yaml](./contracts/notificaciones.openapi.yaml)

**Tests**: incluidos para disparadores, cola/reintentos, deduplicación, opt-out y desacople del camino transaccional.

**MVP** = User Story 1 + User Story 2 + User Story 3 (los tres disparadores automáticos).

## Phase 1: Setup

- [X] T001 Crear módulo `backend/src/notificaciones/` (`router.py service.py scheduler.py repository.py schemas.py models.py`) y `frontend/src/notificaciones/` — sin carpeta `plantillas/` propia de archivos: las plantillas de 014 son overrides en BD (`shared.models.PlantillaEmail`), las plantillas Jinja2 de archivo siguen viviendo en `shared/correo/templates/` (una sola fuente de verdad de layout, no dos)
- [X] T002 [P] Módulo `notificaciones` en RBAC — ya sembrado desde `0003`; Gerente de Sucursal ya tenía `consultar` desde `0024`
- [X] T003 [P] `.env.example` — sin variables nuevas: reutiliza `EMAIL_BACKEND`/`SENDGRID_*` de 001

## Phase 2: Foundational

- [X] T004 Migración `0030_notificaciones` — `plantilla_email` (vive en `shared/models.py`, no en `notificaciones/models.py` — ver nota de arquitectura en `CONVENCIONES.md` §27), `envio`, `preferencia_comunicacion`, `evento_webhook_email` (append-only, reutiliza `cronos_append_only()` de `0023`)
- [X] T005 [P] Semilla: parámetros `antelacion_recordatorio_cita_horas` (24), `max_reintentos_email` (5), `backoff_email_minutos` (10). **Sin sembrar plantillas** (desviación deliberada de data-model.md "7 plantillas sembradas") — ver nota de arquitectura
- [X] T006 [P] `notificaciones/repository.py` + `notificaciones/schemas.py`
- [X] T007 `notificaciones/service.py::encolar()` — dedup por `clave_idempotencia`, consulta `preferencia_comunicacion` (opt-out → `cancelado`), sin email → `sin_destinatario`, `programar_para` opcional
- [X] T008 `notificaciones/router.py` — `POST /_internal/notificaciones/encolar` (para pruebas/operación manual — en producción los disparadores llaman `encolar()` directo en Python, ver T011/T013/T015)
- [X] T009 `notificaciones/scheduler.py` — poller in-proceso (APScheduler, cada 1 min — Spec SC-001) sobre `envio` `encolado` con `proxima_ejecucion ≤ now()`; reintentos con backoff hasta `max_reintentos` → `fallido`
- [X] T010 5 plantillas Jinja2 nuevas en `shared/correo/templates/` (`ot_entregado`, `ot_cancelada`, `cupon`, `nivel`, `recordatorio_cita`) con la identidad visual del Principio XI — son el fallback de archivo de esos 5 tipos nuevos (las 10 plantillas de 001/008/009/010/011 ya existían)

## Phase 3: User Story 1 — Aviso de cambio de estado de OT (P1) 🎯 MVP

- [X] T011 [US1] Integración con 008: `servicio_tecnico.entregar()` y `cambiar_estado(nuevo='cancelada')` llaman `notificaciones.encolar()` directo en Python (tipos `ot_entregado`/`ot_cancelada` — los 2 estados que hasta ahora quedaban completamente mudos; `listo`/`en_diagnostico`/asignación YA tenían su propio correo síncrono desde 008, se dejaron intactos — ver nota de alcance en `CONVENCIONES.md` §27)
- [X] T012 [P] [US1] Test `backend/tests/test_notificaciones.py` — un cambio de estado → un `envio`; dos disparos con la misma clave → un solo `envio` (dedup); cliente sin email → `sin_destinatario`

## Phase 4: User Story 2 — Cupones y beneficios de fidelización (P1) 🎯 MVP

- [X] T013 [US2] Integración con 006: `clientes.crear_cupon()` y `clientes.recalcular_nivel()` (solo en ASCENSO, nunca en descenso silencioso) llaman `notificaciones.encolar()` directo
- [X] T014 [P] [US2] Test — cupón → `envio` encolado con código/vigencia en el contexto; ascenso de nivel → `envio` con beneficios; el cupón se crea igual aunque el aviso quede `cancelado` por opt-out

## Phase 5: User Story 3 — Recordatorio de cita confirmada (P1) 🎯 MVP

- [X] T015 [US3] Integración con 007 — **ajuste real de diseño**: NO se encola en `citas.confirmar()` con `programar_para` futuro (lo que se había implementado primero); se usa el punto de integración que 007 ya dejó preparado explícitamente ("Interno (014)" en su propio código) — `citas.citas_para_recordatorio(antelacion)` — sondeado por `notificaciones.service.generar_recordatorios_cita()` en cada tick del worker, antes de `procesar_cola()`. Evita un mecanismo de programación paralelo al que 007 ya exponía
- [X] T016 [US3] `notificaciones/service.py::cancelar_pendiente()` — `citas.cancelar()` lo llama; cancela cualquier `envio` `encolado` de esa cita como red de seguridad (aunque el sondeo ya deja de generar recordatorios de una cita cancelada, por si uno quedó encolado en el margen de un tick)
- [X] T017 [P] [US3] Test — `cancelar_pendiente` cancela lo `encolado` de un disparo

## Phase 6: User Story 4 — Seguimiento y reintento de envíos (P2)

- [X] T018 [US4] `notificaciones/router.py` — `GET /envios` (filtros tipo/estado/cliente/disparo), `POST /envios/{id}/reintentar` (409 si el estado no es reintentable)
- [X] T019 [US4] `notificaciones/router.py` — `POST /webhooks/email` (actualiza `estado` a `entregado`/`rebotado` vía `evento_webhook_email`, concilia por prefijo de `sg_message_id` — SendGrid le agrega un sufijo por destinatario). **Gap de seguridad documentado** (no bloqueante): sin validar la firma ECDSA del Event Webhook todavía — ver `CONVENCIONES.md` §27
- [X] T020 [P] [US4] Frontend `notificaciones/` — `PanelEnvios.vue` (estado por envío + "Reintentar"; también sirve de reporte operativo — mismo `listar()` para `/envios` y `/reportes/envios`)
- [X] T021 [P] [US4] Test — envío fallido → reintentable manualmente; envío entregado/en curso → 409 al reintentar; `procesar_cola` con el proveedor caído no pierde el envío (queda `encolado` con backoff, nunca `fallido` antes de agotar `max_reintentos`)

## Phase 7: User Story 5 — Opt-out y plantillas (P2)

- [X] T022 [US5] `notificaciones/service.py` — CRUD `plantilla_email` (histórico por versión — índice único parcial "como mucho una `activa` por tipo", migración `0030`) + `preview_plantilla()` (reutiliza `shared/correo/service.render()`/`asunto_de()`)
- [X] T023 [US5] `notificaciones/service.py` — CRUD `preferencia_comunicacion`; tipos críticos (`password_temporal`, `usuario_bienvenida`, `ot_entregado`, `ot_cancelada`) rechazan el opt-out con 422
- [X] T024 [US5] `notificaciones/router.py` — `GET/PUT /plantillas/{tipo}`, `POST /plantillas/{tipo}/preview`, `GET/PUT /preferencias/cliente/{id}` — plantillas gateadas `require_gerencia_o_delegado` (spec: "solo Gerencia General o delegado")
- [X] T025 [P] [US5] Frontend `notificaciones/` — `EditorPlantilla.vue` (con preview en iframe) y `PreferenciasCliente.vue`
- [X] T026 [P] [US5] Test — opt-out cancela el envío pero no el cupón/hecho de origen; tipo crítico rechaza el opt-out; edición de plantilla solo Gerencia General; versión incrementa; el override de BD se usa al renderizar (con fallback al archivo si no hay override activo)

## Phase 8: Desacople (transversal) — parte del MVP conceptual

- [X] T027 Cubierto por diseño, no por un test de integración end-to-end con las 3 features (009/008/007) a la vez: cada integración (T011/T013/T015) llama `encolar()`, que solo hace un `INSERT` local envuelto en `try/except` — nunca puede fallar la transacción de origen. `test_notificaciones.py::test_encolar_nunca_lanza_por_fallo_de_contexto` cubre el caso límite (cliente inexistente) directamente sobre `encolar()`

## Phase 9: Polish & Cross-Cutting

- [X] T028 [P] Integración con 001 y 008: las plantillas `inactivacion_sucursal`, `password_temporal`, `usuario_bienvenida`, `tecnico_asignado`, `tecnico_nueva_ot`, `diagnostico_cliente`, `servicio_listo_retiro`, `compra_urgente_solicitada`, `factura_venta`, `cancelacion_orden` (las 10 que ya existían) quedan bajo gestión de 014 vía el mecanismo de override de `shared/correo/service.py::render()` — esas features siguen llamando `shared.correo.enviar(tipo, ...)` exactamente igual que antes, CERO cambios en esos ~15 sitios de llamada
- [X] T029 [P] `notificaciones/router.py` — `GET /reportes/envios` — no se duplicó lógica: mismo `service.listar()` que `/envios`
- [X] T030 [P] Frontend — `PanelEnvios.vue` ya cubre el reporte (filtros + exportación vía `shared/exportar.js`, ya arreglado de verdad en 013)
- [X] T031 [P] `CONVENCIONES.md` §27 — sin correo entrante; recordatorios de mantenimiento preventivo fuera de alcance (§8); nota de arquitectura de `PlantillaEmail` en `shared/`; gap de firma de webhook documentado
- [X] T032 Ejecutar `quickstart.md` V1–V8 — V1-V3/V6 verificados end-to-end vía pytest (encolar, dedup, opt-out, worker, reintentar, plantillas, webhook — 19 tests, `EMAIL_BACKEND=console` forzado); V4/V5 por inspección de código (gating RBAC del router, `require_perm`); V7 (desacople) cubierto por diseño (T027); V8 (reporte) verificado contra el stack real (`GET /envios`, `GET /plantillas`, `POST preview` — sin crear datos reales para no disparar un envío real por SendGrid, activo en este entorno de dev — ver nota de verificación en `CONVENCIONES.md` §27)

## Dependencias & Orden de ejecución

- Setup → Foundational (T004–T010) → US1 + US2 + US3 (MVP, los tres disparadores) → US4 → US5 → Desacople (T027) → Polish.

## Nota de implementación (2026-09-11)

Implementado de corrido, no solo el MVP. Ver `CONVENCIONES.md` §27 para el detalle completo de las 3 desviaciones de diseño reales encontradas durante la implementación: (1) `PlantillaEmail` vive en `shared/models.py`, no en `notificaciones/models.py` (evita una dependencia invertida de `shared/correo` hacia un módulo de negocio); (2) las 10 plantillas ya existentes NO se sembraron en BD — el override es opcional, con fallback al archivo Jinja2 de siempre; (3) el recordatorio de cita usa el punto de sondeo que 007 ya había dejado preparado (`citas_para_recordatorio`) en vez de un `encolar(programar_para=...)` aparte.
