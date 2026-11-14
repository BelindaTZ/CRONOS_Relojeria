# Implementation Plan: Gestión de Citas

**Branch**: `007-citas` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Registro manual de citas por el personal (§4.1): cliente (ficha existente de 006), fecha/hora preferida y confirmada, motivo (compra/servicio técnico/consulta), canal de origen (catálogo de 001), sucursal, observaciones. Estados pendiente → confirmada → cancelada/atendida. Agenda del día y de la semana por sucursal (§4.11.1). Al marcar "atendida", **vincular a la venta (009) o a la orden de trabajo (008)**; si no existe, abrir el flujo de creación con el cliente cargado (Const. Ppio XI). Tasa de conversión operativa. Exposición de datos para los recordatorios de 014.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `shared/guard` (scope por sucursal), `shared/auditoria`; consume 001 (canal_cita, sucursal), 006 (cliente); expone vínculo a 008/009 y datos a 014

**Storage**: PostgreSQL

**Testing**: `pytest` (ciclo de estados, vínculo a transacción, agenda), `vitest`

**Project Type**: Web — módulo `citas`

**Performance Goals**: registrar una cita < 1 min (UX); agenda del día < 1 s

**Constraints**: cita siempre con cliente existente; canal del catálogo (sin texto libre); sin lectura de correo entrante; sin gestión de slots

**Scale/Scope**: decenas de citas/semana por sucursal

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.1, §4.11.1, §4.11.2, §9.3. ✅ |
| II | Citas y cambios de estado son registros reales. ✅ |
| III | PostgreSQL OLTP. ✅ |
| IV | Módulo `citas`; Vendedor sin "Eliminar" por defecto. ✅ |
| V | Reglas de estado y vínculo en backend. ✅ |
| VI | Referencia 001, 006, 008, 009, 014; no los redefine. ✅ |
| VII | Sin lectura de Gmail ni motor de agenda; registro manual. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | Cobertura del ciclo de estados y del vínculo. ✅ |
| X | Módulo `citas/` con capas. ✅ |
| XI | Filtros reactivos; "Confirmar"/"Cancelar"; modales; "atender" abre flujo real; exportación. ✅ |
| XII | Pantallas con `ui-ux-pro-max`. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/citas/
├── router.py     # /citas, /citas/{id}/confirmar|cancelar|atender, /agenda
├── service.py    # ciclo de estados, vínculo a venta/OT, conversión, aviso de solape
├── repository.py
└── schemas.py

frontend/src/citas/
├── components/ (ListaCitas, PanelCita, AgendaDia, AgendaSemana)
├── composables/ (useCitas, useAgenda)
├── stores/ (citasStore)
└── services/ (citasApi)
```

**Structure Decision**: Un módulo. El vínculo cita→venta/OT se guarda como FK anulable; la acción "atender sin transacción previa" navega en el frontend al flujo de 008/009 pasando `cliente_id` y `cita_id` como contexto.

## Complexity Tracking

*Sin violaciones.*
