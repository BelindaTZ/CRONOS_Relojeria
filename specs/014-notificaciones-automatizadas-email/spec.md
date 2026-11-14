# Feature Specification: Notificaciones Automatizadas por Email

**Feature Branch**: `014-notificaciones-automatizadas-email`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Envíos automatizados por email vía SendGrid (o equivalente): actualizaciones de estado de la orden de trabajo/servicio técnico (008), cupones y beneficios del programa de fidelización (006), y recordatorios de citas ya confirmadas (007). Plantillas configurables, seguimiento del estado de cada envío, cola con reintentos, opt-out por cliente, y desacople total del camino transaccional. Sin procesamiento de correo entrante."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aviso de cambio de estado de la orden de trabajo (Priority: P1)

Cuando una orden de trabajo cambia de estado en 008 (p. ej. "listo", "entregado"), el cliente recibe automáticamente un email con el nuevo estado.

**Why this priority**: Es uno de los tres envíos automatizados que la constitución exige (Const. "Stack"); mejora la experiencia postventa (§4.7).

**Independent Test**: Cambiar el estado de una OT y verificar el email generado con el estado correcto.

**Acceptance Scenarios**:

1. **Given** una OT con cliente que tiene email, **When** pasa a "listo", **Then** se genera un email con el nuevo estado y queda registrado como enviado.
2. **Given** una OT cuyo cliente no tiene email, **When** cambia de estado, **Then** el disparo se marca "sin destinatario" y es visible para el personal, sin reintentos en bucle.
3. **Given** dos cambios de estado seguidos, **When** ocurren, **Then** no se envían emails duplicados por el mismo cambio.

---

### User Story 2 - Cupones y beneficios de fidelización (Priority: P1)

Cuando se emite un cupón a un cliente o el cliente sube de nivel con nuevos beneficios (006), recibe un email con el beneficio y, si aplica, el código.

**Why this priority**: Envío automatizado exigido por la constitución (Const. "Stack"); sustenta el programa de fidelización (§4.8.1, §4.8.2).

**Independent Test**: Emitir un cupón y verificar el email con su código y vigencia.

**Acceptance Scenarios**:

1. **Given** un cliente activo, **When** se le emite un cupón de cumpleaños, **Then** recibe un email con el código y la vigencia.
2. **Given** un cliente que asciende a "Oro", **When** se registra el cambio de nivel, **Then** recibe un email con los beneficios del nuevo nivel.

---

### User Story 3 - Recordatorio de cita confirmada (Priority: P1)

El cliente recibe un recordatorio por email de sus citas ya confirmadas, con una antelación configurable.

**Why this priority**: Tercer envío automatizado exigido por la constitución (Const. "Stack", §4.1).

**Independent Test**: Confirmar una cita y verificar que se programa y envía el recordatorio con la antelación configurada.

**Acceptance Scenarios**:

1. **Given** una cita confirmada para dentro de 2 días y antelación de 24 h, **When** se cumple el plazo, **Then** el cliente recibe el recordatorio.
2. **Given** una cita confirmada con recordatorio programado, **When** la cita se cancela antes, **Then** el recordatorio no se envía.

---

### User Story 4 - Seguimiento y reintento de envíos (Priority: P2)

El personal autorizado consulta el estado de cada envío (encolado, enviado, entregado, rebotado, fallido) y reintenta los fallidos.

**Why this priority**: Sin visibilidad de entregas, los avisos automatizados no son confiables (§6).

**Independent Test**: Provocar un rebote y verificar el estado y el reintento manual.

**Acceptance Scenarios**:

1. **Given** un email rebotado, **When** el personal abre el panel de envíos, **Then** ve el estado "rebotado" y puede reintentar.
2. **Given** el proveedor de email caído, **When** ocurren disparos, **Then** se encolan y se envían al recuperarse el servicio, sin pérdidas.

---

### User Story 5 - Opt-out y plantillas (Priority: P2)

Gerencia General edita las plantillas por tipo de email (asunto, cuerpo, variables) con la identidad visual; un cliente puede quedar excluido de un tipo de comunicación.

**Why this priority**: Control del contenido y respeto a la preferencia del cliente.

**Independent Test**: Marcar opt-out de "fidelización" para un cliente y verificar que no recibe ese tipo pero sí los de OT.

**Acceptance Scenarios**:

1. **Given** una plantilla de recordatorio de cita, **When** Gerencia General la edita, **Then** los envíos siguientes usan el nuevo contenido.
2. **Given** un cliente con opt-out de fidelización, **When** se le emite un cupón, **Then** no se le envía email pero el cupón se crea igual.

### Edge Cases

