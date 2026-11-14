# Implementation Plan: Inventario de Relojes y Piezas

**Branch**: `003-inventario-relojes-piezas` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Ficha por **unidad física** de reloj identificada por número de serie único (§4.4), con todos los campos y **fotos** en `reloj-imagenes`. Catálogo de **calibres** (datos básicos; la ficha de lubricación la añade 008). Gestión de **piezas** (§4.5) con stock/stock mínimo y, para insumos marcados **perecederos**, **lote y fecha de caducidad** con alerta de vencimiento. **Historial inalterable** de eventos por número de serie. **Alertas de stock** (~12 / última unidad / bajo mínimo) que abren la reposición de 002. Reportes operativos: estado de inventario e historial por número de serie. Corrección de número de serie u otros datos solo con rol elevado. Restricción de costo/margen a roles administrativos.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `shared/guard`, `shared/storage` (fotos), `shared/auditoria`, `shared/parametros` (umbrales, stock máximo)

**Storage**: PostgreSQL; MinIO `reloj-imagenes` (fotos), `documentos` (escaneos de papeles del Full Set)

**Testing**: `pytest` (invariante de stock no negativo bajo concurrencia; alertas; inmutabilidad del historial), `vitest`

**Project Type**: Web — módulos `inventario` (relojes + calibres) y `piezas`

**Performance Goals**: alta de unidad + foto < 3 min (UX); estado de inventario < 1 s

**Constraints**: stock de piezas nunca negativo (bloqueo con `SELECT ... FOR UPDATE` / constraint); historial de serie inmutable (solo INSERT); fotos nunca en disco local

**Scale/Scope**: ~cientos de unidades, ~cientos de referencias de pieza, ~12 unidades por modelo

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.4, §4.5, §4.11.1, §9.2, §6, §2.1. ✅ |
| II | Altas/bajas/movimientos son INSERT/UPDATE reales ligados a compra/venta/OT/merma/transferencia. ✅ |
| III | PostgreSQL OLTP; fotos → `reloj-imagenes`; papeles → `documentos`. Sin ClickHouse. ✅ |
| IV | Módulos `inventario_relojes` y `piezas`; costo/margen restringible a rol administrativo. ✅ |
| V | Alertas y validaciones de stock en backend. ✅ |
| VI | Referencia 001 (sucursal, parámetros), 002 (recepción), 003 no redefine. ✅ |
| VII | Sin motor de forecasting; alertas simples por umbral. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | Cobertura: stock no negativo, alertas, historial inmutable. ✅ |
| X | `inventario/` y `piezas/` separados; nada en genérico. ✅ |
| XI | Búsqueda multi-criterio; alerta "Reponer" abre flujo real (002); exportación. ✅ |
| XII | Pantallas con `ui-ux-pro-max`. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/
├── inventario/
│   ├── router.py     # /relojes, /relojes/{serie}/historial, /calibres, /alertas-stock, valor-inventario
│   ├── service.py    # alta de unidad, foto, trazabilidad, alertas, corrección con rol elevado
│   ├── repository.py
│   └── schemas.py
└── piezas/
    ├── router.py     # /piezas, /piezas/{id}/movimientos, /lotes, alertas de caducidad
    ├── service.py    # stock (nunca negativo), lote/caducidad, alertas
    ├── repository.py
    └── schemas.py

frontend/src/
├── inventario/ (ListaRelojes, FichaReloj con galería, HistorialSerie, PanelAlertasStock, CatalogoCalibres)
└── piezas/     (ListaPiezas, FichaPieza, MovimientosPieza, LotesCaducidad)
```

**Structure Decision**: Dos módulos (`inventario` para relojes/calibres, `piezas` para repuestos/insumos) porque tienen ciclos de vida distintos (unidad física con serie vs. stock por cantidad y lote). Comparten `shared/`.

## Complexity Tracking

*Sin violaciones.* El control de lote/caducidad se limita a piezas marcadas `perecedera` (número reducido de insumos), evitando complejidad para el 95% del catálogo.
