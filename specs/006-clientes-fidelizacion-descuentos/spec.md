# Feature Specification: Clientes, Fidelización y Descuentos

**Feature Branch**: `006-clientes-fidelizacion-descuentos`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "CRM básico de clientes (§4.8), programa de fidelización con niveles configurables y recálculo automático (§4.8.1), descuentos generales y cupones (§4.8.2), y el margen mínimo protegido: un servicio compartido que valida en el backend que ningún descuento reduzca el precio final por debajo del margen mínimo configurable, bloqueando o exigiendo autorización de Gerencia General."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ficha de cliente (Priority: P1)

El personal registra y mantiene clientes (persona natural o jurídica) con identificación, contacto, dirección, fecha de nacimiento opcional, preferencias y notas; la ficha muestra el historial de compras y servicios, el nivel de fidelización actual y los cupones activos.

**Why this priority**: El cliente es prerrequisito de citas (007), servicio técnico (008) y ventas (009), y base del reporte de "mejores clientes" (§4.8).

**Independent Test**: Registrar un cliente completo y recuperar su ficha con todas las secciones.

**Acceptance Scenarios**:

1. **Given** el módulo Clientes, **When** se registra un cliente con identificación única, **Then** queda disponible en los selectores de citas, servicio y ventas.
2. **Given** un cliente sin transacciones, **When** se consulta su ficha, **Then** aparece en el nivel base de fidelización.
3. **Given** una identificación (cédula/RUC) ya registrada, **When** se intenta crear otro cliente con la misma, **Then** el sistema lo rechaza.

---

### User Story 2 - Configurar los niveles de fidelización (Priority: P1)

Gerencia General define los niveles (nombre, criterio: monto acumulado / frecuencia / combinación), sus umbrales y sus beneficios.

**Why this priority**: §4.8.1 exige que nombres, umbrales y beneficios sean configurables, no fijos.

**Independent Test**: Configurar tres niveles con umbrales y verificar que un cliente se clasifica según su histórico.

**Acceptance Scenarios**:

1. **Given** el módulo de Configuración, **When** Gerencia General define el nivel "Plata" con umbral de monto acumulado anual, **Then** queda vigente con fecha de vigencia y auditado.
2. **Given** niveles configurados, **When** se consulta el catálogo, **Then** cada nivel muestra su criterio, umbral y beneficios.

---

### User Story 3 - Recálculo automático del nivel (Priority: P1)

Al registrarse una nueva compra o servicio del cliente, el sistema recalcula su nivel y, si cambia, guarda el cambio en el historial de niveles.

**Why this priority**: §4.8.1: "el nivel del cliente se recalcula automáticamente… el sistema conserva el historial de cambios de nivel". Lógica crítica con cobertura de pruebas obligatoria (Const. Ppio IX).

**Independent Test**: Registrar una compra que supera un umbral y verificar el ascenso de nivel y el registro del cambio.

**Acceptance Scenarios**:

1. **Given** un cliente en "Bronce" cerca del umbral de "Plata", **When** 009 registra una venta que lo supera, **Then** el cliente pasa a "Plata" y se registra el cambio con el hecho que lo disparó.
2. **Given** un cliente cuyo nivel no cambia tras una transacción, **When** se recalcula, **Then** no se crea un registro de cambio redundante.

---

### User Story 4 - Margen mínimo protegido (Priority: P1)

Gerencia General configura el margen mínimo (% sobre el costo o monto, global / por marca / por producto). Al aplicar un descuento o cupón, un servicio compartido calcula el margen resultante y, si cae por debajo del mínimo, bloquea la operación o exige autorización expresa de Gerencia General.

**Why this priority**: Regla de negocio explícita de §4.8.2; lógica crítica con cobertura de pruebas obligatoria y validación siempre en backend (Const. Ppio V, Ppio IX).

**Independent Test**: Aplicar un descuento que viole el mínimo y verificar el bloqueo; repetir con autorización registrada y verificar que se permite y se audita.

**Acceptance Scenarios**:

1. **Given** un margen mínimo de 15% sobre el costo, **When** se aplica un descuento que dejaría el margen en 10%, **Then** el sistema bloquea la confirmación de la venta/OT.
2. **Given** el mismo caso, **When** Gerencia General autoriza expresamente, **Then** la operación se permite y queda registrado quién autorizó, cuándo y sobre qué operación.
3. **Given** cualquier intento de calcular el margen mínimo desde el frontend, **When** se confirma la operación, **Then** el backend recalcula y su resultado prevalece.