- ¿Qué pasa con un email con formato inválido?
- ¿Qué pasa si el proveedor de email está caído durante horas?
- ¿Qué pasa si una OT rebota entre estados varias veces en minutos?
- ¿Qué pasa con la zona horaria al programar un recordatorio?
- ¿Qué pasa si el envío de email falla mientras se confirma una venta o se cierra una OT?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE integrarse con SendGrid (o equivalente) para email transaccional, con credenciales vía `.env`. [Const. "Stack"; Const. Ppio IX]
- **FR-002**: El sistema DEBE enviar un email automático al cliente cuando cambia el estado de su orden de trabajo/servicio técnico (008). [Const. "Stack"; Esp. §4.7]
- **FR-003**: El sistema DEBE enviar un email automático cuando se emite un cupón o cuando el cliente cambia de nivel de fidelización con nuevos beneficios (006). [Const. "Stack"; Esp. §4.8.1, §4.8.2]
- **FR-004**: El sistema DEBE enviar un recordatorio por email de las citas ya confirmadas (007), con antelación configurable. [Const. "Stack"; Esp. §4.1]
- **FR-004a**: El sistema DEBE gestionar y renderizar las plantillas de los demás correos del sistema que otras features disparan a través de la capacidad compartida de 001: aviso de inactivación de sucursal a su personal (001), datos del técnico asignado al cliente (008), contraseña temporal (001). Todas con la identidad visual del Principio XI. [Necesidad del negocio; Const. Ppio XI]
- **FR-005**: El sistema NO DEBE procesar correo entrante; la solicitud de citas por Gmail se gestiona manualmente. [Esp. §4.1; Const. "Stack"]
- **FR-006**: Cada tipo de email DEBE usar una plantilla configurable (asunto, cuerpo con variables) con la identidad visual de la tienda. [Const. Ppio XI, Ppio XII]
- **FR-007**: El sistema DEBE registrar el estado de cada envío: encolado, enviado, entregado, rebotado, fallido. [Esp. §6 "Auditoría"]
- **FR-008**: Si el proveedor de email no está disponible, los envíos DEBEN encolarse y reintentarse; ningún disparo se pierde silenciosamente. [Const. Ppio IX; Esp. §6]
- **FR-009**: Un envío fallido o rebotado DEBE poder reintentarse manualmente desde el panel. [Const. Ppio XI "Acciones que no llevan a nada"]
- **FR-010**: Si una cita confirmada se cancela o reprograma antes de que salga su recordatorio, el recordatorio NO se envía o se ajusta. [Esp. §4.1 — regla de integridad derivada]
- **FR-011**: El cliente DEBE poder quedar excluido (opt-out) por tipo de comunicación, y el sistema respeta la exclusión. [Const. Ppio IX; Esp. §6 (protección de datos)]
- **FR-012**: El sistema DEBE deduplicar los envíos por el mismo disparo. [Esp. §6 — regla de integridad derivada]
- **FR-013**: Un cliente sin email registrado NO genera envíos fallidos en bucle; el disparo se marca "sin destinatario" y es visible para el personal. [Esp. §4.8]
- **FR-014**: El sistema DEBE ofrecer un reporte operativo de envíos por tipo y estado, con filtros reactivos y paginación. [Esp. §4.11.1; Const. Ppio XI]
- **FR-015**: Cada envío DEBE auditarse (destinatario, tipo, disparo de origen, timestamp, estado). [Esp. §6]
- **FR-016**: El módulo DEBE declarar sus permisos en el esquema RBAC de dos niveles; las plantillas solo las edita Gerencia General o quien delegue. [Esp. §3.1, §9.4; Const. Ppio IV]
- **FR-017**: Los disparos NO deben acoplarse al camino crítico: confirmar una venta, cerrar una OT o confirmar una cita NO puede fallar porque el email falle. [Const. Ppio IX]
- **FR-018**: Los recordatorios de mantenimiento preventivo quedan FUERA de alcance (propuesta abierta §8). [Esp. §8]

### Key Entities *(include if feature involves data)*

- **PlantillaEmail**: tipo (estado de OT / cupón / cambio de nivel / recordatorio de cita), asunto, cuerpo, variables, estado.
- **Envío**: cliente, email destino, tipo, disparo de origen (OT, cupón, nivel, cita), estado, intentos, timestamps.
- **PreferenciaComunicaciónCliente**: cliente, tipo de comunicación, opt-in/opt-out.
- **ColaEnvío**: elementos pendientes de envío o reintento, con próxima ejecución.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un cambio de estado de OT genera el email al cliente en menos de 1 minuto, con el estado correcto.
- **SC-002**: La emisión de un cupón dispara su email con el código y la vigencia.
- **SC-003**: Las citas confirmadas reciben recordatorio con la antelación configurada; las canceladas no.
- **SC-004**: Con el proveedor de email caído, los disparos se encolan y se envían al recuperarse, sin pérdidas.
- **SC-005**: Confirmar una venta, cerrar una OT o confirmar una cita nunca falla por un fallo de email.
- **SC-006**: Un cliente con opt-out de un tipo no recibe ese tipo de email.
- **SC-007**: No se envían emails duplicados por el mismo disparo.
- **SC-008**: El reporte de envíos cuadra con los estados reales de entrega.

## Assumptions

- 006, 007 y 008 están implementadas (fuentes de los disparos); la capacidad compartida de envío + render de plantillas ya existe desde 001, y 014 construye sobre ella el módulo completo (disparadores automáticos, panel de entregas, cola/reintentos, opt-out, gestión de todas las plantillas).
- El proveedor es SendGrid o equivalente; la cuenta y la API key las provee el negocio vía `.env`.
- El diseño de plantillas usa la identidad visual del Principio XI mediante la skill del Principio XII; todas las plantillas del sistema (incluidas las que disparan 001 y 008) se administran aquí.
- No hay procesamiento de correo entrante ni lectura de Gmail (§4.1, gestión manual).
- Los recordatorios de mantenimiento preventivo y las campañas masivas de marketing quedan fuera de alcance (§8).
- El envío es asíncrono y desacoplado del camino transaccional (cola + worker).
- La antelación de los recordatorios y la periodicidad de reintento son parámetros configurables (mecanismo de 001).
