# Feature Specification: Mermas y Pérdidas

**Feature Branch**: `011-mermas-perdidas`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Registro de cualquier reloj o pieza que sale de stock por daño, pérdida, robo o defecto sin venta (§4.12): bien afectado, causa, fecha, sucursal, responsable, costo a costo de adquisición, ciclo de estados, documento de soporte y usuario que autoriza. Baja del inventario activo conservando historial, asiento automático de pérdida extraordinaria en 010, vínculo a OT (008) o a transferencia (004), y umbral de autorización de Gerencia General (§9.2)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reportar una merma (Priority: P1)

Un técnico o vendedor reporta una merma indicando el bien afectado (reloj por número de serie o pieza por código y cantidad), la causa, la fecha del evento, la sucursal y el responsable; la merma queda "en evaluación".

**Why this priority**: Es el hecho de negocio que saca un bien del stock sin venta y debe quedar trazado (§4.12, Const. Ppio II).

**Independent Test**: Reportar una merma de una unidad y verificar su estado inicial y el costo calculado.

**Acceptance Scenarios**:

1. **Given** una unidad en stock, **When** un técnico reporta un daño en tienda, **Then** la merma queda "en evaluación" con el costo a costo de adquisición.
2. **Given** una unidad ya vendida, **When** se intenta reportar una merma sobre ella, **Then** el sistema lo impide.
3. **Given** una pieza con stock 2, **When** se reporta una merma de 3 unidades, **Then** el sistema lo rechaza.

---

### User Story 2 - Autorización de baja sobre el umbral (Priority: P1)

Las mermas cuyo costo supera el monto configurable requieren autorización expresa de Gerencia General antes de la baja definitiva; el sistema registra quién autoriza.

**Why this priority**: Regla de negocio explícita de §4.12 y §9.2; Const. Ppio XI define la acción "Autorizar baja".

**Independent Test**: Intentar dar de baja una merma sobre el umbral sin autorización y verificar el bloqueo; luego con autorización registrada.

**Acceptance Scenarios**:

1. **Given** una merma cuyo costo supera el umbral, **When** se intenta pasarla a "dado de baja definitivamente" sin autorización, **Then** el sistema lo impide.
2. **Given** la misma merma, **When** Gerencia General autoriza, **Then** la baja procede y queda registrado quién autorizó y cuándo.

---

### User Story 3 - Baja del inventario y asiento contable (Priority: P1)

Al confirmarse la baja, el bien se retira del inventario activo conservando su historial completo y se genera automáticamente el asiento de gasto/pérdida extraordinaria en 010, separado de los gastos operativos regulares.

**Why this priority**: §4.12 lo exige de forma explícita; conecta inventario y contabilidad.

**Independent Test**: Confirmar una baja y verificar que el bien sale del stock activo, conserva historial y genera el asiento en 010.

**Acceptance Scenarios**:

1. **Given** una merma autorizada, **When** se confirma la baja, **Then** el bien deja de estar en el stock activo pero su historial sigue consultable por número de serie.
2. **Given** la misma baja, **When** se consulta la contabilidad, **Then** existe el asiento de pérdida extraordinaria por el costo de adquisición, separado de los gastos operativos.

---

### User Story 4 - Ciclo de estados y reingreso (Priority: P2)

La merma avanza por los estados en evaluación → dado de baja / en reclamo a proveedor / en reclamo a seguro / reparado y reingresado a stock; el reingreso devuelve el bien al inventario activo con su historial.

**Why this priority**: §4.12 define estos estados; el reingreso evita perder unidades recuperables.

**Independent Test**: Llevar una merma a "reparado y reingresado" y verificar que el bien vuelve al stock con su historial.

**Acceptance Scenarios**:

1. **Given** una merma "en evaluación", **When** se marca "reparado y reingresado a stock", **Then** el bien vuelve al inventario activo y conserva el registro de la merma.
2. **Given** una merma por defecto de fábrica, **When** se marca "en reclamo a proveedor", **Then** se vincula al proveedor (002) para seguimiento.

