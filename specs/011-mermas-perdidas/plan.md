# Implementation Plan: Mermas y Pérdidas

**Branch**: `011-mermas-perdidas` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Registro de cualquier reloj o pieza que sale de stock por daño, pérdida, robo, defecto o **caducidad de insumo**, sin venta (§4.12). Datos: bien afectado, causa, fecha, sucursal, responsable, **costo a costo de adquisición**, ciclo de estados (en evaluación / dado de baja / en reclamo a proveedor / en reclamo a seguro / reparado y reingresado), documento(s) de soporte en el bucket `documentos`, y usuario que autoriza. **Umbral configurable** de autorización de Gerencia General para la baja definitiva (§9.2). Al confirmar la baja: retiro del inventario activo conservando historial + **asiento automático de pérdida extraordinaria en 010**. Vínculos a la OT y al técnico (desde 008) o a la transferencia (desde 004). Reporte de mermas por monto/causa/frecuencia.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `shared/guard`, `shared/auditoria`, `shared/parametros` (umbral), `shared/storage` (bucket `documentos`); consume 003 (reloj, pieza, stock, evento_serie, lote), 008 (OT/técnico), 004 (transferencia), 002 (proveedor), 010 (asiento automático)

**Storage**: PostgreSQL; MinIO `documentos` (actas, fotos, denuncias)

**Testing**: `pytest` — **cobertura obligatoria (Const. Ppio IX)**: registro/costeo de mermas, umbral de autorización, baja del inventario y asiento; `vitest`

**Project Type**: Web — módulo `mermas`

**Performance Goals**: reportar una merma < 2 min (UX)

**Constraints**: costo a costo de adquisición (nunca a precio); no merma sobre bien vendido/dado de baja; merma de pieza ≤ stock; baja sobre umbral solo con autorización de Gerencia General

**Scale/Scope**: pocas mermas/mes

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.12, §4.10.1, §9.2, §4.11.2, §3.1, §6, §4.6. ✅ |
| II | Cada merma es un registro real ligado al bien y (si aplica) a OT/transferencia. ✅ |
| III | PostgreSQL OLTP; soporte a `documentos`. ✅ |
| IV | Módulo `mermas`: Técnico crear/consultar, Gerente CRUD, Gerencia también autoriza bajas. ✅ |
| V | Costeo, umbral y baja en backend. ✅ |
| VI | Referencia 003, 008, 004, 002, 010; no los redefine. ✅ |
| VII | Reclamos como seguimiento de estado; sin integración externa. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | **Cobertura obligatoria** del registro/costeo de mermas. ✅ |
| X | Módulo `mermas/` con capas. ✅ |
| XI | "Autorizar baja"; modales para causa/motivo/id que autoriza; exportación. ✅ |
| XII | Pantallas con `ui-ux-pro-max`. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/mermas/
├── router.py     # /mermas, /mermas/{id}/estado|autorizar-baja|reclamo, /reportes/mermas
├── service.py    # costeo, ciclo, autorización, baja + asiento, reingreso
├── repository.py
└── schemas.py

frontend/src/mermas/
├── components/ (ListaMermas, PanelMerma, AutorizarBaja, ReclamoPanel, ReporteMermas)
├── composables/ stores/ services/
```

**Structure Decision**: Un módulo. La creación de una merma puede originarse desde 008 (daño en servicio), 004 (discrepancia de transferencia) o 003 (lote vencido) mediante payloads prellenados; el ciclo de vida y la baja son responsabilidad de este módulo.

## Complexity Tracking

*Sin violaciones.*
