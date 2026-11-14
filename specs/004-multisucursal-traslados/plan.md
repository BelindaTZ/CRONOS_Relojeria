# Implementation Plan: Multi-Sucursal y Traslados de Inventario

**Branch**: `004-multisucursal-traslados` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Flujo de **transferencia** de unidades de reloj y cantidades de pieza entre sucursales (§4.9): envío con motivo y responsable, ítems pasan a `en_transito` (fuera de disponibilidad en origen), recepción en destino con actualización automática del inventario en ambas sucursales, discrepancia que puede derivar a merma (011), cancelación que devuelve los ítems al origen. Historial de transferencias por número de serie y por sucursal. Aplicación del **scoping por sucursal** (001) a los reportes y listados de inventario (propia vs. consolidada). Funciona con una sola sucursal activa y escala a N.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `shared/guard` (scoping), `shared/auditoria`; consume 003 (relojes, `stock_pieza`, `evento_serie`), 001 (`sucursal`)

**Storage**: PostgreSQL

**Testing**: `pytest` (integridad de stock en ambas sucursales, ítem en tránsito no vendible, cancelación reversible), `vitest`

**Project Type**: Web — módulo `traslados`

**Performance Goals**: registrar/confirmar una transferencia < 1 s

**Constraints**: sin nuevos servicios; ítem en tránsito no disponible para venta (009) ni servicio (008); origen ≠ destino; funciona con 1 sucursal

**Scale/Scope**: pocas sucursales, decenas de transferencias/mes

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.9, §4.4, §6, §3. ✅ |
| II | Transferencias y recepciones son registros reales; estados con persistencia. ✅ |
| III | PostgreSQL OLTP; sin ClickHouse. ✅ |
| IV | Módulo `multisucursal`; scoping por sucursal aplicado. ✅ |
| V | Reglas de disponibilidad e integridad en backend. ✅ |
| VI | Referencia 003 (inventario) y 001 (sucursal); no los redefine. ✅ |
| VII | Sin logística externa; solo hitos de envío/recepción. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | Cobertura: integridad de stock, tránsito, cancelación. ✅ |
| X | Módulo `traslados/` con capas. ✅ |
| XI | Panel con "Confirmar recepción"/"Cancelar"; modales; exportación. ✅ |
| XII | Pantallas con `ui-ux-pro-max`. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/traslados/
├── router.py     # /transferencias, /transferencias/{id}/enviar|recibir|cancelar, historial
├── service.py    # transiciones, actualización de inventario en ambas sucursales, discrepancias
├── repository.py
└── schemas.py

frontend/src/traslados/
├── components/ (ListaTransferencias, PanelTransferencia, RecepcionTransferencia)
├── composables/ (useTransferencias)
├── stores/ (transferenciasStore)
└── services/ (trasladosApi)
```

**Structure Decision**: Un módulo. La visibilidad por sucursal de los reportes de inventario se implementa aplicando los helpers `scope_sucursal` de 001 en los endpoints de 003 y en los propios; no se duplica lógica de scoping.

## Complexity Tracking

*Sin violaciones.*
