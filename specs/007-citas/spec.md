# Feature Specification: Gestión de Citas

**Feature Branch**: `007-citas`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Registro manual de citas por el personal (§4.1), canales de origen correo electrónico y presencial, datos por cita (cliente, fecha preferida/confirmada, motivo, estado, sucursal, canal, observaciones), estados pendiente/confirmada/cancelada/atendida, agenda del día y de la semana (§4.11.1), y vínculo de la cita atendida a la venta o la orden de trabajo generada para trazar el embudo cita → transacción."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar una cita (Priority: P1)

El vendedor registra una cita a partir de una solicitud recibida por correo electrónico o presencial, vinculándola a la ficha de cliente, con fecha y hora preferida, motivo, sucursal, canal de origen y observaciones.

**Why this priority**: Es la entrada del embudo de atención; sin cita registrada no hay trazabilidad cita → transacción (§4.1).

**Independent Test**: Registrar una cita con todos sus datos y recuperarla en estado "pendiente".

**Acceptance Scenarios**:

1. **Given** una ficha de cliente existente, **When** el vendedor registra una cita con canal "correo electrónico", **Then** queda en estado "pendiente" con todos sus datos.
2. **Given** una solicitud de alguien sin ficha de cliente, **When** se intenta registrar la cita, **Then** el sistema exige crear primero la ficha de cliente.
3. **Given** el catálogo de canales de cita, **When** se registra una cita, **Then** el canal se elige de la lista configurable (001), no como texto libre.

---

### User Story 2 - Confirmar, cancelar o atender una cita (Priority: P1)

El personal cambia el estado de la cita: la confirma (fijando fecha y hora confirmada), la cancela (con motivo) o la marca como atendida.

**Why this priority**: El ciclo de vida de la cita es el núcleo operativo del módulo (§4.1).

**Independent Test**: Recorrer una cita por los estados pendiente → confirmada → atendida y verificar los datos en cada paso.

**Acceptance Scenarios**:

1. **Given** una cita pendiente, **When** se confirma, **Then** se registra la fecha y hora confirmada y el estado pasa a "confirmada".
2. **Given** una cita confirmada, **When** se cancela, **Then** se solicita el motivo en un modal del design-system y el estado pasa a "cancelada".
3. **Given** una cita ya atendida, **When** se intenta cancelar, **Then** el sistema lo impide.

---

### User Story 3 - Agenda del día y de la semana (Priority: P1)

El personal de mostrador consulta la agenda de citas del día y de la semana, filtrada por su sucursal.

**Why this priority**: Reporte operativo de uso diario (§4.11.1).

**Independent Test**: Abrir la agenda del día y comprobar que lista todas las citas de la sucursal para esa fecha ordenadas por hora.

**Acceptance Scenarios**:

1. **Given** varias citas para hoy en la sucursal A, **When** un usuario de A abre la agenda del día, **Then** ve todas ordenadas por hora.
2. **Given** citas en A y B, **When** un usuario de A abre la agenda, **Then** no ve las de B salvo permiso ampliado.

---

### User Story 4 - Vincular la cita atendida a su transacción (Priority: P2)

Al marcar una cita como "atendida", el personal la vincula a la venta (009) o a la orden de trabajo (008) generada; si aún no existe, la acción abre el flujo de creación con el cliente y el contexto ya cargados.

**Why this priority**: §4.1 exige la trazabilidad completa del embudo cita → transacción; Const. Ppio XI prohíbe acciones sin efecto.

**Independent Test**: Atender una cita sin venta/OT previa y verificar que se abre el flujo de creación con el cliente cargado; luego que la cita queda vinculada.

**Acceptance Scenarios**:

1. **Given** una cita de motivo "servicio técnico" sin OT, **When** se marca como atendida, **Then** se abre la creación de orden de trabajo (008) con el cliente ya cargado.
2. **Given** una venta ya creada para ese cliente ese día, **When** se atiende la cita, **Then** el personal puede vincularla a esa venta existente.
3. **Given** una cita atendida y vinculada, **When** se consulta, **Then** muestra la referencia a su venta u OT.

### Edge Cases

