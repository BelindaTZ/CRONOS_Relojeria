# Feature Specification: Multi-Sucursal y Traslados de Inventario

**Feature Branch**: `004-multisucursal-traslados`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Transferencia de relojes y piezas entre sucursales con fecha, motivo, responsable de envío/recepción y actualización automática del inventario en ambas (§4.9), historial de transferencias por número de serie (§4.4), y visibilidad de reportes y listados de inventario consolidada o filtrada por sucursal según el rol."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enviar una transferencia entre sucursales (Priority: P1)

El personal autorizado inicia una transferencia de una o varias unidades de reloj (por número de serie) y/o cantidades de pieza desde su sucursal hacia otra, indicando motivo, fecha de envío y responsable de envío.

**Why this priority**: Es la funcionalidad transversal central del modelo multi-sucursal (§4.9) y prerrequisito para operar stock distribuido.

**Independent Test**: Crear una transferencia con varios ítems y verificar que quedan "en tránsito" y fuera de disponibilidad en la sucursal origen.

**Acceptance Scenarios**:

1. **Given** unidades disponibles en la sucursal A, **When** se envía una transferencia hacia B, **Then** los ítems pasan a "en tránsito" y dejan de estar disponibles para venta o servicio en A.
2. **Given** una transferencia con origen y destino iguales, **When** se intenta enviar, **Then** el sistema la rechaza.
3. **Given** una unidad ya vendida, **When** se intenta incluir en una transferencia, **Then** el sistema la excluye.

---

### User Story 2 - Recibir la transferencia en destino (Priority: P1)

El responsable de recepción en la sucursal destino confirma la llegada con fecha real; el inventario se actualiza automáticamente en ambas sucursales.

**Why this priority**: Cierra el ciclo y garantiza el registro real de la operación (Const. Ppio II).

**Independent Test**: Confirmar una recepción y verificar que los relojes cambian de sucursal y el stock de piezas se mueve, sin ajustes manuales.

**Acceptance Scenarios**:

1. **Given** una transferencia en tránsito, **When** el destino confirma la recepción completa, **Then** los relojes quedan con sucursal actual = destino y el stock de piezas se descuenta de A y se suma a B.
2. **Given** una transferencia en tránsito, **When** la recepción reporta menos unidades de las enviadas, **Then** se registra la discrepancia y se ofrece crear la merma "daño/pérdida en tránsito" (011).
3. **Given** una transferencia recibida, **When** se consulta el número de serie de una unidad, **Then** su historial de transferencias muestra origen, destino, fecha y motivo.

---

### User Story 3 - Visibilidad por sucursal vs. consolidada (Priority: P2)

Los reportes y listados de inventario se muestran filtrados por la sucursal del usuario o consolidados, según su rol.

**Why this priority**: §4.9 y §3 exigen que un gerente de sucursal no vea otras sucursales salvo permiso explícito.

**Independent Test**: Con inventario en dos sucursales, comprobar lo que ve un gerente de sucursal frente a Gerencia General.

**Acceptance Scenarios**:

1. **Given** inventario en A y B, **When** un gerente de A consulta el estado de inventario, **Then** solo ve A.
2. **Given** el mismo inventario, **When** Gerencia General consulta, **Then** puede ver el consolidado o filtrar por sucursal.

---

### User Story 4 - Cancelar una transferencia en tránsito (Priority: P3)

El personal autorizado cancela una transferencia que aún no fue recibida; los ítems vuelven a estar disponibles en la sucursal origen.

**Why this priority**: Caso operativo real (envío fallido, error); menor frecuencia.

**Independent Test**: Cancelar una transferencia en tránsito y verificar que los ítems vuelven a disponibilidad en origen.

**Acceptance Scenarios**:

1. **Given** una transferencia en tránsito, **When** se cancela con motivo, **Then** los ítems vuelven a "disponible" en la sucursal origen y el cambio queda auditado.

### Edge Cases

