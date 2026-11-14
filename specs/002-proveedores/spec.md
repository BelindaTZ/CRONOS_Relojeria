# Feature Specification: Proveedores y Órdenes de Compra

**Feature Branch**: `002-proveedores`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Ficha de proveedor con todos los datos obligatorios de §4.2, órdenes de compra y su recepción (historial de compras), calificación de confiabilidad 1–5 con criterios, y cálculo automático de tiempo de entrega real vs. pactado que retroalimenta la calificación. Punto de entrada para 'Reponer stock' desde Inventario."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mantener la ficha de proveedor (Priority: P1)

El personal autorizado registra y mantiene proveedores con nombre/razón social, contacto, teléfono, email, tipo (relojes, piezas originales, piezas no originales, lubricantes, herramientas), condiciones de pago, plazos de entrega y datos legales (RUC/NIT, certificación de distribución autorizada).

**Why this priority**: Sin proveedores no puede ingresarse stock (003) ni construirse el historial de compras ni las cuentas por pagar (010). [Esp. §4.2]

**Independent Test**: Crear un proveedor con todos los campos obligatorios y recuperarlo íntegro.

**Acceptance Scenarios**:

1. **Given** el módulo Proveedores, **When** se registra un proveedor con todos los datos obligatorios, **Then** queda disponible como opción en selectores de compra e inventario.
2. **Given** un proveedor con historial de compras, **When** se intenta eliminar, **Then** el sistema lo impide y ofrece desactivarlo.
3. **Given** un proveedor de tipo "piezas no originales", **When** se consulta desde el módulo de Piezas (003), **Then** aparece filtrable por ese tipo.

---

### User Story 2 - Órdenes de compra y recepción (Priority: P1)

El personal registra órdenes de compra a un proveedor (ítems, cantidades, costos unitarios, fecha pactada) y luego su recepción (total o parcial) con la fecha real, construyendo el historial de compras.

**Why this priority**: Es el hecho de negocio que alimenta el ingreso a stock (003), el costo de adquisición (§4.4/§4.5) y las cuentas por pagar (010). [Esp. §4.2]

**Independent Test**: Crear una orden de compra, registrar su recepción y verificar el historial y las fechas.

**Acceptance Scenarios**:

1. **Given** una orden de compra emitida, **When** se registra su recepción completa, **Then** la orden pasa a "recibida" con fecha real y aparece en el historial de compras del proveedor.
2. **Given** una orden de compra, **When** se recibe solo parte de las unidades, **Then** la orden queda "parcialmente recibida" y admite recepciones posteriores.
3. **Given** una orden recibida, **When** se consulta desde 003, **Then** sus líneas están disponibles para dar de alta las unidades/piezas en inventario.

---

### User Story 3 - Calificación de confiabilidad (Priority: P2)

El personal califica al proveedor en escala 1–5 según criterios (cumplimiento de plazos, calidad, soporte postventa) y consulta el historial de calificaciones.

**Why this priority**: Requisito explícito de §4.2 y base para decisiones de compra.

**Independent Test**: Calificar un proveedor y ver reflejada la nota y su histórico.

**Acceptance Scenarios**:

1. **Given** un proveedor, **When** se registra una calificación por criterio, **Then** se calcula y guarda la nota agregada con fecha y autor.
2. **Given** varias calificaciones en el tiempo, **When** se consulta el proveedor, **Then** se ve la evolución.

---

### User Story 4 - Cumplimiento de plazos automático (Priority: P2)

El sistema calcula, por cada orden recibida, el desfase entre la fecha de entrega real y la pactada, y mantiene un indicador agregado de cumplimiento de plazos por proveedor que retroalimenta la calificación.

**Why this priority**: Ampliación pedida en §4.2 ("retroalimentar la calificación de forma automática en lugar de manual").

**Independent Test**: Recibir dos órdenes (una a tiempo, otra tarde) y verificar el indicador.

**Acceptance Scenarios**:

