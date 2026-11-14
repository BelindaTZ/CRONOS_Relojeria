# Feature Specification: Dashboards y Reportes

**Feature Branch**: `013-dashboards-reportes`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Panel principal de Gerencia General con 5–6 KPIs críticos (§4.11.3), reportes analíticos de §4.11.2 renderizados desde ClickHouse (012) con filtros por periodo/sucursal/marca/técnico y gráficos vue-echarts según el tipo de dato, índice unificado de los reportes simples de §4.11.1, carga asíncrona con sello de frescura, y exportación CSV/Excel/PDF."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Panel principal de Gerencia (Priority: P1)

Gerencia General abre un panel con 5–6 indicadores críticos del periodo (margen, rentabilidad neta por sucursal, CxC vencidas, rotación de stock, productividad de técnicos, clientes por nivel), con carga asíncrona y sello de "datos actualizados a HH:MM".

**Why this priority**: §4.11.3 lo define como la vista clave para la dirección; un panel saturado dificulta la lectura.

**Independent Test**: Abrir el panel y verificar que muestra los indicadores, carga sin bloquear y muestra la frescura.

**Acceptance Scenarios**:

1. **Given** el warehouse actualizado, **When** Gerencia General abre el panel, **Then** ve 5–6 KPIs con su valor del periodo y el sello de frescura.
2. **Given** el panel, **When** se cuentan los indicadores, **Then** no supera 8–10.
3. **Given** un KPI de "CxC vencidas", **When** se pulsa su acción, **Then** se abre el flujo de gestión de cobros con el contexto cargado (no un mensaje sin efecto).

---

### User Story 2 - Reportes analíticos con filtros (Priority: P1)

Un gerente o administrador abre un reporte de §4.11.2, aplica filtros de periodo, sucursal, marca o técnico de forma reactiva, ve el gráfico adecuado y la tabla de detalle, y lo exporta.

**Why this priority**: Son los reportes que orientan las decisiones de gestión (§4.11.2, §4.11.3).

**Independent Test**: Abrir "margen por marca", filtrar por periodo y sucursal y exportar.

**Acceptance Scenarios**:

1. **Given** el reporte "margen por marca y modelo", **When** se cambia el periodo, **Then** el gráfico y la tabla se actualizan sin pulsar "Buscar".
2. **Given** un reporte comparativo, **When** se muestra, **Then** usa un gráfico de barras (vue-echarts); una distribución usa pastel/dona; una tendencia usa líneas.
3. **Given** cualquier reporte, **When** se exporta, **Then** ofrece CSV, Excel y PDF (solo CSV si supera ~5 000 filas).

---

### User Story 3 - Degradación cuando el warehouse no está disponible (Priority: P2)

Si ClickHouse está caído o el pipeline no ha corrido, los reportes analíticos y el panel lo indican con un estado claro y el resto de la aplicación sigue usable.

**Why this priority**: Const. Ppio IX: los reportes agregados no deben bloquear la interfaz.

**Independent Test**: Detener ClickHouse y abrir el panel y un reporte analítico.

**Acceptance Scenarios**:

1. **Given** ClickHouse detenido, **When** se abre un reporte de §4.11.2, **Then** se muestra un estado "datos no disponibles" sin error críptico.
2. **Given** el mismo escenario, **When** se navega a un módulo operativo, **Then** funciona con normalidad.

---

### User Story 4 - Acceso unificado a los reportes simples (Priority: P2)

El personal accede a los reportes operativos de §4.11.1 (agenda de citas, inventario, OT en curso, CxC pendientes, historial de cliente, historial de un reloj) desde un índice unificado, filtrado por su rol.

**Why this priority**: §4.11.1 y §4.11.3: los reportes simples son de consulta libre según el rol.

**Independent Test**: Abrir el índice con distintos roles y verificar qué reportes aparecen.

**Acceptance Scenarios**:

1. **Given** un vendedor, **When** abre el índice de reportes, **Then** ve los operativos permitidos a su rol y no los complejos.

### Edge Cases

