# Feature Specification: Inventario de Relojes y Piezas

**Feature Branch**: `003-inventario-relojes-piezas`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Ficha por unidad física de reloj identificada por número de serie único (§4.4), gestión de piezas y repuestos con stock y stock mínimo (§4.5), fotos por reloj en el bucket `reloj-imagenes`, alertas de stock (~12 / 1 unidad / mínimo de pieza) que abren la reposición de 002, y los reportes operativos de inventario e historial por número de serie (§4.11.1)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Alta de una unidad de reloj (Priority: P1)

El personal autorizado da de alta cada reloj como unidad física con su ficha completa (marca, referencia, número de serie, calibre, materiales, cristal, estado, costo, precio, Full Set, sucursal), vinculándola a la recepción de compra de 002 y adjuntando una o varias fotos.

**Why this priority**: El número de serie es la clave de trazabilidad de todo el sistema (§4.4, §6); sin el alta de unidades no hay ventas ni servicio técnico.

**Independent Test**: Registrar una unidad con ficha completa y foto, y recuperarla íntegra incluyendo la imagen desde `reloj-imagenes`.

**Acceptance Scenarios**:

1. **Given** una recepción de compra registrada en 002, **When** se da de alta una unidad vinculada a esa línea, **Then** la ficha hereda proveedor, costo de adquisición y fecha de ingreso.
2. **Given** un número de serie ya existente, **When** se intenta registrar otra unidad con el mismo, **Then** el sistema lo rechaza.
3. **Given** una unidad dada de alta, **When** se sube una foto, **Then** se almacena en `reloj-imagenes` y se sirve a la app sin pasar por disco local.

---

### User Story 2 - Consultar el estado del inventario (Priority: P1)

Cualquier usuario con acceso consulta el estado de inventario actual de relojes disponibles y de piezas, con filtros reactivos (marca, modelo, sucursal, estado) y paginación.

**Why this priority**: Reporte operativo de consulta rápida de disponibilidad, de uso diario en mostrador (§4.11.1).

**Independent Test**: Filtrar por marca y sucursal y comprobar que el resultado coincide con las unidades activas.

**Acceptance Scenarios**:

1. **Given** unidades en varias sucursales, **When** se filtra por una sucursal, **Then** solo se listan las de esa sucursal, paginadas.
2. **Given** una unidad vendida, **When** se consulta el inventario disponible, **Then** no aparece, pero sí en la consulta por número de serie.

---

### User Story 3 - Gestión de piezas y repuestos (Priority: P1)

El personal mantiene el catálogo de piezas con código, descripción, tipo (original / no original de calidad equivalente), calibres compatibles, proveedor, costo, precio de venta suelta, stock y stock mínimo.

**Why this priority**: Las piezas se consumen en las órdenes de trabajo (008) y se venden sueltas (009); su stock alimenta las alertas.

**Independent Test**: Crear una pieza, ajustar su stock y verificar el historial de movimientos.

**Acceptance Scenarios**:

1. **Given** una pieza nueva, **When** se registra con calibres compatibles, **Then** es seleccionable desde una orden de trabajo para esos calibres.
2. **Given** una pieza con stock 0, **When** una OT intenta consumirla, **Then** el sistema impide dejar stock negativo.

---

### User Story 4b - Insumos perecederos con lote y caducidad (Priority: P2)

Una pieza o insumo (p. ej. lubricantes Moebius) puede marcarse como "perecedero"; en ese caso cada ingreso registra lote y fecha de caducidad, y el sistema alerta cuando un lote está próximo a vencer o vencido.

**Why this priority**: Un número limitado de repuestos/insumos caduca; sin control de caducidad se usan productos vencidos o se pierde trazabilidad del consumo real (§4.6).

**Independent Test**: Marcar un lubricante como perecedero, ingresar dos lotes con fechas distintas y verificar la alerta de caducidad próxima.

**Acceptance Scenarios**:

1. **Given** una pieza marcada como perecedera, **When** se registra un ingreso, **Then** el sistema exige lote y fecha de caducidad.
2. **Given** un lote a menos de N días de caducar (umbral configurable), **When** se consulta el inventario, **Then** aparece la alerta de caducidad próxima.
3. **Given** un lote vencido, **When** se intenta consumirlo en una OT, **Then** el sistema advierte y ofrece darlo de baja por merma (011, causa "insumo caducado").

---

### User Story 4 - Alertas de stock y reposición (Priority: P2)

El sistema alerta cuando el stock de un modelo/marca se acerca al máximo recomendado (~12) o queda 1 unidad, y cuando una pieza baja de su mínimo; la alerta ofrece "Reponer stock" que abre la orden de compra de 002 prellenada.

**Why this priority**: §4.4 y §4.5 piden alertas de reposición; Const. Ppio XI exige que la sugerencia abra el flujo concreto.

**Independent Test**: Llevar un modelo a 1 unidad y comprobar la alerta y que su acción abre la orden de compra con datos puestos.