1. **Given** una orden con entrega pactada y real, **When** se registra la recepción, **Then** el desfase (días) se calcula y se guarda.
2. **Given** varias órdenes recibidas, **When** se consulta el proveedor, **Then** el indicador de cumplimiento refleja el promedio real vs. pactado.
3. **Given** un indicador de cumplimiento bajo, **When** se consulta la calificación, **Then** el componente "cumplimiento de plazos" se ajusta automáticamente sin impedir el ajuste manual de los demás criterios.

---

### User Story 5 - Compras programadas y especiales (Priority: P2)

El personal define órdenes de compra programadas con frecuencia (semanal, mensual, trimestral) que el sistema genera automáticamente en cada ciclo, y además registra órdenes especiales/puntuales para casos fuera de programa.

**Why this priority**: El abastecimiento de insumos recurrentes (lubricantes, consumibles) se planifica; las compras de relojes o piezas puntuales son excepcionales.

**Independent Test**: Configurar una compra mensual y verificar que se genera la orden al llegar el ciclo; crear una orden especial y verificar que queda marcada como puntual.

**Acceptance Scenarios**:

1. **Given** una compra programada mensual a un proveedor de lubricantes, **When** llega la fecha del ciclo, **Then** el sistema genera la orden de compra correspondiente en estado borrador para su revisión.
2. **Given** una necesidad puntual, **When** se crea una orden especial, **Then** queda registrada como "puntual" y no genera recurrencia.
3. **Given** una compra programada, **When** se pausa o se cancela, **Then** deja de generar órdenes en los ciclos siguientes.

---

### User Story 6 - Corrección de datos y baja de proveedor (Priority: P2)

El personal con rol elevado corrige datos de una compra ya recibida (p. ej. una cantidad o un costo mal ingresado) y edita un subconjunto de datos del proveedor; un proveedor con historial se inactiva, no se borra.

**Why this priority**: Los errores de digitación en compras y proveedores son frecuentes y deben poder corregirse de forma controlada y auditada.

**Independent Test**: Corregir el costo de una línea de una compra recibida con un rol autorizado y verificar la auditoría; intentar la misma corrección con un rol no autorizado y verificar el rechazo.

**Acceptance Scenarios**:

1. **Given** una compra ya recibida con un costo unitario mal digitado, **When** un Gerente de Sucursal o Gerencia General lo corrige, **Then** el cambio se aplica y queda auditado (valor previo/nuevo, actor, motivo).
2. **Given** el mismo caso, **When** lo intenta un rol no autorizado, **Then** recibe 403.
3. **Given** un proveedor con historial, **When** se editan sus datos, **Then** solo son editables contacto, teléfono, email, condiciones de pago y calificación; razón social y RUC/NIT requieren rol elevado.
4. **Given** un proveedor con historial, **When** se intenta eliminar, **Then** el sistema solo permite inactivarlo.

---

### User Story 7 - Reponer stock desde una alerta (Priority: P3)

Cuando Inventario (003) emite una alerta de reposición, el usuario abre una orden de compra ya prellenada con el proveedor habitual, el modelo/pieza y la cantidad sugerida.

**Why this priority**: Const. Ppio XI: un botón que "sugiere" debe abrir el flujo concreto. 002 provee el flujo; 003 lo invoca.

**Independent Test**: Invocar la creación de orden de compra con parámetros de prellenado y verificar que la orden llega con esos datos puestos.

**Acceptance Scenarios**:

1. **Given** parámetros de prellenado (proveedor, ítem, cantidad), **When** se abre la creación de orden de compra, **Then** el formulario aparece con esos valores y editable.
2. **Given** un ítem sin proveedor habitual, **When** se abre el flujo, **Then** se solicita elegir proveedor de la lista existente (nunca texto libre).

### Edge Cases