- ¿Qué pasa con dos citas confirmadas solapadas en la misma sucursal y franja horaria?
- ¿Qué pasa si se registra una cita con fecha en el pasado?
- ¿Qué pasa si el canal de origen se deshabilita en configuración después de registrar citas con ese canal?
- ¿Qué pasa si se cancela una cita que ya tiene una OT abierta vinculada?
- ¿Qué pasa si el cliente pide atención en una sucursal distinta a la del vendedor que registra?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE registrar una cita con cliente (ficha existente de 006), fecha y hora preferida, motivo (compra / servicio técnico / consulta), sucursal asignada, canal de origen y observaciones. [Esp. §4.1]
- **FR-002**: El estado de la cita DEBE ser uno de: pendiente, confirmada, cancelada, atendida. [Esp. §4.1]
- **FR-003**: Al confirmar una cita, el sistema DEBE registrar la fecha y hora confirmada. [Esp. §4.1]
- **FR-004**: El canal de origen DEBE tomarse del catálogo configurable de canales de cita (001); nunca como texto libre. [Esp. §4.1, §9.3; Const. Ppio XI]
- **FR-005**: La cita DEBE vincularse a un cliente existente; no se permite cita sin ficha de cliente. [Esp. §4.1]
- **FR-006**: Al marcar una cita como "atendida", el sistema DEBE permitir vincularla a la venta (009) o a la orden de trabajo (008) generada. [Esp. §4.1]
- **FR-007**: Si al atender la cita no existe aún la venta/OT, la acción DEBE abrir el flujo de creación correspondiente con el cliente y el contexto ya cargados. [Esp. §4.1; Const. Ppio XI "Acciones que no llevan a nada"]
- **FR-008**: El sistema DEBE ofrecer la agenda de citas del día y de la semana, filtrable por sucursal. [Esp. §4.11.1]
- **FR-009**: Los listados de citas DEBEN tener filtros reactivos (estado, canal, sucursal, cliente, rango de fechas) y paginación. [Const. Ppio XI]
- **FR-010**: El sistema DEBE mostrar una tasa de conversión operativa de citas atendidas a venta/servicio. [Esp. §4.11.2 — versión operativa; el analítico comparado es 013]
- **FR-011**: Toda confirmación (confirmar, cancelar, atender) y toda entrada puntual (motivo de cancelación) se resuelve con el modal del design-system, nunca con `window.confirm`/`prompt`. [Const. Ppio XI]
- **FR-012**: El panel de trabajo DEBE usar el set estandarizado de acciones, incluyendo "Confirmar" y "Cancelar". [Const. Ppio XI]
- **FR-013**: El módulo DEBE declarar sus permisos bajo "Citas"; por defecto Vendedor con Crear/Consultar/Editar y no Eliminar. [Esp. §3.1; Const. Ppio IV]
- **FR-014**: El scoping por sucursal (001) DEBE aplicarse a los listados y a la agenda. [Esp. §4.9, §3]
- **FR-015**: Cada cambio de estado de una cita DEBE auditarse con actor y timestamp. [Esp. §6]
- **FR-016**: El sistema DEBE exponer los datos de la cita confirmada (cliente, fecha, sucursal) para que 014 envíe recordatorios; el envío NO es responsabilidad de esta feature. [Esp. §4.1; Const. "Flujo de Trabajo" §014]
- **FR-017**: El sistema DEBE advertir (sin bloquear) si ya existe otra cita confirmada para la misma sucursal en una franja solapada. [Esp. §4.1 — gestión manual por el personal]
- **FR-018**: El sistema DEBE ofrecer exportación CSV/Excel/PDF de la agenda. [Const. Ppio XI]

### Key Entities *(include if feature involves data)*

- **Cita**: cliente, sucursal asignada, motivo, canal de origen, fecha/hora preferida, fecha/hora confirmada, estado, observaciones, vínculo opcional a venta (009) o a orden de trabajo (008).
- **CanalCita**: catálogo configurable, propiedad de 001.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Registrar una cita completa toma menos de 1 minuto.
- **SC-002**: La agenda del día muestra el 100% de las citas de la sucursal para esa fecha, ordenadas por hora.
- **SC-003**: Al atender una cita sin venta/OT previa, la acción abre el flujo de creación con el cliente ya cargado (0 mensajes sin efecto).
- **SC-004**: El 100% de las citas atendidas queda vinculada o vinculable a su venta u orden de trabajo.
- **SC-005**: El 100% de los cambios de estado queda auditado con actor y timestamp.
- **SC-006**: Un usuario de la sucursal A no ve por defecto las citas de la sucursal B.

## Assumptions

- 001 y 006 están implementadas (catálogo de canales de cita, clientes, helper de scoping).
- El vínculo efectivo cita → venta lo completa 009 y cita → orden de trabajo lo completa 008; 007 provee el campo de vínculo y la acción de creación con contexto.
- El sistema no lee correos de Gmail: el personal gestiona la solicitud entrante manualmente (§4.1) y registra la cita indicando el canal "correo electrónico".
- Los recordatorios automáticos por email de citas confirmadas los envía 014.
- El reporte analítico de tasa de conversión del embudo de atención es 013.
- No hay gestión de disponibilidad tipo "slots"; el personal coordina los horarios (no autoservicio).