---

### User Story 5 - Descuentos generales y cupones (Priority: P1)

Gerencia General define descuentos generales (segmento, alcance, vigencia o evento, límite de uso) y emite cupones (código, cliente, vigencia, condiciones, estado).

**Why this priority**: §4.8.2 contempla ambos mecanismos, no excluyentes.

**Independent Test**: Crear un descuento por nivel "Oro" y un cupón de cumpleaños y verificar su aplicabilidad.

**Acceptance Scenarios**:

1. **Given** un descuento general para el segmento "nivel Oro" vigente este mes, **When** un cliente Oro compra, **Then** el descuento está disponible para esa venta.
2. **Given** un cupón de uso único, **When** se aplica una vez, **Then** su estado pasa a "usado" y no puede volver a aplicarse.
3. **Given** un cupón vencido, **When** se intenta aplicar, **Then** el sistema lo rechaza.

---

### User Story 6 - Reportes de clientes (Priority: P2)

El personal consulta el reporte de clientes agrupados por nivel de fidelización, el reporte operativo de "mejores clientes" por volumen de compra + servicios, y el historial de un cliente puntual.

**Why this priority**: §4.8.1 pide el reporte por nivel para campañas dirigidas; §4.11.1 pide el historial del cliente.

**Independent Test**: Generar cada reporte y verificar que cuadra con los datos de los clientes.

**Acceptance Scenarios**:

1. **Given** clientes en varios niveles, **When** se genera el reporte por nivel, **Then** la distribución cuadra con el nivel vigente de cada cliente y se puede exportar.
2. **Given** un cliente con compras y servicios, **When** se consulta su historial, **Then** se ven todas sus transacciones y citas.

### Edge Cases