---

### User Story 5 - Mermas derivadas de servicio o de traslado (Priority: P2)

Una merma originada por daño durante un servicio técnico queda vinculada a la OT y al técnico; una por daño o pérdida en tránsito queda vinculada a la transferencia.

**Why this priority**: §4.12 exige la trazabilidad interna; los orígenes vienen derivados de 008 y 004.

**Independent Test**: Crear una merma desde una OT y desde una transferencia y verificar los vínculos.

**Acceptance Scenarios**:

1. **Given** un daño registrado en una OT (008), **When** se genera la merma, **Then** queda vinculada a esa OT y al técnico, sin sanción automática.
2. **Given** una discrepancia de recepción en una transferencia (004), **When** se genera la merma, **Then** queda vinculada a esa transferencia.

---

### User Story 6 - Reporte de mermas y pérdidas (Priority: P2)

El personal autorizado consulta el reporte de mermas por monto, causa y frecuencia.

**Why this priority**: §4.11.2 lo pide; base para decisiones de prevención y de seguros.

**Independent Test**: Generar el reporte y verificar que cuadra con los registros.

**Acceptance Scenarios**:

1. **Given** varias mermas de distintas causas, **When** se genera el reporte, **Then** agrupa por causa con monto y frecuencia y se puede exportar.

### Edge Cases

- ¿Qué pasa con una merma cuyo costo queda exactamente en el umbral de autorización?
- ¿Qué pasa si el proveedor no repone el bien en reclamo?
- ¿Qué pasa al reingresar un bien cuyo modelo ya superó el stock máximo recomendado?
- ¿Qué pasa si se intenta autorizar una baja sin el permiso correspondiente?
- ¿Qué pasa si se anula la venta de un reloj que después se quiso dar por merma?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE registrar una merma sobre un reloj (número de serie) o una pieza (código + cantidad + lote si es perecedera), con causa (daño en tienda, daño en tránsito/transporte, robo o pérdida, defecto de fábrica, daño durante servicio técnico, **insumo/repuesto caducado o vencido**), fecha del evento, sucursal y responsable que reporta. [Esp. §4.12; necesidad del negocio]
- **FR-001a**: Una merma de causa "insumo caducado" DEBE poder generarse desde la alerta de lote vencido de 003, prellenada con la pieza, el lote y la cantidad. [Necesidad del negocio; Esp. §4.6, §4.12]
- **FR-002**: El sistema DEBE calcular el costo de la pérdida a costo de adquisición del bien, nunca a precio de venta. [Esp. §4.12, §4.10.1]
- **FR-003**: La merma DEBE seguir el ciclo de estados: en evaluación, dado de baja definitivamente, en reclamo a proveedor, en reclamo a seguro, reparado y reingresado a stock. [Esp. §4.12]
- **FR-004**: El sistema DEBE permitir adjuntar documento(s) de soporte (acta interna, fotografías, denuncia policial) a la merma, almacenados en el bucket `documentos` (prefijo de merma) y servidos vía endpoint autenticado. [Esp. §4.12; Const. Ppio III]
- **FR-005**: El monto de merma a partir del cual se requiere aprobación de Gerencia General DEBE ser un parámetro configurable. [Esp. §4.12, §9.2]
- **FR-006**: Una merma cuyo costo supera el umbral NO puede pasar a "dado de baja definitivamente" sin autorización expresa de Gerencia General; el sistema registra quién autoriza y cuándo. [Esp. §4.12, §9.2]
- **FR-007**: Al confirmarse la baja, el bien DEBE retirarse del inventario activo (003) conservando su historial completo. [Esp. §4.12, §4.4]
- **FR-008**: Al confirmarse la baja, el sistema DEBE generar automáticamente el asiento de gasto/pérdida extraordinaria en 010, separado de los gastos operativos regulares. [Esp. §4.12, §4.10.1]
- **FR-009**: Una merma por daño durante servicio técnico DEBE quedar vinculada a la orden de trabajo y al técnico responsable, sin sanción automática. [Esp. §4.12]
- **FR-010**: Una merma por daño o pérdida en tránsito DEBE poder vincularse a la transferencia de origen (004). [Esp. §4.12, §4.9]
- **FR-011**: El estado "reparado y reingresado a stock" DEBE devolver el bien al inventario activo con su historial completo (incluida la merma). [Esp. §4.12]
- **FR-012**: El estado "en reclamo a proveedor" DEBE poder vincularse al proveedor (002); "en reclamo a seguro" registra aseguradora, estado del reclamo y monto recuperado. [Esp. §4.12]
- **FR-013**: El sistema DEBE ofrecer el reporte de mermas y pérdidas por monto, causa y frecuencia. [Esp. §4.11.2 — versión operativa]
- **FR-014**: El scoping por sucursal (001) DEBE aplicarse a los listados y reportes de mermas. [Esp. §3, §4.9]
- **FR-015**: El módulo DEBE declarar sus permisos bajo "Mermas": Técnico con Crear/Consultar, Gerente de Sucursal con Crear/Consultar/Editar, Gerencia General también Eliminar (autoriza bajas). [Esp. §3.1; Const. Ppio IV]
- **FR-016**: Toda confirmación y entrada puntual (causa, motivo, id que autoriza) se resuelve con el modal del design-system; el panel de trabajo incluye la acción "Autorizar baja". [Const. Ppio XI]
- **FR-017**: Cada cambio de estado y cada autorización DEBEN auditarse con actor y timestamp. [Esp. §6, §9.4]
- **FR-018**: El sistema NO puede registrar una merma sobre un bien ya vendido o ya dado de baja. [Esp. §4.12 — regla de integridad derivada]
- **FR-019**: La merma de una pieza NO puede exceder el stock disponible de esa pieza en la sucursal. [Esp. §4.5, §4.12]
- **FR-020**: Los reportes se exportan en CSV/Excel/PDF. [Const. Ppio XI]