- ¿Qué pasa con una recepción parcial y las unidades faltantes que nunca llegan?
- ¿Qué pasa si el sistema opera con una sola sucursal activa?
- ¿Qué pasa si se intenta vender un ítem en tránsito desde la sucursal destino antes de confirmar recepción?
- ¿Qué pasa si dos usuarios confirman la misma recepción a la vez?
- ¿Qué pasa si la sucursal destino se desactiva mientras hay una transferencia en tránsito hacia ella?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE registrar una transferencia entre dos sucursales distintas con ítems (unidades de reloj por número de serie y/o piezas con cantidad), fecha de envío, motivo y responsable de envío. [Esp. §4.9, §4.4]
- **FR-002**: Al registrar el envío, los ítems DEBEN pasar a estado "en tránsito" y dejar de estar disponibles para venta (009) o servicio (008) en la sucursal origen. [Esp. §4.9; Const. Ppio II]
- **FR-003**: El sistema DEBE registrar la recepción en destino con responsable y fecha real; al confirmarse, el inventario se actualiza automáticamente en ambas sucursales (relojes cambian de sucursal actual; stock de piezas se mueve). [Esp. §4.9]
- **FR-004**: Si la recepción reporta menos cantidad de la enviada, el sistema DEBE registrar la discrepancia y permitir derivarla a un registro de merma "daño/pérdida en tránsito" (011). [Esp. §4.9, §4.12]
- **FR-005**: Cada transferencia DEBE quedar en el historial de transferencias del reloj (número de serie) con fecha, origen, destino y motivo. [Esp. §4.4]
- **FR-006**: El sistema DEBE permitir consultar el historial de transferencias por sucursal y por unidad, con filtros reactivos y paginación. [Esp. §4.9, §4.11.1; Const. Ppio XI]
- **FR-007**: Una transferencia "en tránsito" DEBE poder cancelarse, devolviendo los ítems a "disponible" en la sucursal origen. [Esp. §4.9]
- **FR-008**: El sistema DEBE aplicar el scoping por sucursal de 001 a los reportes y listados de inventario (propia vs. consolidada según rol). [Esp. §4.9, §3, §6]
- **FR-009**: El módulo DEBE declarar sus permisos bajo "Multi-sucursal" en el esquema RBAC de dos niveles. [Esp. §3.1; Const. Ppio IV]
- **FR-010**: Toda confirmación (enviar, recibir, cancelar) y toda entrada puntual (motivo) se resuelve con el modal del design-system, nunca con `window.confirm`/`prompt`. [Const. Ppio XI]
- **FR-011**: El panel de trabajo DEBE usar el set estandarizado de acciones, incluyendo "Confirmar recepción" y "Cancelar transferencia". [Const. Ppio XI]
- **FR-012**: Cada cambio de estado de una transferencia DEBE auditarse con actor y timestamp. [Esp. §6 "Auditoría"]
- **FR-013**: El sistema DEBE funcionar con una sola sucursal activa y escalar a N sucursales sin cambios de modelo de datos. [Esp. §4.9, §6 "escalabilidad multi-sucursal desde el modelo"]
- **FR-014**: El sistema DEBE ofrecer exportación CSV/Excel/PDF del historial de transferencias. [Const. Ppio XI]

### Key Entities *(include if feature involves data)*

- **Transferencia**: sucursal origen, sucursal destino, estado (en preparación / en tránsito / recibida / parcial / cancelada), fecha de envío, fecha de recepción, responsable de envío, responsable de recepción, motivo.
- **LíneaTransferencia**: transferencia, ítem (unidad de reloj por número de serie o pieza + cantidad enviada + cantidad recibida).
- **DiscrepanciaRecepción**: línea de transferencia, cantidad faltante, derivación a merma (011).
- **EventoTransferenciaSerie**: entrada en el historial de transferencias de un número de serie (origen, destino, fecha, motivo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una transferencia de 3 unidades se envía y se recibe, y el inventario de ambas sucursales queda correcto sin ningún ajuste manual.
- **SC-002**: Un ítem en tránsito no puede venderse ni entrar a servicio en ninguna de las dos sucursales (verificado en integración).
- **SC-003**: El historial de transferencias de un número de serie muestra origen, destino, fecha y motivo de cada movimiento.
- **SC-004**: Una recepción con faltante registra la discrepancia y ofrece crear la merma correspondiente.
- **SC-005**: Un gerente de la sucursal A no obtiene inventario de la sucursal B en ningún reporte; Gerencia General obtiene el consolidado.
- **SC-006**: Cancelar una transferencia en tránsito devuelve el 100% de los ítems a disponibilidad en origen.

## Assumptions

- 001 y 003 están implementadas (sucursal, helper de scoping, relojes, piezas).
- Caja, movimientos de dinero y gastos operativos por sucursal (§4.9) son responsabilidad de 010; 004 cubre solo el inventario y su visibilidad por sucursal.
- La asignación de técnicos a sucursales (§4.9) la gestiona 005.
- La merma por daño o pérdida en tránsito se registra en 011; 004 solo detecta y deriva la discrepancia.
- La logística física del transporte queda fuera del sistema; solo se registran los hitos de envío y recepción.
- Los reportes analíticos de rentabilidad por sucursal son 013 (desde ClickHouse); 004 solo aporta la visibilidad operativa por sucursal del inventario.