- ¿Qué pasa al cambiar los umbrales de nivel con muchos clientes ya clasificados? (¿reclasificación retroactiva o solo a la siguiente transacción?)
- ¿Se puede acumular un descuento general y un cupón en la misma venta/OT? ¿En qué orden?
- ¿Qué pasa cuando el margen resultante queda exactamente en el mínimo?
- ¿Qué pasa si dos cajas aplican el mismo cupón de uso único a la vez?
- ¿Qué pasa con un cliente persona jurídica sin fecha de nacimiento para el cupón de cumpleaños?
- ¿Qué pasa si se elimina un nivel de fidelización que tiene clientes asignados?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir CRUD de la ficha de cliente: nombre/razón social, cédula/RUC, teléfono, email, dirección, fecha de nacimiento (opcional), preferencias (marcas, complicaciones), notas del vendedor. Tras el alta, la cédula/RUC solo se corrige con rol elevado y auditoría; el resto de datos los edita el personal, auditado. [Esp. §4.8, §6]
- **FR-001a**: El sistema DEBE asignar a cada cliente un número de afiliado interno único, autogenerado al alta, además de la cédula/RUC; ambos sirven para identificar y buscar al cliente. [Necesidad del negocio; Esp. §4.8]
- **FR-001b**: El alta de cliente DEBE incluir una casilla de consentimiento de la ley de protección de datos (LOPDP, Ecuador), registrando la aceptación con fecha y versión del texto de consentimiento. [Necesidad del negocio; Esp. §7 (marco legal)]
- **FR-002**: La ficha DEBE mostrar el historial de compras y el historial de servicios técnicos del cliente (poblados por 009 y 008). [Esp. §4.8]
- **FR-003**: La ficha DEBE mostrar el nivel de fidelización actual y los cupones/beneficios activos. [Esp. §4.8]
- **FR-004**: Gerencia General DEBE poder configurar los niveles de fidelización: nombre, criterio (monto acumulado / frecuencia / combinación), umbrales y beneficios, con vigencia y auditoría. [Esp. §4.8.1, §9.1, §9.4]
- **FR-005**: El sistema DEBE calcular el nivel del cliente automáticamente y recalcularlo al registrarse una nueva compra o servicio. [Esp. §4.8.1]
- **FR-006**: El sistema DEBE conservar el historial de cambios de nivel de cada cliente (nivel anterior, nuevo, fecha, hecho disparador). [Esp. §4.8.1]
- **FR-007**: Un cliente sin transacciones DEBE quedar en el nivel base definido en la configuración. [Esp. §4.8.1]
- **FR-008**: Gerencia General DEBE poder definir descuentos generales con tipo (% o monto fijo), alcance (producto/servicio, marca o toda la tienda), segmento (todos / nivel / cliente puntual), vigencia (fechas o evento) y límite de uso. [Esp. §4.8.2]
- **FR-009**: Gerencia General DEBE poder emitir cupones con código, cliente asignado, tipo y valor, alcance, vigencia o evento, límite de uso y estado (activo / usado / vencido). [Esp. §4.8.2]
- **FR-010**: Gerencia General DEBE poder configurar el margen mínimo protegido como % sobre el costo o monto mínimo, con ámbito global, por marca o por producto. [Esp. §4.8.2, §9.1]
- **FR-011**: El sistema DEBE proveer un servicio compartido que, dado un ítem y su costo, calcule el precio final descontado y el margen resultante tras aplicar un descuento o cupón. [Esp. §4.8.2]
- **FR-012**: Si el margen resultante cae por debajo del mínimo, el servicio DEBE bloquear la operación o marcarla "requiere autorización expresa de Gerencia General"; sin esa autorización la venta/OT no se confirma. [Esp. §4.8.2]
- **FR-013**: La autorización de Gerencia General para saltar el margen mínimo DEBE registrarse (quién, cuándo, sobre qué operación) y quedar auditada. [Esp. §4.8.2, §6, §9.4]
- **FR-014**: Todo descuento o cupón aplicado DEBE quedar registrado en la venta u orden de trabajo, de modo que el margen real se calcule sobre el precio final descontado. [Esp. §4.8.2]
- **FR-015**: Un descuento general y un cupón son MUTUAMENTE EXCLUYENTES en una misma venta u orden de trabajo: el sistema NO permite aplicar ambos a la misma operación (regla de negocio). [Esp. §4.8.2; decisión del negocio]
- **FR-016**: Un cupón de uso único NO puede aplicarse dos veces (control de concurrencia). [Esp. §4.8.2 "Límite de uso"]
- **FR-017**: El sistema DEBE ofrecer el reporte de clientes agrupados por nivel de fidelización, exportable. [Esp. §4.8.1, §4.11.2 — versión operativa]
- **FR-018**: El sistema DEBE ofrecer el reporte operativo "mejores clientes" por volumen de compra + servicios. [Esp. §4.8, §4.11.1 / §4.11.2 — versión operativa]
- **FR-019**: El sistema DEBE ofrecer el "historial de un cliente puntual" (compras, servicios, citas). [Esp. §4.11.1]
- **FR-020**: Un cliente con transacciones NO se elimina físicamente; se desactiva o anonimiza según necesidad legal. [Esp. §6 "Trazabilidad"]
- **FR-021**: El módulo DEBE declarar sus permisos bajo "Clientes/Fidelización" en el esquema RBAC de dos niveles. [Esp. §3.1; Const. Ppio IV]
- **FR-022**: El cálculo del margen mínimo protegido y el cálculo del nivel de fidelización DEBEN validarse siempre en el backend, nunca en el frontend. [Const. Ppio V]
- **FR-023**: Los listados DEBEN tener filtros reactivos, búsqueda multi-criterio de clientes (nombre, cédula/RUC, email, teléfono, número de afiliado) y paginación; el panel de trabajo usa el set estandarizado de acciones y ofrece exportación CSV/Excel/PDF de todos los reportes. [Const. Ppio XI]
- **FR-024**: Los selectores de segmento, nivel, marca y cliente se pueblan desde datos existentes; nunca campos de texto libre. [Const. Ppio XI]
- **FR-025**: Cambiar los umbrales, criterios o beneficios de un nivel DEBE recalcular en cascada el nivel vigente de todos los clientes (proceso diferido); el historial de niveles previo se conserva y el cambio queda auditado. [Esp. §4.8.1, §9.4; Const. "Parámetros configurables — recálculo en cascada"; decisión del negocio]
- **FR-026**: Cada transacción del cliente (compra 009 / servicio 008) DEBE conservar la **sucursal** en la que se realizó; el historial del cliente la muestra. 006 define el campo en el contrato de transacciones; 008/009 lo pueblan. [Necesidad del negocio; Esp. §4.9]
- **FR-027**: La dirección del cliente es **opcional** (no bloquea el alta). [Necesidad del negocio; Esp. §4.8]
- **FR-028** *(ampliación 2026-09-10, confirmada por el usuario)*: El sistema DEBE ofrecer un reporte operativo de **clientes en riesgo de abandono**: para cada cliente de nivel con valor (todo nivel **no base** — Plata/Oro), analiza su **patrón propio de compra** (cadencia mediana entre transacciones en una ventana) y lo marca en riesgo si su silencio actual (días desde la última transacción) supera `churn_factor_cadencia` × su cadencia **y** además supera un piso mínimo `churn_piso_dias`. Exige un historial mínimo `churn_min_transacciones` para tener patrón. Umbrales configurables por Gerencia General (§9). Severidad `atencion` / `critico`. [Esp. §4.8.2 "cupón de reactivación para clientes inactivos"; §4.11.1]
- **FR-029** *(ampliación)*: Desde el reporte de riesgo, el personal autorizado DEBE poder **emitir un cupón de reactivación** para el cliente (cupón puntual de uso único), sin salir de la pantalla (Const. Ppio XI "acciones que no llevan a nada"). El envío por correo lo hace 014. [Esp. §4.8.2]
- **FR-030** *(ampliación)*: El análisis de riesgo de abandono y sus umbrales DEBEN vivir en el backend (Const. Ppio V); el reporte es exportable CSV/Excel/PDF. [Const. Ppio V, Ppio XI]

