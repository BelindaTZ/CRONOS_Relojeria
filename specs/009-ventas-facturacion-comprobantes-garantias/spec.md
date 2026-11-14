# Feature Specification: Ventas, Comprobantes y Garantías

**Feature Branch**: `009-ventas-facturacion-comprobantes-garantias`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Orden de venta de relojes y piezas (Principio II), baja de stock y evento de venta en el número de serie, aplicación de descuentos/cupones con margen mínimo protegido (006), medios de pago sin pasarela en línea, cálculo del margen de la venta (§4.11.2), garantías de fábrica y de tienda por transacción (§7), y generación del comprobante de venta y del certificado de garantía/autenticidad a `comprobantes-venta`. Genera la cuenta por cobrar."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar y confirmar una venta (Priority: P1)

El vendedor registra una venta con cliente, una o varias unidades de reloj (por número de serie) y/o piezas sueltas, precio, descuentos y medios de pago; al confirmar, el stock baja y se generan los documentos.

**Why this priority**: Es la transacción de negocio central del retail (Principio II, §2.2).

**Independent Test**: Registrar una venta de un reloj con descuento y pago mixto, confirmarla y verificar baja de stock, evento en el número de serie y documentos generados.

**Acceptance Scenarios**:

1. **Given** una unidad disponible, **When** se confirma su venta, **Then** sale del stock activo y su número de serie registra el evento "venta".
2. **Given** una venta con pago en efectivo + transferencia, **When** se confirma, **Then** ambos pagos quedan registrados y suman el total.
3. **Given** una unidad "en tránsito" entre sucursales, **When** se intenta vender, **Then** el sistema lo impide.

---

### User Story 2 - Margen de la venta y margen mínimo protegido (Priority: P1)

El sistema calcula el margen de la venta (precio final descontado − costo de adquisición) y, al aplicar descuentos o cupones, valida el margen mínimo protegido de 006.

**Why this priority**: Cálculo de margen de venta y margen mínimo tras descuentos: lógica crítica con cobertura de pruebas obligatoria (Const. Ppio IX); siempre en backend (Const. Ppio V).

**Independent Test**: Verificar el margen sobre casos de prueba y el bloqueo cuando un descuento lo lleva bajo el mínimo.

**Acceptance Scenarios**:

1. **Given** un reloj con costo de adquisición conocido, **When** se vende con un 10% de descuento, **Then** el margen se calcula sobre el precio ya descontado.
2. **Given** un descuento que dejaría el margen bajo el mínimo configurado, **When** se intenta confirmar, **Then** el sistema bloquea salvo autorización de Gerencia General registrada.

---

### User Story 3 - Garantías de fábrica y de tienda (Priority: P1)

Cada venta registra la garantía de fábrica (marca) y la garantía de tienda, con periodos configurables por tipo de producto.

**Why this priority**: §7 exige diferenciar garantía de fábrica vs. garantía del servicio propio; la constitución adopta el certificado por transacción (Ppio III).

**Independent Test**: Confirmar una venta y verificar los dos periodos de garantía registrados.

**Acceptance Scenarios**:

1. **Given** parámetros de garantía por tipo de producto, **When** se confirma la venta, **Then** se registran ambas garantías con sus fechas de vigencia.

---

### User Story 4 - Comprobante y certificado (Priority: P1)

Al confirmar la venta, el sistema genera el comprobante de venta (PDF) y el certificado de garantía/autenticidad vinculado al número de serie, y los almacena en `comprobantes-venta`, servidos solo vía endpoint autenticado.

**Why this priority**: Const. Ppio III y §2.3/§7: documento generado al confirmar cada transacción.

**Independent Test**: Confirmar una venta y recuperar ambos PDF solo con autenticación y permiso.

**Acceptance Scenarios**:

1. **Given** una venta confirmada, **When** se generan los documentos, **Then** quedan en `comprobantes-venta` y no exponen costos ni márgenes.
2. **Given** un usuario sin permiso, **When** solicita un comprobante, **Then** recibe 403.