**Acceptance Scenarios**:

1. **Given** un modelo con 2 unidades y umbral de alerta en 2, **When** se vende una, **Then** aparece la alerta de reposición para ese modelo.
2. **Given** una alerta de reposición, **When** el usuario pulsa "Reponer stock", **Then** se abre la creación de orden de compra (002) con proveedor, modelo y cantidad sugerida prellenados.
3. **Given** un modelo que supera el máximo recomendado, **When** se da de alta otra unidad, **Then** el sistema alerta pero no bloquea el alta.

---

### User Story 5 - Historial por número de serie (Priority: P2)

Al recibir un reloj en mostrador o taller, el personal consulta por número de serie la ficha y todo su historial: ingreso, servicios, transferencias y baja.

**Why this priority**: Consulta técnica al recibir un reloj (§4.11.1) y requisito de trazabilidad inalterable (§6).

**Independent Test**: Consultar un número de serie con eventos de varios tipos y comprobar el orden cronológico y la no editabilidad.

**Acceptance Scenarios**:

1. **Given** un número de serie con ingreso y (más adelante) servicios, **When** se consulta, **Then** se ven todos los eventos ordenados por fecha.
2. **Given** el historial de un número de serie, **When** un usuario intenta editar un evento pasado, **Then** el sistema no lo permite.

### Edge Cases

- ¿Qué pasa si se intenta dar de alta una unidad sin recepción de compra asociada?
- ¿Qué pasa con la foto si la subida al bucket falla a mitad?
- ¿Qué pasa si dos ventas simultáneas intentan tomar la última unidad de un modelo?
- ¿Qué pasa al cambiar el precio de venta de una unidad que ya está en una venta en curso?
- ¿Qué pasa si el stock máximo recomendado se reduce por debajo del stock actual?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE gestionar cada reloj como unidad física identificada por número de serie único e irrepetible. [Esp. §4.4]
- **FR-002**: La ficha de reloj DEBE incluir: marca, referencia/modelo, número de serie, calibre/movimiento, año de fabricación, material de caja y brazalete, color de esfera, tipo de cristal, resistencia al agua, estado (nuevo/usado), costo de adquisición, precio de venta, fecha de ingreso a stock, proveedor, Full Set (sí/no + detalle: caja, papeles, garantía, eslabones extra), sucursal actual. [Esp. §4.4]
- **FR-003**: El alta de una unidad DEBE poder vincularse a una línea de recepción de compra de 002, heredando proveedor, costo y fecha de ingreso. [Esp. §4.2, §4.4]
- **FR-004**: El sistema DEBE almacenar una o varias fotos por unidad en el bucket `reloj-imagenes` y servirlas a la app; nunca en disco local. [Const. Ppio III; Const. "Stack"]
- **FR-005**: Cada número de serie DEBE mantener un historial inalterable de eventos (ingreso, venta, servicios, transferencias, baja). [Esp. §6 "Trazabilidad"]
- **FR-006**: El sistema DEBE gestionar piezas con código, descripción, tipo (original / no original de calidad equivalente), calibres/modelos compatibles, proveedor, costo de adquisición, precio de venta suelta, stock disponible y stock mínimo. [Esp. §4.5]
- **FR-006a**: Una pieza o insumo DEBE poder marcarse como "perecedero"; si lo es, cada ingreso registra lote y fecha de caducidad, y el sistema emite alerta de caducidad próxima (umbral configurable) y de lote vencido. Un lote vencido no se consume sin advertencia y puede derivarse a merma (011, causa "insumo caducado"). [Necesidad del negocio; Esp. §4.6]
- **FR-007**: El sistema DEBE registrar el historial de uso de cada pieza en órdenes de trabajo (poblado por 008). [Esp. §4.5]
- **FR-008**: El sistema DEBE ofrecer el reporte operativo "estado de inventario actual" de relojes y piezas, con filtros reactivos y paginación. [Esp. §4.11.1; Const. Ppio XI]
- **FR-009**: El sistema DEBE ofrecer el reporte operativo "historial de servicios de un reloj" por número de serie. [Esp. §4.11.1]
- **FR-010**: El stock máximo recomendado por modelo/marca DEBE ser un parámetro configurable (por defecto ~12). [Esp. §9.2, §2.1]
- **FR-011**: El umbral de alerta de reposición de relojes y de piezas DEBE ser configurable. [Esp. §9.2]
- **FR-012**: El sistema DEBE emitir alerta cuando el stock de un modelo/marca se acerque al máximo configurado o quede 1 unidad, y cuando una pieza esté en o por debajo de su mínimo; la alerta NO bloquea operaciones. [Esp. §4.4, §4.5]
- **FR-013**: La alerta de reposición DEBE ofrecer la acción "Reponer stock" que abre la creación de orden de compra de 002 prellenada con proveedor habitual, modelo/pieza y cantidad sugerida. [Const. Ppio XI; Esp. §4.4]
- **FR-014**: Un reloj vendido (009) o dado de baja por merma (011) DEBE salir del stock activo conservando ficha e historial completos. [Esp. §4.4, §4.12]
- **FR-015**: El stock de piezas NO puede quedar negativo; el consumo se confirma en la orden de trabajo (008) o en la venta suelta (009). [Esp. §4.5; Const. Ppio II]
- **FR-016**: Los cambios de costo de adquisición y de precio de venta DEBEN auditarse con actor, timestamp y valor anterior/nuevo. [Esp. §6 "Auditoría ... especialmente en precios y márgenes"]
- **FR-016a**: La corrección del número de serie u otros datos de la ficha de una unidad ya ingresada (p. ej. por error de digitación en la recepción de compra) SOLO se permite con rol elevado (Gerente de Sucursal o Gerencia General), con motivo y auditoría. [Necesidad del negocio; Esp. §6]
- **FR-017**: El sistema DEBE mostrar el valor del inventario a costo y a precio de venta como consulta operativa. [Esp. §4.11.2 "Valor total del inventario" — versión operativa; el análisis comparado es 013]
- **FR-018**: El módulo DEBE declarar sus permisos bajo "Inventario de relojes" y "Piezas"; por defecto Vendedor y Técnico solo Consultar. [Esp. §3.1; Const. Ppio IV]
- **FR-019**: El costo de adquisición y el margen DEBEN poder restringirse a roles administrativos. [Esp. §6 "restringir información financiera sensible"]
- **FR-020**: El panel de trabajo DEBE usar el set estandarizado de acciones y ofrecer exportación CSV/Excel/PDF de los reportes de inventario. Los listados DEBEN ofrecer búsqueda multi-criterio (relojes por marca, referencia/modelo, número de serie, calibre, sucursal o estado; piezas por código, descripción, calibre o proveedor) y resolver la entrada por selección/filtrado, no por texto libre. [Const. Ppio XI]
- **FR-021**: El campo "sucursal actual" referencia el catálogo de sucursales de 001; la transferencia entre sucursales y su historial los añade 004. [Esp. §4.4, §4.9]