### Key Entities *(include if feature involves data)*

- **Cliente**: identificación (cédula/RUC), número de afiliado interno único, tipo (natural/jurídica), contacto, dirección, fecha de nacimiento, preferencias, notas, consentimiento de protección de datos (fecha + versión), estado.
- **NivelFidelización**: nombre, criterio, umbral(es), beneficios, vigencia.
- **HistorialNivelCliente**: cliente, nivel anterior, nivel nuevo, fecha, hecho disparador.
- **Descuento (general)**: tipo, valor, alcance, segmento, vigencia/evento, límite de uso, estado.
- **Cupón**: código, cliente, tipo, valor, alcance, vigencia/evento, límite de uso, estado.
- **AplicaciónDescuento**: descuento/cupón, venta u OT, precio de lista, precio final, margen resultante, autorización asociada (si aplica).
- **ParámetroMargenMínimo**: ámbito (global/marca/producto), tipo (% costo / monto), valor, vigencia.
- **AutorizaciónMargenMínimo**: operación, autorizador (Gerencia General), fecha, margen resultante.
- **RiesgoAbandono** *(derivado, no persistido)*: cliente, cadencia mediana propia, días de silencio, ratio, severidad, última transacción — calculado en caliente sobre las transacciones del cliente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Registrar un cliente con datos completos toma menos de 2 minutos.
- **SC-002**: Tras una compra que supera un umbral, el nivel del cliente sube automáticamente y el cambio queda registrado con su causa.
- **SC-003**: El motor de nivel clasifica correctamente un set de clientes de prueba con históricos diversos (módulo con cobertura de pruebas obligatoria).
- **SC-004**: Un descuento que dejaría el margen bajo el mínimo se bloquea; con autorización de Gerencia General registrada, se permite y queda auditado (módulo con cobertura de pruebas obligatoria).
- **SC-005**: El 100% de los descuentos/cupones aplicados aparece en la venta/OT y el margen real se calcula sobre el precio final descontado.
- **SC-006**: El reporte de clientes por nivel cuadra con el nivel vigente de cada cliente.
- **SC-007**: Un cupón de uso único no puede consumirse dos veces (pruebas de concurrencia).

## Assumptions

- 001 está implementada (RBAC, parámetros de configuración, auditoría).
- La aplicación real de descuentos y el disparo del recálculo de nivel ocurren en 008 (servicio) y 009 (ventas); 006 entrega los motores, la configuración y el contrato que esas features consumen, y se validan con datos de prueba.
- Los reportes analíticos "efectividad de fidelización y descuentos" y "mejores clientes" comparados entre periodos son 013.
- El envío de campañas de email a partir de niveles y cupones lo realiza 014; 006 solo expone los datos.
- El recálculo masivo de niveles al cambiar umbrales se ejecuta como proceso diferido y reclasifica a todos los clientes según su histórico; el historial de niveles previo se conserva (decisión del negocio: recálculo en cascada).
- Descuento general y cupón nunca se acumulan en la misma operación (regla de negocio).
- La facturación electrónica y los datos fiscales del cliente para el SRI están fuera de alcance (§7 pendiente).