- ¿Qué pasa si se recibe más cantidad que la pedida en una línea?
- ¿Qué pasa con una orden de compra cancelada tras una recepción parcial?
- ¿Qué pasa si cambian las condiciones de pago del proveedor con órdenes abiertas?
- ¿Qué pasa si dos usuarios registran recepciones de la misma orden a la vez?
- ¿Qué ocurre con el indicador de cumplimiento si nunca se registró fecha pactada?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir CRUD de la ficha de proveedor con nombre/razón social, contacto, teléfono y email. [Esp. §4.2]
- **FR-002**: El proveedor DEBE poder marcarse con uno o varios tipos: relojes, piezas originales, piezas no originales, lubricantes, herramientas. [Esp. §4.2]
- **FR-003**: El sistema DEBE registrar las condiciones de pago y los plazos de entrega pactados por proveedor. [Esp. §4.2]
- **FR-004**: El sistema DEBE registrar RUC/NIT y el estado de certificación de distribución autorizada como campos estructurados, y permitir adjuntar los PDF de certificados y documentos legales del proveedor en el bucket `documentos`, servidos vía endpoint autenticado. [Esp. §4.2; Const. Ppio III]
- **FR-005**: El sistema DEBE permitir registrar órdenes de compra con líneas (ítem, cantidad, costo unitario), fecha de emisión y fecha de entrega pactada. [Esp. §4.2 "Historial de compras"]
- **FR-006**: El sistema DEBE permitir registrar la recepción de una orden de compra, total o parcial, con la fecha real de recepción. [Esp. §4.2; alimenta §4.4 "Fecha de ingreso a stock" en 003]
- **FR-007**: El sistema DEBE construir y mostrar el historial de compras por proveedor. [Esp. §4.2]
- **FR-008**: El sistema DEBE permitir calificar la confiabilidad en escala 1–5 por criterios (cumplimiento de plazos, calidad, soporte postventa) y conservar el histórico. [Esp. §4.2]
- **FR-009**: El sistema DEBE calcular, por orden recibida, el desfase entre entrega real y pactada, y un indicador agregado de cumplimiento de plazos por proveedor. [Esp. §4.2 (ampliación sugerida)]
- **FR-010**: El indicador de cumplimiento DEBE retroalimentar automáticamente el criterio "cumplimiento de plazos" de la calificación, sin impedir el ajuste manual de los demás criterios. [Esp. §4.2 (ampliación sugerida)]
- **FR-011**: El sistema DEBE exponer una creación de orden de compra que acepte parámetros de prellenado (proveedor, ítem, cantidad sugerida) para ser invocada desde la alerta de reposición de 003. [Esp. §4.4 (regla de reposición); Const. Ppio XI]
- **FR-011a**: El sistema DEBE permitir definir compras programadas con frecuencia (semanal, mensual, trimestral) que generan automáticamente una orden en estado borrador en cada ciclo, y marcar las órdenes fuera de programa como "puntuales/especiales". Una compra programada se puede pausar o cancelar. [Necesidad del negocio; Esp. §4.2]
- **FR-011b**: El sistema DEBE permitir corregir datos de una compra ya recibida (cantidad, costo, referencia) SOLO con rol elevado (Gerente de Sucursal o Gerencia General), con motivo y auditoría del valor previo/nuevo. La corrección del número de serie de una unidad ya ingresada se hace en 003 con las mismas restricciones. [Necesidad del negocio; Esp. §6]
- **FR-011c**: Un proveedor con historial solo admite edición de un subconjunto de campos (contacto, teléfono, email, condiciones de pago, calificación); razón social y RUC/NIT requieren rol elevado. [Necesidad del negocio; Esp. §6]
- **FR-011d**: Al recibir lubricantes o consumibles marcados como perecederos en 003, la recepción DEBE registrar el lote y la fecha de caducidad por cada línea recibida. [Necesidad del negocio; Esp. §4.5, §4.6]
- **FR-012**: La orden de compra DEBE registrar el importe y las condiciones a pagar al proveedor, que 010 consume para la cuenta por pagar. [Esp. §4.10 "Cuentas por pagar a proveedores"]
- **FR-013**: El sistema DEBE registrar la retención en la fuente aplicable por orden/pago cuando corresponda (campos listos, sin cálculo ni declaración fiscal). [Esp. §7 "Retenciones en la fuente a proveedores"]
- **FR-014**: El proveedor con historial NO se elimina físicamente; solo se desactiva. [Esp. §6 "Trazabilidad"]
- **FR-015**: Los listados de proveedores y de órdenes de compra DEBEN tener filtros reactivos (sin botón "Buscar"), búsqueda multi-criterio (proveedor por nombre, RUC/NIT, email o teléfono; líneas por nombre, código/número o referencia del ítem) y paginación; los inputs se resuelven por selección/filtrado, no por texto libre salvo campos descriptivos. [Const. Ppio XI]
- **FR-016**: El módulo DEBE declarar sus permisos en el esquema RBAC de dos niveles bajo el módulo "Proveedores". [Const. Ppio IV; Esp. §3.1]
- **FR-017**: El sistema DEBE auditar los cambios de calificación y de condiciones de pago. [Esp. §6 "Auditoría"]
- **FR-018**: El panel de trabajo DEBE usar el set estandarizado de acciones y ofrecer exportación CSV/Excel/PDF del historial de compras. [Const. Ppio XI]