---

### User Story 5 - Venta a crédito y cuenta por cobrar (Priority: P2)

Si el pago no cubre el total, el saldo pendiente genera una cuenta por cobrar que 010 consume.

**Why this priority**: §4.10 exige el control de cuentas por cobrar; el hecho se origina en la venta.

**Independent Test**: Confirmar una venta con pago parcial y verificar la CxC por el saldo exacto.

**Acceptance Scenarios**:

1. **Given** una venta de 5 000 con pago de 3 000, **When** se confirma, **Then** se genera una cuenta por cobrar de 2 000 a nombre del cliente.

---

### User Story 6 - Anulación o devolución (Priority: P2)

El personal autorizado anula o registra la devolución de una venta: reingreso de stock, reversa del margen y del nivel de fidelización, y documento de anulación.

**Why this priority**: Necesario para la trazabilidad e integridad del margen (§6, §4.8.2).

**Independent Test**: Anular una venta y verificar el reingreso de stock y las reversas.

**Acceptance Scenarios**:

1. **Given** una venta confirmada, **When** se anula con motivo, **Then** la unidad vuelve al stock, el margen se revierte y el nivel de fidelización del cliente se recalcula.
2. **Given** una venta cuyo reloj ya entró a servicio técnico, **When** se intenta anular, **Then** el sistema lo impide o exige resolver la OT primero.

### Edge Cases