### Key Entities *(include if feature involves data)*

- **Reloj (unidad física)**: identificada por número de serie; todos los campos de §4.4; estado de disponibilidad (disponible / vendido / en servicio / dado de baja); sucursal actual.
- **FotoReloj**: referencia a objeto en `reloj-imagenes`, orden de visualización.
- **Calibre**: identificador y datos básicos del movimiento; la ficha de lubricación (puntos, productos Moebius) la añade 008.
- **Pieza**: código, descripción, tipo, calibres compatibles, proveedor, costo, precio suelto, stock mínimo.
- **MovimientoStockPieza**: pieza, sucursal, tipo (ingreso / consumo OT / venta suelta / ajuste / merma), cantidad, lote, referencia al documento.
- **LotePieza**: pieza perecedera, número de lote, fecha de caducidad, cantidad, sucursal, estado (vigente / próximo a vencer / vencido).
- **EventoTrazabilidadSerie**: número de serie, tipo de evento, fecha, referencia al documento origen. Inalterable.
- **AlertaStock**: ámbito (modelo/marca o pieza), sucursal, tipo (máximo / última unidad / bajo mínimo), estado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El alta de una unidad con ficha completa y una foto toma menos de 3 minutos y la imagen se recupera desde `reloj-imagenes`.
- **SC-002**: El estado de inventario actual coincide al 100% con las altas, ventas y bajas registradas.
- **SC-003**: Al quedar 1 unidad de un modelo, la alerta aparece y su acción "Reponer" abre la orden de compra prellenada.
- **SC-004**: El historial por número de serie muestra todos los eventos en orden cronológico y rechaza toda edición retroactiva.
- **SC-005**: El 100% de los cambios de costo o precio queda auditado.
- **SC-006**: Superar el máximo recomendado genera alerta sin impedir el alta.
- **SC-007**: En 0 casos el stock de una pieza queda negativo (pruebas de concurrencia).

## Assumptions

- 001 y 002 están implementadas.
- El catálogo de calibres lo crea esta feature (identificador y datos básicos); la ficha de lubricación por calibre la añade 008.
- El historial de servicios de un reloj se puebla desde 008; el de transferencias desde 004; la venta desde 009; la baja por merma desde 011.
- La venta de piezas sueltas se registra en 009; 003 solo aporta el precio de venta suelta.
- Los reportes analíticos de rotación de stock, margen por marca/modelo y comparativo de valor son 013 (desde ClickHouse).
- Las fotos de producto van al bucket `reloj-imagenes`; los escaneos de papeles del Full Set y otros documentos de la unidad van al bucket `documentos` (prefijo de reloj), servidos vía endpoint autenticado.
- El control de caducidad aplica a un número reducido de insumos (principalmente lubricantes); la mayoría de piezas no son perecederas y no requieren lote.
