# Implementation Plan: Servicio Técnico y Lubricación

**Branch**: `008-servicio-tecnico-lubricacion` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Órdenes de trabajo (§4.7) con trazabilidad por número de serie, sobre relojes adquiridos en la tienda. **Fichas de lubricación por calibre** (§4.6): puntos, producto Moebius recomendado, registro del producto realmente usado por punto → auditoría de desviaciones y consumo real de insumos. **Costeo y margen del servicio** (§5): costo interno = mano de obra por tarifa horaria (005) × horas registradas + piezas + insumos; precio = costo + margen objetivo configurable; margen real automático. **Paso de presupuesto** con elección de piezas originales / no originales (aprobación fuera del sistema, resultado registrado). **Fecha estimada solo tras diagnóstico**. **Aviso por email al cliente** con datos del técnico asignado. Ciclo recibido → diagnóstico → (presupuesto) → reparación → listo → entregado; **cobro al retiro** (sin pago no se entrega) usando el registro de pagos multimedios que esta feature introduce en `shared/`. Descuentos vía `shared/descuentos` (006). Documento de OT + certificado de garantía a `comprobantes-venta` (helper PDF que esta feature introduce en `shared/`). Merma por daño en servicio → 011. Informe de servicios/arreglos.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `weasyprint` o `reportlab` (PDF, en `shared/pdf`); `shared/guard` (scope "solo las propias" para técnico), `shared/auditoria`, `shared/parametros`, `shared/correo` (001), `shared/descuentos` (006), `shared/storage`; consume 003 (relojes, piezas, calibres, stock), 005 (costo MO, indicadores de bono), 006 (cliente, descuentos), 007 (cita)

**Storage**: PostgreSQL; MinIO `comprobantes-venta` (documento OT + certificado), `documentos` (cotizaciones/actas si aplica)

**Testing**: `pytest` — **cobertura obligatoria (Const. Ppio IX)**: cálculo de margen del servicio, margen mínimo tras descuentos, registro/consumo de insumos; `vitest`

**Project Type**: Web — módulos `servicio_tecnico` y `lubricacion`; introduce `shared/pdf` y `shared/pagos`

**Performance Goals**: crear OT < 3 min (UX); cálculo de margen < 200 ms; generación de PDF < 3 s (asíncrona)

**Constraints**: reloj `en_transito` no entra a OT; stock de pieza nunca negativo; costo/margen nunca al cliente; OT no `entregado` sin pago o crédito autorizado; fecha estimada solo post-diagnóstico; presupuesto aprobado antes de `reparación`

**Scale/Scope**: decenas de OT/mes por sucursal

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.6, §4.7, §5, §9.2, §2.1, §7, §4.12, §4.11.1. ✅ |
| II | OT, presupuestos, lubricación, pagos son registros reales ligados al documento OT. ✅ |
| III | PostgreSQL OLTP; PDF a `comprobantes-venta`. ✅ |
| IV | Módulos `ordenes_trabajo` y `lubricacion`; técnico solo edita sus OT. ✅ |
| V | Costeo, margen y margen mínimo en backend; nunca en frontend. ✅ |
| VI | Referencia 003, 005, 006, 007; no los redefine. ✅ |
| VII | PDF con una sola librería; pagos multimedios como helper simple; sin motor de reglas. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | **Cobertura obligatoria** de margen del servicio y margen mínimo. ✅ |
| X | `servicio_tecnico/`, `lubricacion/`; helpers en `shared/pdf`, `shared/pagos`. ✅ |
| XI | "Cerrar orden"; modales; presupuesto y elección de piezas con selectores; exportación del informe. ✅ |
| XII | Documento de OT y certificado con identidad visual (`ui-ux-pro-max`). ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/
├── servicio_tecnico/
│   ├── router.py     # /ordenes-trabajo, /{id}/diagnostico|presupuesto|estado|entregar, /informe-servicios
│   ├── service.py    # ciclo, costeo, margen, presupuesto, cobro, merma-derivada, aviso técnico
│   ├── costeo.py     # costo interno del servicio (usa 005) + margen
│   ├── repository.py
│   └── schemas.py
├── lubricacion/
│   ├── router.py     # /calibres/{id}/ficha-lubricacion, /productos-moebius
│   ├── service.py    # ficha por calibre, registro por punto, consumo real
│   ├── repository.py
│   └── schemas.py
└── shared/
    ├── pdf/           # render de documento OT y certificado (Jinja2 -> weasyprint) con identidad visual
    └── pagos/         # registrar_pago(documento, medio, monto), saldo(documento)

frontend/src/servicio_tecnico/ + frontend/src/lubricacion/
```

**Structure Decision**: Dos módulos de negocio. `shared/pdf` y `shared/pagos` son capacidades compartidas que 009 reutiliza (Const. "Entidades compartidas").

## Complexity Tracking

| Elemento | Por qué | Alternativa más simple rechazada porque |
|---|---|---|
| `shared/pagos` (multimedios contra documento) | §4.10 + necesidad del negocio (cheque/tarjeta/efectivo mixto) en OT y venta | Pago único por documento: el negocio cobra con medios mixtos |
| `shared/pdf` | Const. Ppio III (documento OT + certificado); reutilizado por 009 | Generar HTML imprimible sin PDF: el certificado de garantía debe ser archivo estable en `comprobantes-venta` |