### Key Entities *(include if feature involves data)*

- **Merma**: bien afectado (reloj o pieza + cantidad), causa, fecha del evento, sucursal, responsable, costo (a costo de adquisición), estado, autorización de baja, OT vinculada (008), transferencia vinculada (004), asiento contable generado (010).
- **DocumentoSoporteMerma**: tipo (acta / fotografía / denuncia), referencia a objeto en el bucket `documentos`.
- **ReclamoMerma**: destino (proveedor / seguro), estado, monto recuperado.
- **ParámetroUmbralMerma**: monto que dispara la autorización de Gerencia General.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reportar una merma toma menos de 2 minutos y queda "en evaluación" con el costo a costo de adquisición.
- **SC-002**: Una merma sobre el umbral no puede darse de baja sin autorización de Gerencia General registrada.
- **SC-003**: Al confirmarse la baja, el bien sale del inventario activo y se genera el asiento de pérdida extraordinaria en 010.
- **SC-004**: El bien dado de baja conserva su historial completo consultable por número de serie.
- **SC-005**: Una merma derivada de una OT (008) o de una transferencia (004) conserva el vínculo.
- **SC-006**: "Reparado y reingresado" devuelve el bien al stock activo con su historial.
- **SC-007**: El reporte de mermas cuadra por monto, causa y frecuencia con los registros.
- **SC-008**: El registro y costeo de mermas está cubierto por pruebas unitarias/integración (Const. Ppio IX).

## Assumptions

- 001, 003, 008 y 010 están implementadas.
- El asiento contable de la pérdida se genera vía la API de asientos de 010.
- Los adjuntos de soporte se guardan en el bucket `documentos` provisionado por 000.
- La merma de un insumo por caducidad se enlaza con el lote/caducidad gestionado en 003.
- El reporte analítico de mermas comparado entre periodos, causas y sucursales es 013.
- La gestión del reclamo con aseguradora o proveedor se limita al seguimiento de estado y montos recuperados; sin integración externa.
- La vinculación técnico ↔ merma es informativa para trazabilidad interna, sin efecto disciplinario automático (§4.12).