### Key Entities *(include if feature involves data)*

- **Proveedor**: nombre/razón social, contacto, tipos, condiciones de pago, plazos, RUC/NIT, certificación, estado. Referenciado por 003, 010, 011.
- **OrdenCompra**: proveedor, sucursal destino, fecha de emisión, fecha pactada, estado (borrador / emitida / parcial / recibida / cancelada), tipo (puntual / generada por programa), importe a pagar, retención aplicable.
- **CompraProgramada**: proveedor, ítems, frecuencia (semanal/mensual/trimestral), estado (activa/pausada/cancelada), próxima generación.
- **LíneaOrdenCompra**: ítem (referencia de reloj o código de pieza — resuelto en 003), cantidad, costo unitario.
- **RecepciónCompra**: orden, fecha real, cantidades recibidas por línea, lote y fecha de caducidad (si el ítem es perecedero), responsable.
- **CalificaciónProveedor**: proveedor, notas por criterio, nota agregada, fecha, autor, componente automático de cumplimiento de plazos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Registrar un proveedor con todos los campos obligatorios toma menos de 2 minutos.
- **SC-002**: El historial de compras de un proveedor refleja el 100% de las órdenes y recepciones registradas.
- **SC-003**: Tras registrar una recepción, el desfase real vs. pactado y el indicador de cumplimiento se actualizan sin acción manual.
- **SC-004**: Una orden de compra abierta desde una alerta de reposición de 003 llega con proveedor, ítem y cantidad ya puestos y editables.
- **SC-005**: Ningún proveedor con historial puede borrarse físicamente.
- **SC-006**: El 100% de los cambios de calificación y de condiciones de pago quedan auditados con actor y timestamp.

## Assumptions

- 001 está implementada (RBAC, `sucursal`, catálogos, parámetros de configuración).
- El ingreso efectivo de unidades de reloj y de piezas al inventario lo realiza 003, vinculando la recepción de compra con la ficha correspondiente; 002 solo registra la compra y su recepción.
- La cuenta por pagar como subledger y su aging se construyen en 010; 002 aporta los datos de la obligación (importe, condiciones, retención).
- Los PDF de certificados y documentos legales del proveedor se adjuntan en el bucket `documentos` (prefijo de proveedor), servidos vía endpoint autenticado.
- El cálculo fiscal de retenciones y su declaración ante el SRI están fuera de alcance (§7 pendiente; Const. "Stack").
- La lista de referencias de reloj y códigos de pieza que pueden figurar en una línea de compra existe a partir de 003; hasta entonces las líneas se validan contra texto controlado.