- ¿Qué pasa si el pipeline nunca corrió y el warehouse está vacío?
- ¿Qué pasa con un reporte que devuelve cero filas para el filtro elegido?
- ¿Qué pasa con un periodo muy amplio y mucho detalle (rendimiento)?
- ¿Qué pasa si un gerente de sucursal abre un reporte consolidado?
- ¿Qué pasa al exportar a PDF un reporte que incluye un gráfico?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE ofrecer el panel principal de Gerencia General con 5–6 indicadores: margen del periodo, rentabilidad neta por sucursal, cuentas por cobrar vencidas, rotación de stock, productividad de técnicos y clientes por nivel de fidelización. [Esp. §4.11.3]
- **FR-002**: El panel NO DEBE superar 8–10 indicadores. [Esp. §4.11.3]
- **FR-003**: Los reportes analíticos de §4.11.2 DEBEN leerse desde ClickHouse (012), no desde PostgreSQL. [Esp. §4.11.2; Const. Ppio III]
- **FR-004**: Cada reporte analítico DEBE admitir filtros por periodo, sucursal, marca y técnico según corresponda, aplicados de forma reactiva. [Esp. §4.11.3; Const. Ppio XI]
- **FR-005**: Los gráficos DEBEN construirse con `vue-echarts` sin otra librería de gráficos: barras para comparativos, pastel/dona para distribuciones, líneas para tendencias, tarjetas KPI para el panel. [Const. Ppio XI]
- **FR-006**: La carga de los reportes y del panel DEBE ser asíncrona y no bloquear la interfaz. [Const. Ppio IX; Esp. §4.11.3]
- **FR-007**: El sistema DEBE mostrar el sello de frescura de datos ("actualizado a HH:MM") tomado del estado del pipeline de 012. [Const. Ppio IX; Esp. §4.11.3]
- **FR-008**: Si el warehouse está caído o sin datos, los reportes analíticos DEBEN mostrar un estado claro, sin error críptico ni bloqueo. [Const. Ppio IX; Const. Ppio XI]
- **FR-009**: Toda pantalla de reporte DEBE ofrecer descarga en CSV, Excel y PDF mediante `frontend/src/shared/exportar.js`; para reportes de más de ~5 000 filas, solo CSV. [Const. Ppio XI]
- **FR-010**: El sistema DEBE ofrecer un índice unificado de navegación a los reportes simples de §4.11.1 (incluido el informe de servicios/arreglos de 008: cliente, fecha, técnico, repuestos, precio), filtrado por el rol del usuario. [Esp. §4.11.1, §4.11.3]
- **FR-011**: Los reportes complejos DEBEN ser accesibles principalmente para gerencia/administración; el panel principal, para Gerencia General. [Esp. §4.11.3; Const. Ppio IV]
- **FR-012**: El scoping por sucursal (001) DEBE aplicarse a todos los reportes (propia vs. consolidada según rol). [Esp. §3, §4.9, §6]
- **FR-013**: El módulo DEBE declarar sus permisos bajo "Reportes" en el esquema RBAC de dos niveles. [Esp. §3.1; Const. Ppio IV]
- **FR-014**: Todas las pantallas DEBEN construirse con la skill `ui-ux-pro-max` y la paleta del Principio XI, con acabado profesional. [Const. Ppio XII, Ppio XI]
- **FR-015**: Un indicador del panel que "recomiende" una acción DEBE abrir el flujo concreto correspondiente con el contexto cargado. [Const. Ppio XI "Acciones que no llevan a nada"]
- **FR-016**: El backend operativo NO DEBE recalcular agregaciones; toda la lógica analítica vive en el warehouse (012). [Const. Ppio III, Ppio VII]
- **FR-017**: Las tablas de detalle largas DEBEN paginarse. [Const. Ppio XI]

### Key Entities *(include if feature involves data)*

- **DefiniciónReporte**: identificador, título, fuente en el warehouse, filtros aplicables, tipo de gráfico. (Configuración de presentación; no es entidad OLTP.)
- **IndicadorPanel**: KPI del panel de Gerencia, valor del periodo, comparación/tendencia, acción de drill-down.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El panel de Gerencia carga sus 5–6 KPIs de forma asíncrona sin bloquear la interfaz y muestra el sello de frescura.
- **SC-002**: Cada reporte de §4.11.2 está disponible con sus filtros y el tipo de gráfico adecuado.
- **SC-003**: Cambiar un filtro actualiza el reporte sin recargar la página ni pulsar un botón "Buscar".
- **SC-004**: Todo reporte se exporta en los tres formatos (o solo CSV si supera ~5 000 filas).
- **SC-005**: Con el warehouse caído, el panel y los reportes muestran un estado claro y el resto de la aplicación sigue usable.
- **SC-006**: Un gerente de sucursal no ve datos de otra sucursal en ningún reporte.
- **SC-007**: El 100% de las acciones "recomendadas" del panel abre el flujo real correspondiente con contexto.

## Assumptions

- 012 está implementada (warehouse poblado y estado de frescura disponible); 001–011 ya cargados como fuente.
- Los reportes simples de §4.11.1 ya existen dentro de cada módulo (001–011); 013 los enlaza, no los reimplementa.
- El número exacto y la definición fina de cada reporte complejo puede ajustarse en el diseño detallado (§4.11.3), manteniendo la lista de §4.11.2 como cobertura mínima.
- No hay forecasting ni proyecciones (Const. "Stack").
- El panel principal es una sola vista; los drill-down navegan a los reportes o módulos correspondientes.
