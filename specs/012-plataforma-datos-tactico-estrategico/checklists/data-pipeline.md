# Data Pipeline Quality Checklist: ELT (012)

**Purpose**: Checklist adicional de calidad para el pipeline ELT — valida que los requisitos garantizan un pipeline correcto, idempotente, observable y no invasivo.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Aislamiento de la fuente

- [x] DP001 ¿Se especifica que la extracción es estrictamente de solo lectura sobre PostgreSQL? [Completeness, Spec §FR-006]
- [x] DP002 ¿Se especifica que el pipeline usa credenciales/rol de solo lectura y no el usuario de la app? [Gap]
- [x] DP003 ¿Se especifica que un fallo del pipeline no puede degradar la operación (health, endpoints)? [Consistency, Spec §FR-011]

## Idempotencia y reprocesamiento

- [x] DP004 ¿Se especifica el mecanismo de dedup en la carga (clave + versión)? [Clarity, research D3]
- [x] DP005 ¿Se especifica cómo se reprocesa un rango histórico (full-refresh / borrar watermark)? [Completeness, Spec §FR-007]
- [x] DP006 ¿Se especifica el comportamiento ante un reintento parcial (una fase falló)? [Coverage]
- [x] DP007 ¿Se especifica que `landing-zone` es inmutable por corrida y versionado por `run_id`? [Clarity, research D2]

## Observabilidad

- [x] DP008 ¿Cada fase (Extract/Load raw/Load wh/Transform) es una tarea Airflow observable por separado? [Completeness, Spec §FR-005]
- [x] DP009 ¿Se registra por corrida el dominio, la fase, filas y estado? [Completeness, Data-model pipeline_corrida]
- [x] DP010 ¿El estado de frescura distingue "cargado ok", "error" y "sin datos"? [Clarity, Contracts pipeline-estado]

## Cobertura de dominios y modelos

- [x] DP011 ¿Cada dominio operativo (ventas, OT, inventario, citas, mermas, contabilidad, fidelización, técnicos, proveedores) tiene su extracción? [Coverage, Spec §FR-008]
- [x] DP012 ¿Cada uno de los 18 reportes de §4.11.2 tiene un modelo/vista que lo alimenta? [Coverage, Spec §FR-008]
- [x] DP013 ¿Todos los modelos admiten los filtros periodo/sucursal/marca/técnico donde aplica? [Completeness, Spec §FR-009]
- [x] DP014 ¿Las anulaciones/bajas se reflejan (estado sobrescrito) y las agregaciones las filtran? [Consistency, Spec §FR-013; research D4]

## Retención y respaldo

- [x] DP015 ¿`landing-zone` tiene política de retención parametrizable? [Completeness, Spec §FR-012]
- [x] DP016 ¿Hay procedimiento de respaldo del warehouse y de los DAGs/variables de Airflow? [Completeness, Spec §FR-015]

## Evolución del esquema de origen

- [x] DP017 ¿El pipeline tolera columnas/tablas nuevas en el origen sin romperse? [Coverage, Spec §FR-018]
- [x] DP018 ¿Se especifica cómo se añade un dominio nuevo (feature futura) al DAG? [Gap]
