# Implementation Plan: Técnicos y Productividad

**Branch**: `005-tecnicos-productividad` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Ficha de RRHH técnico (§4.3): especialidades, certificaciones, sucursales, vínculo a `usuario`. **Costeo de mano de obra por tarifa horaria** (sueldo mensual ÷ horas productivas estándar configurables; costo de la OT = tarifa × horas registradas, fallback al tiempo estimado del tipo de reparación). **Esquema de bono por productividad configurable** (§5): indicadores objetivos (OT completadas, cumplimiento de tiempos, margen generado, calidad), umbrales y fórmula (monto fijo / % margen / combinación); **motor de acumulación** por técnico y periodo, con el bono **prorrateado entre las OT cerradas** del periodo proporcional al costo de MO. Vista operativa de productividad. Autoedición limitada del técnico (solo contacto/foto, vía 001) y sin autoinactivación.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `shared/guard`, `shared/auditoria`, `shared/parametros` (fórmula/umbrales del bono, horas estándar); consume 001 (`usuario`, `sucursal`), 004 (sucursales); expone contrato de costo de MO a 008

**Storage**: PostgreSQL

**Testing**: `pytest` — **módulo con cobertura obligatoria (Const. Ppio IX)**: cálculo de bono por productividad, tarifa horaria, prorrateo

**Project Type**: Web — módulo `tecnicos`

**Performance Goals**: alta de técnico < 3 min; cálculo de bono de un periodo < 2 s

**Constraints**: bono nunca negativo; costo de MO restringido a rol administrativo y nunca en documentos del cliente; cambios de fórmula recalculan solo periodos abiertos

**Scale/Scope**: pocos técnicos por sucursal, periodos mensuales

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.3, §5, §9.1, §9.4, §6, §8. ✅ |
| II | Ficha, esquemas y bonos acumulados son registros reales. ✅ |
| III | PostgreSQL OLTP. ✅ |
| IV | Módulo `tecnicos`; costo/bono restringidos a rol administrativo. ✅ |
| V | Cálculo de bono y prorrateo en backend; nunca en frontend. ✅ |
| VI | Referencia 001, 004, 008; no los redefine. ✅ |
| VII | Bono como parámetros tipados; sin motor de reglas externo. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | **Cobertura obligatoria** del cálculo de bono. ✅ |
| X | Módulo `tecnicos/` con capas. ✅ |
| XI | Listados con búsqueda; exportación de productividad; sin texto libre en selectores. ✅ |
| XII | Pantallas con `ui-ux-pro-max`. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/tecnicos/
├── router.py     # /tecnicos, /tecnicos/{id}/costo, /reglas-bono, /bonos, /productividad
├── service.py    # tarifa horaria, motor de bono, prorrateo, productividad
├── costeo.py     # contrato consumido por 008: costo_mano_obra_ot(tecnico, horas, tipo_reparacion)
├── repository.py
└── schemas.py

frontend/src/tecnicos/
├── components/ (ListaTecnicos, FichaTecnico, EsquemaCosto, ReglaBono, PanelProductividad)
├── composables/ stores/ services/
```

**Structure Decision**: Un módulo. `costeo.py` expone la API interna que 008 llama para el costo de MO por OT; el motor de bono se registra como **consumidor de parámetros** en `shared/parametros` para el recálculo en cascada de 001.

## Complexity Tracking

| Elemento | Por qué | Alternativa más simple rechazada porque |
|---|---|---|
| Motor de bono configurable (indicadores + fórmula) | §5 exige fórmula y umbrales configurables, no fijos | Bono fijo hardcodeado: viola §5 y Ppio VII (no se puede ajustar sin código) |
