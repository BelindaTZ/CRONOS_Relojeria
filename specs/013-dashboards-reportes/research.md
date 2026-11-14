# Research: Dashboards y Reportes

**Feature**: `013-dashboards-reportes` | **Phase**: 0 | **Date**: 2026-09-10

## D1 — Panel principal de Gerencia General

- **Decisión**: `GET /panel?periodo=` devuelve 6 KPIs: (1) margen del periodo, (2) rentabilidad neta por sucursal, (3) CxC vencidas, (4) rotación de stock, (5) productividad de técnicos, (6) clientes por nivel de fidelización. Cada KPI trae `valor`, `tendencia` (vs. periodo anterior) y `drill_down` (ruta + filtros para abrir el reporte o el flujo real). Máximo 8–10 KPIs (§4.11.3).
- **Rationale**: §4.11.3 (lista explícita).

## D2 — Carga asíncrona

- **Decisión**: el frontend pide cada KPI/reporte por separado y los renderiza a medida que llegan (skeleton loaders). El backend no bloquea: si un modelo tarda, los demás ya se ven.
- **Rationale**: Const. Ppio IX ("sin bloquear la interfaz, carga asíncrona").

## D3 — Catálogo de reportes y tipo de gráfico

- **Decisión**: `warehouse.py` tiene un catálogo `{slug: {modelo_ch, filtros_soportados, tipo_grafico}}` para los 18 reportes de §4.11.2. Tipo de gráfico por dato (Const. Ppio XI):
  - **barras**: margen por marca, productividad por técnico, rentabilidad por sucursal, comparativo costo vs. precio, piezas más usadas.
  - **pastel/dona**: clientes por nivel, mermas por causa.
  - **líneas**: margen mensual, rotación de stock, tiempo medio de servicio, tasa de reposición, conversión de citas (tendencia).
  - **KPI cards**: panel principal.
  - **tabla**: aging CxC/CxP, mejores clientes, valor total de inventario, desviación de lubricación (detalle).
- **Rationale**: §4.11.2, §4.11.3; Const. Ppio XI.

## D4 — Filtros reactivos

- **Decisión**: cada reporte declara los filtros que soporta (periodo, sucursal, marca, técnico). El frontend los aplica al cambiar el criterio (sin botón "Buscar"). Selectores poblados desde el warehouse/dimensiones.
- **Rationale**: §4.11.3; Const. Ppio XI.

## D5 — Sello de frescura y "actualizar ahora"

- **Decisión**: `SelloFrescura` consume `GET /reportes/estado-frescura` (012) y muestra "actualizado a HH:MM" por dominio. Un botón "Actualizar ahora" llama `POST /reportes/actualizar-ahora` (012) — es una acción real, no un mensaje (Const. Ppio XI).
- **Rationale**: §4.11.3; Const. Ppio IX, Ppio XI.

## D6 — Degradación

- **Decisión**: si ClickHouse/Airflow no responden, `service.py` devuelve `{disponible: false, motivo}` y el frontend muestra un estado claro ("Datos analíticos no disponibles — última actualización: …") sin stack trace. La navegación operativa sigue intacta.
- **Rationale**: §4.11.3; Const. Ppio IX, Ppio XI.

## D7 — Índice de reportes simples

- **Decisión**: `GET /reportes/indice` devuelve la lista de reportes operativos de §4.11.1 con su ruta en el módulo dueño, filtrada por los permisos del usuario: agenda de citas (007), estado de inventario (003), OT en curso (008), CxC pendientes (010), historial de cliente (006), historial de un reloj (003), **informe de servicios/arreglos (008)**.
- **Rationale**: §4.11.1, §4.11.3.

## D8 — Drill-down que abre el flujo real

- **Decisión**: cada KPI/celda con acción define `{tipo: navegar|abrir_flujo, ruta, filtros|contexto}`. Ej.: "CxC vencidas" → abre `/contabilidad/cxc?estado=vencida`; "stock bajo mínimo" → abre la reposición de 002 prellenada. Nunca un mensaje "listo" sin efecto.
- **Rationale**: Const. Ppio XI ("Acciones que no llevan a nada").

## D9 — Exportación

- **Decisión**: `GET /reportes/{slug}/exportar?formato=csv|xlsx|pdf`. CSV/XLSX del mismo arreglo de filas; PDF = vista imprimible con el gráfico. Si el reporte tiene > 5 000 filas, solo `csv`.
- **Rationale**: Const. Ppio XI ("Exportación de reportes").

## D10 — Scope

- **Decisión**: `service.py` aplica `scope_sucursal` (001): un gerente de sucursal ve sus datos; Gerencia General consolidado o filtrado. Los complejos son para gerencia/administración; el panel para Gerencia General.
- **Rationale**: §3, §4.9, §4.11.3.
