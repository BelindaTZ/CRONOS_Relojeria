# Feature Specification: Técnicos y Productividad

**Feature Branch**: `005-tecnicos-productividad`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Ficha de RRHH técnico (§4.3): especialidades, certificaciones, sucursales, vínculo a usuario, costo interno de mano de obra. Esquema de bono por productividad configurable (§5): indicadores objetivos, umbrales y fórmula definidos por Gerencia General; motor que calcula el bono acumulado por técnico y periodo y lo refleja como costo de mano de obra en los reportes de margen. Vista operativa de productividad por técnico."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ficha de técnico y costo interno (Priority: P1)

El personal autorizado registra técnicos con nombre, especialidades (Rolex, Omega, complicaciones…), certificaciones, sucursales de trabajo y vínculo a un usuario del sistema, junto con su costo interno de mano de obra (sueldo fijo + esquema de comisiones/bonos si aplica).

**Why this priority**: El costo de mano de obra es un componente del costo interno del servicio (§5); sin la ficha no puede asignarse ni costearse una orden de trabajo (008).

**Independent Test**: Registrar un técnico completo con su costo interno y recuperarlo íntegro; verificar que el costo no es visible para roles no administrativos.

**Acceptance Scenarios**:

1. **Given** el módulo Técnicos, **When** se registra un técnico con especialidades y sucursal, **Then** queda disponible para asignación de órdenes de trabajo en 008.
2. **Given** un técnico vinculado a un usuario, **When** ese usuario inicia sesión, **Then** su acceso refleja el nivel definido en 001.
3. **Given** un rol no administrativo, **When** consulta la ficha del técnico, **Then** no ve el costo interno de mano de obra.

---

### User Story 2 - Definir el esquema de bono por productividad (Priority: P1)

Gerencia General define reglas de bono evaluadas sobre indicadores objetivos (número de OT completadas, cumplimiento de tiempos estimados, margen generado, calidad) con umbrales y una fórmula (monto fijo por meta, porcentaje sobre el margen, o combinación), por periodo.

**Why this priority**: §5 exige que la fórmula y los umbrales sean configurables, no valores fijos; es lógica de negocio crítica con cobertura de pruebas obligatoria (Const. Ppio IX).

**Independent Test**: Configurar una regla de bono y validar el cálculo contra un set de órdenes de prueba.

**Acceptance Scenarios**:

1. **Given** el módulo de Configuración, **When** Gerencia General define un bono de "monto fijo si OT completadas ≥ 20 en el mes", **Then** la regla queda vigente con fecha de vigencia y auditada.
2. **Given** una regla que combina monto fijo + % sobre margen, **When** se guarda, **Then** el motor la evalúa aplicando ambos componentes.

---

### User Story 3 - Cálculo automático del bono acumulado (Priority: P2)

El sistema calcula automáticamente el bono acumulado por técnico y por periodo a partir de las órdenes de trabajo registradas (008), con el desglose por indicador.

**Why this priority**: §5 pide cálculo automático; el bono se refleja en el costo de mano de obra de los reportes de margen.

**Independent Test**: Con un conjunto de OT de prueba, comparar el bono calculado con el cálculo manual.

**Acceptance Scenarios**:

1. **Given** un técnico con 22 OT completadas y la regla de US2, **When** se cierra el periodo, **Then** el bono calculado corresponde a la regla y muestra el desglose.
2. **Given** un técnico sin OT en el periodo, **When** se calcula, **Then** el bono es 0 (nunca negativo).
3. **Given** un periodo ya cerrado, **When** se modifica la fórmula del bono, **Then** el bono de ese periodo no se recalcula automáticamente y el cambio queda auditado.

---

### User Story 4 - Costo de mano de obra para el costeo del servicio (Priority: P2)

El costo de mano de obra por técnico (sueldo prorrateado por orden + bono acumulado) se expone a 008 para el costo interno del servicio, sin exponerse nunca al cliente.

**Why this priority**: §5: "sin exponer el costo interno de mano de obra al cliente"; es la entrada del cálculo de margen del servicio.

**Independent Test**: Consultar por contrato el costo de mano de obra prorrateado de una orden y verificar que no aparece en ningún documento del cliente.

**Acceptance Scenarios**:

1. **Given** una orden de trabajo en 008, **When** solicita el costo de mano de obra del técnico asignado, **Then** recibe el sueldo prorrateado más la parte proporcional del bono.
2. **Given** el comprobante que ve el cliente, **When** se genera, **Then** no contiene el costo interno de mano de obra.

---

### User Story 5 - Vista operativa de productividad (Priority: P2)

El personal autorizado consulta la productividad por técnico: OT completadas, tiempo promedio de ejecución, margen generado y bono alcanzado en el periodo.

**Why this priority**: §4.3 y §4.11.2 lo piden; la versión operativa sirve al Técnico Jefe para supervisión diaria.

**Independent Test**: Consultar la productividad de un técnico y comprobar que coincide con sus OT.

**Acceptance Scenarios**:

1. **Given** un técnico con OT completadas en el periodo, **When** se consulta su productividad, **Then** se ven OT completadas, tiempo promedio, margen generado y bono.
2. **Given** el listado de productividad, **When** se exporta, **Then** ofrece CSV, Excel y PDF.

### Edge Cases

- ¿Qué pasa si se cambia la fórmula del bono a mitad de un periodo abierto?
- ¿Qué pasa con un técnico que trabaja en varias sucursales (atribución de OT y de costo)?
- ¿Qué pasa si hay un reproceso sobre el mismo reloj (indicador de calidad)?
- ¿Qué pasa con un técnico desactivado que tiene bono pendiente de un periodo?
- ¿Qué pasa si dos periodos se solapan o hay OT sin fecha de cierre?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir CRUD de la ficha de técnico: nombre completo, especialidades (multivalor), certificaciones/formación, sucursal(es) donde trabaja. [Esp. §4.3]
- **FR-002**: Cada técnico DEBE poder vincularse a un usuario del sistema (001) con su nivel de acceso. [Esp. §4.3]
- **FR-003**: El sistema DEBE registrar el costo interno de mano de obra por técnico: sueldo fijo y esquema de comisiones/bonos si aplica, con vigencia. [Esp. §4.3, §5]
- **FR-004**: El sistema DEBE calcular el costo de mano de obra por orden de trabajo con base en una tarifa horaria: tarifa = sueldo mensual del técnico ÷ horas productivas estándar del periodo (parámetro configurable, p. ej. 160 h/mes). El costo de MO de la OT = tarifa × horas que el técnico registró en esa OT; si no hay horas registradas, se usa el tiempo estimado del tipo de reparación (008/§9.2). Este método lo consume 008. [Esp. §5; decisión del negocio]
- **FR-004a**: El bono acumulado del periodo DEBE prorratearse entre las órdenes de trabajo cerradas del periodo, proporcional al costo de mano de obra de cada una, y sumarse al costo de MO de la OT en los reportes de margen. [Esp. §5; decisión del negocio]
- **FR-005**: Gerencia General DEBE poder definir reglas de bono por productividad sobre indicadores objetivos: número de OT completadas, cumplimiento de tiempos estimados, margen generado, calidad (tasa de reprocesos/reclamos sobre el mismo reloj). [Esp. §5, §9.1]
- **FR-006**: El bono DEBE poder definirse como monto fijo por meta alcanzada, porcentaje sobre el margen generado, o una combinación. [Esp. §5]
- **FR-007**: La fórmula y los umbrales del bono DEBEN ser parámetros configurables por Gerencia General, con fecha de vigencia y auditoría (mecanismo de 001). [Esp. §5, §9.1, §9.4]
- **FR-008**: El sistema DEBE calcular automáticamente el bono acumulado por técnico y por periodo a partir de las órdenes de trabajo (008), con desglose por indicador. [Esp. §5]
- **FR-009**: El bono acumulado DEBE reflejarse como parte del costo de mano de obra en los reportes de margen y NUNCA exponerse al cliente. [Esp. §5]
- **FR-010**: El bono NUNCA puede ser negativo; un periodo sin OT arroja bono 0. [Esp. §5 — regla de integridad derivada]
- **FR-011**: Cambiar la fórmula o los umbrales del bono DEBE recalcular el bono de todos los periodos de liquidación aún abiertos (no cerrados); los periodos ya cerrados conservan su valor histórico. Todo el efecto queda auditado. [Esp. §9.4; Const. "Parámetros configurables — recálculo en cascada"]
- **FR-012**: El sistema DEBE ofrecer una vista operativa de productividad por técnico: OT completadas, tiempo promedio de ejecución, margen generado, bono alcanzado. [Esp. §4.3, §4.11.2 — versión operativa]
- **FR-013**: Las especialidades del técnico DEBEN estar disponibles para que 008 sugiera la asignación de una OT según calibre/marca. [Esp. §4.3, §4.7]
- **FR-014**: El costo interno de mano de obra y el desglose del bono DEBEN restringirse a roles administrativos. [Esp. §6]
- **FR-015**: El módulo DEBE declarar sus permisos bajo "Técnicos" en el esquema RBAC de dos niveles. [Esp. §3.1; Const. Ppio IV]
- **FR-016**: Todo cambio de costo interno o de esquema de bono DEBE auditarse con actor, timestamp y valor anterior/nuevo. [Esp. §6]
- **FR-017**: Un técnico con historial NO se elimina; se desactiva. La inactivación de un técnico SOLO la realiza el Técnico Jefe o Gerencia General; un técnico no puede inactivarse a sí mismo. [Esp. §6 "Trazabilidad"]
- **FR-017a**: Un técnico puede editar únicamente sus datos de contacto (a través del autoservicio de usuario de 001) y su foto de perfil; NO puede editar su costo interno de mano de obra, su esquema de bono, sus especialidades ni sus certificaciones — esos los mantiene el Técnico Jefe o Gerencia General. [Necesidad del negocio; Esp. §6]
- **FR-018**: Los listados DEBEN tener filtros reactivos y paginación; el panel de trabajo usa el set estandarizado de acciones y ofrece exportación CSV/Excel/PDF de la productividad. [Const. Ppio XI]
- **FR-019**: Las comisiones para vendedores quedan FUERA de alcance de esta feature (propuesta abierta §8); el modelo del esquema de incentivos NO debe impedir añadirlas después. [Esp. §8; Const. Ppio VII]