- ¿Qué pasa si dos cajas confirman la venta de la última unidad a la vez?
- ¿Qué pasa si el medio de pago "cheque" se registra y luego el cheque rebota? (se resuelve en 010)
- ¿Qué pasa con el certificado si la unidad no tiene foto cargada?
- ¿Qué pasa si se anula una venta que ya disparó un ascenso de nivel de fidelización?
- ¿Qué pasa si una venta de piezas sueltas a "consumidor final" supera el monto configurable? (se exige identificar al cliente)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE registrar una orden de venta con cliente, una o varias unidades de reloj (por número de serie) y/o piezas sueltas, con su precio de lista. [Const. Ppio II; Esp. §2.2, §4.4]
- **FR-002**: Al confirmar la venta, la(s) unidad(es) DEBEN salir del stock activo (003) y registrarse el evento "venta" en el historial del número de serie. [Esp. §4.4; Const. Ppio II]
- **FR-003**: El sistema DEBE aplicar descuentos y cupones mediante el servicio compartido de 006, respetando el margen mínimo protegido (bloqueo o autorización de Gerencia General). [Esp. §4.8.2]
- **FR-004**: El sistema DEBE calcular automáticamente el margen de la venta = precio final descontado − costo de adquisición. [Esp. §4.8.2, §4.11.2 "Margen por reloj vendido"]
- **FR-005**: El sistema DEBE registrar uno o varios medios de pago por venta, del catálogo `medio_pago` de 001 (Efectivo, Transferencia Bancaria, Cheque, Tarjeta vía datáfono), reutilizando el registro de pagos multimedios compartido introducido en 008; sin pasarela de pago en línea. El ciclo del cheque (protesto) es de 010. [Const. "Stack"; Const. Ppio X]
- **FR-006**: Si el pago no cubre el total, el saldo pendiente DEBE generar una cuenta por cobrar consumida por 010. [Esp. §4.10 "Cuentas por cobrar a clientes"]
- **FR-007**: El sistema DEBE registrar, por transacción, la garantía de fábrica y la garantía de tienda, con periodos configurables por tipo de producto. [Esp. §7, §2.3, §9.2; Const. Ppio III]
- **FR-008**: Al confirmar la venta, el sistema DEBE generar el comprobante de venta (PDF) y el certificado de garantía/autenticidad vinculado al número de serie, y almacenarlos en `comprobantes-venta`, servidos vía endpoint autenticado. [Const. Ppio III; Esp. §2.3, §7]
- **FR-009**: El comprobante y el certificado NO exponen costos internos ni márgenes. [Esp. §6, §5]
- **FR-010**: Al confirmar la venta, el sistema DEBE actualizar el historial de compras del cliente y disparar el recálculo de su nivel de fidelización (006). [Esp. §4.8, §4.8.1]
- **FR-011**: La venta DEBE poder vincularse a la cita de la que proviene (007). [Esp. §4.1]
- **FR-012**: El sistema DEBE permitir anular o registrar la devolución de una venta: reingreso de stock, reversa del margen y del nivel de fidelización, y documento de anulación. [Esp. §6, §4.8.2]
- **FR-013**: La venta de piezas sueltas DEBE descontar stock de piezas (003) y calcular su margen (precio − costo). [Esp. §2.2 (punto 3), §4.5]
- **FR-014**: El sistema DEBE registrar quién realizó la venta y en qué sucursal, aplicando el scoping por sucursal de 001. [Esp. §4.9, §6]
- **FR-015**: Los cambios de precio y las anulaciones DEBEN auditarse con actor, timestamp y motivo. [Esp. §6]
- **FR-016**: El módulo DEBE declarar sus permisos (módulo de Ventas/Facturación) en el esquema RBAC de dos niveles. [Const. Ppio IV; Esp. §3.1]
- **FR-017**: El cálculo de margen y la validación de margen mínimo DEBEN ejecutarse siempre en el backend. [Const. Ppio V]
- **FR-018**: Los listados DEBEN tener filtros reactivos y paginación; el panel de trabajo usa el set estandarizado (incluye "Confirmar venta" y "Anular"); las confirmaciones y entradas puntuales usan el modal del design-system; los reportes se exportan en CSV/Excel/PDF. [Const. Ppio XI]
- **FR-019**: El sistema DEBE exponer los datos de la venta (cliente, cupones aplicados, beneficios) para que 014 envíe comunicaciones; el envío NO es responsabilidad de esta feature. [Const. "Stack"; Const. "Flujo de Trabajo" §014]
- **FR-020**: El sistema DEBE ofrecer una consulta operativa de ventas del día y su margen. [Esp. §4.11.2 — versión operativa; el analítico es 013]
- **FR-021**: La facturación electrónica ante el SRI NO se implementa en esta fase; el modelo de datos del comprobante DEBE ser compatible con incorporarla después (identificación fiscal del cliente, secuencial, impuestos desglosados). [Esp. §7; Const. "Stack"]
- **FR-022**: Toda venta de reloj DEBE exigir una ficha de cliente identificado (por la garantía, el certificado, la fidelización y el respaldo legal). Solo se admite "consumidor final" anónimo para venta de piezas sueltas por debajo de un monto configurable. [Esp. §4.8; decisión del negocio]

**Ampliación (2026-09-10, feedback del usuario tras la 1ª implementación):**

