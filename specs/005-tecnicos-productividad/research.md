# Research: Técnicos y Productividad

**Feature**: `005-tecnicos-productividad` | **Phase**: 0 | **Date**: 2026-09-10

Sin `NEEDS CLARIFICATION` (el costeo por tarifa horaria fue decisión del negocio).

## D1 — Costo de mano de obra por OT

- **Decisión**: `tarifa_hora(tecnico, fecha) = esquema_costo.sueldo_mensual / parametro("horas_productivas_estandar_mes")` (def. 160). `costo_mo_ot = tarifa_hora × horas_registradas`. Si `horas_registradas` es null, `costo_mo_ot = tarifa_hora × tiempo_estimado(tipo_reparacion)` (parámetro de 008/§9.2). Función pura en `costeo.py`, llamada por 008.
- **Rationale**: decisión del negocio; §5 ("prorrateado por orden").
- **Alternativas**: partes iguales por número de OT del mes (menos preciso); sueldo como gasto fijo (no atribuye margen por OT). Ambas descartadas por el negocio.

## D2 — Prorrateo del bono

- **Decisión**: el bono acumulado del periodo se calcula al **cerrar el periodo** (o en preview). Se reparte entre las OT cerradas del periodo proporcionalmente a su `costo_mo_ot`. Cada OT recibe `bono_asignado = bono_total × (costo_mo_ot / Σ costo_mo_ot del periodo)`, que 008 suma al costo de MO en los reportes de margen.
- **Rationale**: §5 ("reflejarlo como parte del costo de mano de obra en los reportes de margen").
- **Alternativas**: prorrateo por número de OT (ignora la carga real).

## D3 — Motor de bono configurable

- **Decisión**: `regla_bono` (periodo, vigencia) con una lista de `componente_bono`:
  - `tipo` ∈ {monto_por_meta, porcentaje_margen, combinacion}
  - `indicador` ∈ {ot_completadas, cumplimiento_tiempos, margen_generado, calidad}
  - `umbral` (valor a superar), `valor` (monto o porcentaje)
  El bono del técnico = suma de los componentes cuyo `indicador` supera su `umbral` en el periodo. Evaluación 100% en backend, con función pura testeable.
- **Rationale**: §5, §9.1.
- **Alternativas**: DSL/fórmula libre — potente pero riesgoso y difícil de validar; se prefiere un conjunto acotado de componentes (KISS).

## D4 — Indicadores

- **Decisión**:
  - `ot_completadas`: conteo de OT del técnico con estado `entregado` y fecha en el periodo.
  - `cumplimiento_tiempos`: % de esas OT entregadas dentro de `fecha_estimada`.
  - `margen_generado`: Σ margen real de esas OT (de 008).
  - `calidad`: 100 − (reprocesos/reclamos sobre el mismo reloj del técnico en el periodo ÷ OT) × 100.
- **Rationale**: §5 (lista explícita de indicadores).
- **Nota**: hasta que 008 exista, el motor se valida con OT de prueba (fixtures).

## D5 — Periodos y recálculo

- **Decisión**: `periodo_liquidacion` (rango, estado `abierto`/`cerrado`). El bono se materializa en `bono_acumulado` (técnico, periodo, valor, desglose). Cambiar `regla_bono` o `horas_productivas_estandar_mes` ⇒ `recalcular_por_parametro` recalcula `bono_acumulado` de periodos **abiertos**; los cerrados no. Registrado como consumidor en `shared/parametros` (001).
- **Rationale**: Const. "Parámetros configurables — recálculo en cascada"; §9.4.

## D6 — Técnico como usuario

- **Decisión**: `tecnico.usuario_id` FK opcional 1—1. Los datos de contacto y foto los edita el técnico vía autoservicio de 001. En 005: costo, especialidades, certificaciones e inactivación son de Técnico Jefe / Gerencia General.
- **Rationale**: §4.3; necesidad del negocio.

## D7 — Vista de productividad

- **Decisión**: `GET /productividad?periodo=...` devuelve por técnico: OT completadas, tiempo promedio de ejecución, margen generado, bono alcanzado. Es la versión operativa; el comparativo entre técnicos/periodos/sucursales es 013 (ClickHouse).
- **Rationale**: §4.3, §4.11.2, §4.11.3.