### Key Entities *(include if feature involves data)*

- **Técnico**: nombre, especialidades, certificaciones, sucursales, vínculo a usuario, estado.
- **Especialidad**: catálogo (marca/complicación).
- **EsquemaCostoManoObra**: técnico, sueldo fijo mensual, tarifa horaria derivada, horas productivas estándar del periodo (parámetro), vigencia.
- **ReglaBono**: indicadores considerados, umbrales, fórmula (fijo / % margen / combinación), periodo de evaluación, vigencia.
- **BonoAcumulado**: técnico, periodo, valor total, desglose por indicador, estado (abierto / cerrado).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Registrar un técnico completo con costo interno y esquema toma menos de 3 minutos.
- **SC-002**: El motor de bono produce el mismo resultado que un cálculo manual sobre un set de órdenes de prueba (módulo con cobertura de pruebas obligatoria, Const. Ppio IX).
- **SC-003**: Cambiar la fórmula del bono queda auditado y no altera los bonos de periodos ya cerrados.
- **SC-004**: El costo de mano de obra prorrateado por orden está disponible para 008 mediante un contrato estable.
- **SC-005**: La productividad por técnico coincide al 100% con las órdenes de trabajo registradas.
- **SC-006**: El costo de mano de obra no es visible para roles no administrativos y no aparece en ningún documento del cliente (verificado en integración).

## Assumptions

- 001 y 004 están implementadas (usuario, sucursal, scoping, parámetros de configuración).
- La acumulación de bono "en vivo" se activa cuando 008 registra órdenes de trabajo; hasta entonces el motor se valida con datos de prueba.
- El reporte analítico comparativo de productividad (entre técnicos, periodos y sucursales) es 013.
- Las comisiones de vendedores están fuera de alcance (propuesta §8).
- El "margen generado" por técnico se toma de las órdenes de trabajo cerradas en el periodo, cuyo cálculo lo entrega 008.
- Las horas trabajadas por OT las registra el técnico en 008; si faltan, el costeo cae al tiempo estimado del tipo de reparación.
- Las horas productivas estándar del periodo (denominador de la tarifa horaria) son un parámetro configurable de 001 (por defecto ~160 h/mes).