- **FR-023**: La venta NO lleva un campo de sucursal de libre elección: se registra en la sucursal del **vendedor** que la confirma (usuario con una sola sucursal asignada → automática; con varias → elige entre las suyas; Gerencia General, sin sucursal asignada, indica en cuál). [Esp. §4.9, §6; decisión del negocio]
- **FR-024**: Los precios del catálogo son **PVP (IVA incluido)**. El sistema DEBE calcular el IVA por *back-out* (`base = precio / (1 + IVA%)`, `IVA = precio − base`) y mostrarlo desglosado en la factura junto con el descuento y el total, según la tasa vigente del parámetro `iva_porcentaje` (15 % por defecto, configurable por Gerencia General). [Esp. §7, §9.1; Ley de Régimen Tributario Interno de Ecuador]
- **FR-025**: El comprobante de venta es una **factura completa**: datos del emisor (razón social, nombre comercial, RUC, dirección matriz y del establecimiento, obligado a llevar contabilidad, contribuyente especial, régimen), numeración tipo SRI `EEE-PPP-NNNNNNNNN` (establecimiento-punto de emisión-secuencial propio por sucursal), datos del cliente con su identificación, detalle con precio unitario sin impuesto y descuento por línea, y el bloque de totales reglamentario (subtotal por tarifa, subtotal sin impuestos, total descuento, IVA, valor total). Sin autorización real del SRI en esta fase (FR-021 se mantiene). [Esp. §7; decisión del negocio]
- **FR-026**: Los datos del emisor y el punto de emisión de cada sucursal DEBEN ser configurables por Gerencia General (o delegado) desde Sistema → Configuración → Facturación. [Const. Ppio IV; Esp. §9]
- **FR-027**: El sistema DEBE permitir enviar la factura de una venta confirmada al correo del cliente mediante una acción manual del personal (no es un envío automático ni responsabilidad de 014); requiere que el cliente tenga correo registrado. Usa la capacidad compartida de correo con plantilla (001, Const. Ppio XI). [Esp. §7; decisión del negocio]
- El **margen de la venta** (FR-004) se recalcula sobre el precio **neto de IVA** (el IVA se remite al SRI, no es ingreso del negocio): `margen_línea = (precio_final / (1 + IVA%)) − costo`.

### Key Entities *(include if feature involves data)*

- **OrdenVenta**: cliente, sucursal, vendedor, fecha, estado (borrador / confirmada / anulada), total, descuentos aplicados, margen, cita vinculada.
- **LíneaVenta**: orden, ítem (unidad de reloj por número de serie o pieza + cantidad), precio de lista, precio final, costo, margen.
- **PagoVenta**: orden, medio de pago, monto, referencia.
- **MedioPago**: catálogo fijo de 001 (Efectivo, Transferencia Bancaria, Cheque, Tarjeta vía datáfono).
- **GarantíaVenta**: orden, tipo (fábrica / tienda), periodo, cobertura, fechas.
- **Comprobante** / **CertificadoGarantíaAutenticidad**: referencia a objeto en `comprobantes-venta`, número de serie vinculado.
- **AnulaciónVenta**: orden, motivo, actor, fecha, reversas aplicadas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Registrar y confirmar una venta de un reloj con descuento y pago mixto toma menos de 4 minutos.
- **SC-002**: Al confirmar, la unidad sale del stock, el número de serie registra "venta" y el comprobante + certificado quedan en `comprobantes-venta`.
- **SC-003**: El margen de la venta coincide con precio final − costo de adquisición en el 100% de los casos de prueba (módulo con cobertura obligatoria).
- **SC-004**: Un descuento que viola el margen mínimo se bloquea salvo autorización de Gerencia General registrada.
- **SC-005**: Una venta a crédito genera la cuenta por cobrar por el saldo exacto.
- **SC-006**: Anular una venta reingresa el 100% del stock vendido y revierte nivel de fidelización y margen.
- **SC-007**: Los comprobantes y certificados solo son accesibles con autenticación y permiso.
- **SC-008**: Ningún documento entregado al cliente muestra costos ni márgenes.

## Assumptions

- 001, 003, 006 y 008 están implementadas; esta feature reutiliza de `backend/src/shared/` el helper de generación de PDF y el registro de pagos multimedios introducidos por 008, y el catálogo `medio_pago` de 001.
- El certificado de autenticidad/garantía queda adoptado por la constitución (Ppio III), resolviendo la propuesta abierta de §8 / §2.3.
- Toda venta de reloj exige cliente identificado; "consumidor final" anónimo solo para piezas sueltas bajo un monto configurable (decisión del negocio).
- El subledger de cuentas por cobrar y su aging los construye 010; 009 genera la obligación.
- La facturación electrónica ante el SRI está fuera de alcance (§7 pendiente).
- Los reportes analíticos de margen por marca/modelo, rotación y comparativo costo vs. precio son 013.
- El envío de cupones y beneficios post-venta lo hace 014.
