# Implementation Plan: Ventas, Comprobantes y Garantías

**Branch**: `009-ventas-facturacion-comprobantes-garantias` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Transacción de **venta** de relojes y piezas sueltas (Principio II): orden de venta con líneas, **baja de stock** y `evento_serie(venta)` al confirmar, aplicación de **descuentos/cupones** vía `shared/descuentos` (006) con **margen mínimo protegido**, **pagos multimedios** vía `shared/pagos` (008) sin pasarela en línea, cálculo del **margen de la venta** (precio final − costo de adquisición), **garantías** de fábrica y de tienda por transacción (§7), y generación del **comprobante de venta** y el **certificado de garantía/autenticidad** en `comprobantes-venta` vía `shared/pdf` (008). Genera la **CxC** por el saldo pendiente. Dispara el **recálculo de nivel de fidelización** (006). **Anulación/devolución** con reingreso de stock y reversas. **Consumidor final** solo para piezas sueltas bajo un monto configurable.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `shared/pdf`, `shared/pagos` (008), `shared/descuentos` (006), `shared/guard`, `shared/auditoria`, `shared/parametros`, `shared/storage`; consume 003 (relojes, piezas, stock, evento_serie), 006 (cliente, descuentos, nivel), 007 (cita), 001 (`medio_pago`)

**Storage**: PostgreSQL; MinIO `comprobantes-venta`

**Testing**: `pytest` — **cobertura obligatoria (Const. Ppio IX)**: cálculo de margen de venta, margen mínimo tras descuentos/cupones; `vitest`

**Project Type**: Web — módulo `ventas`

**Performance Goals**: confirmar una venta < 4 min (UX); cálculo de margen < 150 ms; PDF asíncrono < 3 s

**Constraints**: stock nunca negativo; margen y validaciones en backend; venta de reloj siempre con cliente identificado; comprobantes sin costos/márgenes; sin SRI (modelo compatible)

**Scale/Scope**: pocas ventas de reloj/semana; ventas de piezas sueltas ocasionales

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan Ppio II, §2.2, §4.4, §4.8.2, §4.11.2, §7, §4.10. ✅ |
| II | La venta es un INSERT ligado a un documento real; baja de stock y evento de serie reales. ✅ |
| III | PostgreSQL OLTP; PDF a `comprobantes-venta`. ✅ |
| IV | Módulo `ventas`; anulación auditada. ✅ |
| V | Margen y margen mínimo en backend; frontend solo consume. ✅ |
| VI | Referencia 003, 006, 007, 008, 001; reutiliza `shared/*`. ✅ |
| VII | Sin pasarela de pago en línea; reutiliza helpers de 008/006. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | **Cobertura obligatoria** del margen de venta y margen mínimo. ✅ |
| X | Módulo `ventas/` con capas; nada duplicado. ✅ |
| XI | "Confirmar venta"/"Anular"; modales; selectores sin texto libre; consulta de ventas del día. ✅ |
| XII | Comprobante y certificado con identidad visual. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/ventas/
├── router.py     # /ventas, /ventas/{id}/confirmar|anular, /ventas/{id}/pagos, /ventas-dia
├── service.py    # orden de venta, baja de stock, margen, garantías, comprobante, CxC, recálculo nivel
├── margen.py     # cálculo del margen de venta
├── repository.py
└── schemas.py

frontend/src/ventas/
├── components/ (PanelVenta, LineasVenta, PagosVenta, PanelGarantias, AnularVenta)
├── composables/ stores/ services/
```

**Structure Decision**: Un módulo. Reutiliza `shared/pdf`, `shared/pagos` (008), `shared/descuentos` (006); no duplica lógica.

## Complexity Tracking

*Sin violaciones.* Todo lo transversal (PDF, pagos, descuentos) ya existe como capacidad compartida.
