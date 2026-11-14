# Research: Proveedores y Órdenes de Compra

**Feature**: `002-proveedores` | **Phase**: 0 | **Date**: 2026-09-10

Sin `NEEDS CLARIFICATION` pendientes.

## D1 — Recurrencia de compras programadas

- **Decisión**: entidad `compra_programada` (proveedor, ítems plantilla, `frecuencia` ∈ {semanal, mensual, trimestral}, `proxima_generacion`, `estado` ∈ {activa, pausada, cancelada}). Un `scheduler.py` in-proceso (APScheduler) revisa cada hora y genera la `orden_compra` en estado `borrador` cuando `proxima_generacion ≤ now()`, luego avanza `proxima_generacion`.
- **Rationale**: §4.2 (abastecimiento) + necesidad del negocio; Airflow está reservado a 012 (Const.).
- **Alternativas**: Airflow (viola el reparto de infra), cron del host (fuera de Docker), job del compose que hace `curl` a un endpoint interno (válido como plan B).

## D2 — Cálculo de cumplimiento de plazos

- **Decisión**: por cada `recepcion_compra` se calcula `desfase_dias = fecha_real − fecha_pactada`. El indicador del proveedor es el promedio móvil de `desfase_dias` de las últimas N órdenes recibidas (N configurable, def. 10). El componente "cumplimiento de plazos" de la calificación se deriva de ese indicador (escala 1–5 por tramos); los demás criterios (calidad, soporte) son manuales.
- **Rationale**: §4.2 ampliación ("retroalimentar la calificación de forma automática").
- **Alternativas**: promedio total histórico (menos representativo de la tendencia reciente).

## D3 — Recepción parcial

- **Decisión**: `recepcion_compra` con `cantidad_recibida` por línea; la orden pasa a `parcial` mientras `Σ recibido < Σ pedido`, y a `recibida` al completarse. Recepción con `cantidad_recibida > pedida` en una línea ⇒ se acepta y se marca "sobre-entrega" para revisión.
- **Rationale**: operación real; §4.2.

## D4 — Adjuntos de proveedor

- **Decisión**: certificados y documentos legales se suben al bucket `documentos` con clave `proveedor/{id}/{uuid}-{nombre}`; se sirven solo vía endpoint autenticado del backend (URL firmada corta).
- **Rationale**: Const. Ppio III (bucket `documentos` privado, provisionado en 000).

## D5 — Corrección de datos con rol elevado

- **Decisión**: `PATCH /ordenes-compra/{id}` y correcciones de recepción requieren `require_perm("proveedores", "editar")` **más** rol en {Gerente de Sucursal, Gerencia General}; exigen `motivo`; generan `registro_auditoria` con antes/después. La corrección del `numero_serie` de una unidad ya ingresada se delega a 003 (mismo criterio).
- **Rationale**: necesidad del negocio; §6.

## D6 — Datos a pagar y CxP

- **Decisión**: la `orden_compra` guarda `importe_a_pagar`, `condiciones_pago` (heredadas del proveedor, editables), `retencion_aplicable` (monto/porcentaje, sin cálculo fiscal). 010 lee estos campos para construir el subledger de CxP y su aging. 002 no crea asientos ni CxP.
- **Rationale**: §4.10, §7; separación de responsabilidades (010 es dueño de contabilidad).

## D7 — Perecederos y lote

- **Decisión**: si una línea referencia una pieza marcada `perecedera` en 003, la `recepcion_compra` exige `lote` y `fecha_caducidad` por línea y los propaga a 003 (crea `lote_pieza`).
- **Rationale**: necesidad del negocio; §4.5/§4.6.

## D8 — Ítems de línea antes de 003

- **Decisión**: una `linea_orden_compra` referencia un ítem por `tipo` (`reloj` | `pieza`) y un identificador. Mientras 003 no exista en tiempo de desarrollo, se valida contra un catálogo controlado; una vez 003 disponible, se valida contra `pieza.codigo` y contra `referencia`/`marca` de relojes.
- **Rationale**: orden de features (003 va después de 002 pero antes de la implementación real de recepción→inventario).
