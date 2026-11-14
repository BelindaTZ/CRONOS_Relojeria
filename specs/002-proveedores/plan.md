# Implementation Plan: Proveedores y Órdenes de Compra

**Branch**: `002-proveedores` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Ficha de proveedor (§4.2) con datos obligatorios, tipos, condiciones de pago, RUC/NIT y adjuntos de certificados en el bucket `documentos`. Órdenes de compra (puntuales y **programadas** con frecuencia) y su **recepción** total/parcial, construyendo el historial de compras. **Calificación de confiabilidad** 1–5 por criterios, con retroalimentación automática del **cumplimiento de plazos** (entrega real vs. pactada). Endpoint de creación de orden con **prellenado** para la alerta de reposición de 003. Registro del importe/condiciones/retención a pagar que 010 consume como CxP. Corrección de compras recibidas y edición parcial de proveedor **solo con rol elevado**, auditadas. Al recibir lubricantes/consumibles perecederos se captura **lote y fecha de caducidad** (enlaza con 003).

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `shared/guard`, `shared/auditoria`, `shared/storage` (de 000/001); un scheduler ligero para compras programadas (APScheduler in-proceso o tarea disparada por cron del compose — **sin** Airflow, que es 012)

**Storage**: PostgreSQL; MinIO bucket `documentos` (certificados/documentos legales)

**Testing**: `pytest` (cálculo de cumplimiento de plazos, generación de compras programadas), `vitest`

**Project Type**: Web — módulo `proveedores` (backend y frontend)

**Performance Goals**: alta de proveedor < 2 min (UX); listados con búsqueda multi-criterio < 1 s

**Constraints**: sin nuevos servicios en `docker-compose.yml` (Const.); scheduler in-proceso o job del compose ya existente; retenciones sin cálculo fiscal ni SRI

**Scale/Scope**: decenas de proveedores, cientos de órdenes/año

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | Cada FR cita §4.2, §4.4, §4.10, §7 o necesidad del negocio. ✅ |
| II | Órdenes de compra y recepciones son registros reales ligados a un documento. ✅ |
| III | PostgreSQL OLTP; certificados a `documentos` (bucket privado). Sin mezclar motores. ✅ |
| IV | Módulo `proveedores` declara permisos; correcciones restringidas a rol elevado. ✅ |
| V | Cálculo de cumplimiento y validaciones en backend. ✅ |
| VI | Referencia 001 (sucursal, auditoría) y 003 (ítems); no los redefine. ✅ |
| VII | Sin Airflow para la recurrencia (scheduler mínimo); sin motor de compras complejo. ✅ |
| VIII | Documentos de corrido tras aprobación. ✅ |
| IX | Cobertura de cumplimiento de plazos y de compras programadas; auditoría de correcciones. ✅ |
| X | Módulo `proveedores/` con capas; nada en `utils` genérico. ✅ |
| XI | Búsqueda multi-criterio, filtros reactivos, paginación, modales del design-system, exportación. ✅ |
| XII | Pantallas con `ui-ux-pro-max`. ✅ |

**Resultado**: PASS. Nota en Complexity Tracking sobre el scheduler.

## Project Structure

```text
backend/src/proveedores/
├── router.py          # /proveedores, /ordenes-compra, /ordenes-compra/{id}/recepciones, /compras-programadas
├── service.py         # calificación, cumplimiento de plazos, generación de programadas, prellenado
├── repository.py
├── schemas.py
└── scheduler.py       # dispara la generación de órdenes programadas (in-proceso)

frontend/src/proveedores/
├── components/  (ListaProveedores, FichaProveedor, PanelOrdenCompra, Recepcion, CompraProgramada)
├── composables/ (useProveedores, useOrdenesCompra)
├── stores/      (proveedoresStore)
└── services/    (proveedoresApi)
```

**Structure Decision**: Un solo módulo de negocio. La recurrencia se resuelve con `scheduler.py` in-proceso que, al arrancar el backend, programa la próxima generación de cada `compra_programada`; alternativa: un job del `docker-compose.yml` existente que llame a un endpoint interno. No se añade Airflow (es 012).

## Complexity Tracking

| Elemento | Por qué | Alternativa más simple rechazada porque |
|---|---|---|
| Scheduler in-proceso para compras programadas | §4.2 (abastecimiento recurrente) y necesidad del negocio | Generación 100% manual: el negocio pidió explícitamente automatizar semanal/mensual/trimestral |
