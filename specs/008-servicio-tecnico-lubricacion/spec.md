# Feature Specification: Servicio Técnico y Lubricación

**Feature Branch**: `008-servicio-tecnico-lubricacion`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Órdenes de trabajo con trazabilidad por número de serie (§4.7), fichas de lubricación por calibre con producto Moebius recomendado por punto y registro del producto realmente usado (§4.6), costeo y margen del servicio (§5: mano de obra prorrateada + piezas + insumos; precio = costo + margen configurable; margen real automático), ciclo de estados y garantía del servicio, y generación del documento de la orden y del certificado de garantía a `comprobantes-venta`."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abrir una orden de trabajo y asignar técnico (Priority: P1)

El personal crea una orden de trabajo para un reloj adquirido en la tienda (por número de serie), con cliente, motivo y fecha de ingreso, y asigna un técnico (sugerido según especialidad y calibre). La fecha estimada de entrega NO se ingresa aquí: se registra recién tras el diagnóstico. Al asignar el técnico, el cliente recibe por email la información general del técnico (nombre, especialidades, certificaciones) y un email de contacto.

**Why this priority**: La OT es el documento de negocio del servicio técnico y la base de su costeo y trazabilidad (§4.7, Const. Ppio II).

**Independent Test**: Crear una OT para un número de serie del inventario/historial de ventas, asignar técnico y verificar el estado "recibido", la ausencia de fecha estimada y el email al cliente.

**Acceptance Scenarios**:

1. **Given** un reloj vendido por la tienda, **When** se abre una OT para su número de serie, **Then** la OT queda en estado "recibido" con fecha de ingreso y SIN fecha estimada de entrega.
2. **Given** un número de serie que la tienda nunca vendió, **When** se intenta abrir la OT, **Then** el sistema advierte y exige autorización para continuar (§2.1).
3. **Given** un calibre con especialistas registrados, **When** se abre la OT, **Then** el sistema sugiere un técnico con esa especialidad.
4. **Given** una OT sin técnico, **When** se le asigna uno, **Then** el cliente recibe un email (plantilla cuidada) con los datos generales del técnico y un email de contacto.

---

### User Story 1b - Diagnóstico, presupuesto y elección de piezas (Priority: P1)

Tras revisar el reloj, el técnico registra el diagnóstico y arma en el sistema un presupuesto: precio del servicio y detalle de piezas con opción "originales" vs. "no originales de calidad equivalente" y su diferencia de costo. La comunicación con el cliente para aprobarlo ocurre por un medio informal externo (WhatsApp, correo); el sistema solo registra el resultado: la preferencia del cliente (originales / no originales / mixto), quién la confirmó y cuándo. Recién con el presupuesto aprobado se fija la fecha estimada de entrega y la OT pasa a "en reparación".

**Why this priority**: Refleja el flujo real del negocio; sin la elección de piezas registrada no se puede costear ni justificar la OT ante el cliente.

**Independent Test**: Registrar un diagnóstico, armar el presupuesto con ambas opciones de piezas, registrar la aprobación del cliente y verificar la fecha estimada y el cambio de estado.

**Acceptance Scenarios**:

1. **Given** una OT en diagnóstico, **When** el técnico arma el presupuesto, **Then** puede listar piezas con opción original y no original y el sistema muestra la diferencia de precio.
2. **Given** un presupuesto preparado, **When** el técnico registra que el cliente aprobó con piezas no originales para dos ítems, **Then** queda registrado el detalle, quién confirmó y la fecha, y se solicita la fecha estimada de entrega.
3. **Given** un presupuesto sin aprobar, **When** se intenta pasar la OT a "en reparación", **Then** el sistema lo impide.

---

### User Story 2 - Registrar diagnóstico, piezas y lubricación (Priority: P1)

El técnico registra el diagnóstico, el trabajo realizado, las piezas usadas (que descuentan stock) y, por cada punto de lubricación del calibre, el producto recomendado y el producto realmente usado.

**Why this priority**: Es el registro real del servicio; alimenta el costo, el consumo de insumos y la auditoría de desviaciones (§4.6, §4.7).

**Independent Test**: Registrar piezas y lubricación en una OT y verificar el descuento de stock y el registro recomendado vs. usado.

**Acceptance Scenarios**:

1. **Given** una OT en reparación, **When** el técnico añade una pieza, **Then** el stock de esa pieza baja y no puede quedar negativo.
2. **Given** el calibre con su ficha de lubricación, **When** el técnico registra los puntos, **Then** por cada punto queda el producto recomendado, el usado, el técnico y la fecha.
3. **Given** un punto donde el técnico usó un producto distinto al recomendado, **When** se guarda, **Then** el sistema registra la desviación sin bloquear.

---

### User Story 3 - Fichas de lubricación por calibre (Priority: P1)

El Técnico Jefe mantiene la ficha técnica de cada calibre: puntos de lubricación, producto Moebius recomendado por punto y notas técnicas.

**Why this priority**: Sin la ficha no hay recomendación contra la cual comparar ni cálculo de consumo (§4.6).

**Independent Test**: Crear la ficha de un calibre con varios puntos y verificar que se ofrece al abrir una OT de ese calibre.

**Acceptance Scenarios**:

1. **Given** el módulo Lubricación, **When** se crea la ficha del calibre con sus puntos y productos recomendados, **Then** queda disponible para las OT de ese calibre.
2. **Given** el catálogo Moebius, **When** se asigna producto a un punto, **Then** se elige de la lista (9010, 9104/HP-1300, 9415, 9501/9504, 8200/8217, 8513/8516…), no como texto libre.

---

### User Story 4 - Costeo y margen del servicio (Priority: P1)

El sistema calcula automáticamente el costo interno (mano de obra prorrateada + piezas + insumos), propone el precio (costo + margen objetivo configurable), y calcula el margen real; los descuentos pasan por el margen mínimo protegido de 006.

**Why this priority**: Cálculo de margen del servicio técnico y margen mínimo tras descuentos: lógica crítica con cobertura de pruebas obligatoria (Const. Ppio IX); se valida siempre en backend (Const. Ppio V).

**Independent Test**: Sobre casos de prueba, verificar costo interno, precio propuesto y margen real, y el bloqueo por margen mínimo.

**Acceptance Scenarios**:

1. **Given** una OT con mano de obra, piezas e insumos, **When** se calcula, **Then** el costo interno es la suma de los tres y el margen real = precio cobrado − costo interno.
2. **Given** un margen objetivo del 50% para el tipo de servicio, **When** se propone el precio, **Then** es costo interno × 1,5 (editable).
3. **Given** un descuento que dejaría el margen bajo el mínimo configurado, **When** se intenta confirmar, **Then** se bloquea salvo autorización de Gerencia General registrada.

---

### User Story 5 - Ciclo de estados, cobro al retiro y garantía (Priority: P1)

La OT avanza por los estados recibido → en diagnóstico → (presupuesto aprobado) → en reparación → listo → entregado. "Listo" significa terminado pero no pagado ni retirado. El cobro del servicio se realiza al momento del retiro: la OT no pasa a "entregado" sin el pago registrado (total, con medios múltiples, o crédito explícitamente autorizado que genera una CxC). Al entregar se registra la fecha real y se genera el documento de la orden y el certificado de garantía del servicio.

**Why this priority**: Cierra el ciclo, produce el comprobante y asegura el cobro (§4.7, §7; regla del negocio: sin pago no se entrega).

**Independent Test**: Recorrer una OT hasta "listo", intentar entregar sin pago (bloqueo), registrar el pago y verificar la entrega, la fecha real y el PDF en `comprobantes-venta`.

**Acceptance Scenarios**:

1. **Given** una OT lista sin pago registrado, **When** se intenta marcar "entregado", **Then** el sistema lo impide y solicita registrar el pago.
2. **Given** una OT lista, **When** se registra el pago (efectivo + tarjeta, por ejemplo) y se marca "entregado", **Then** se registra la fecha real de entrega y se genera el documento de la OT + certificado de garantía en `comprobantes-venta`.
3. **Given** una OT lista, **When** Gerencia General autoriza expresamente la entrega a crédito, **Then** se genera una CxC por el saldo y la OT puede entregarse.
4. **Given** una OT entregada dentro del periodo de garantía, **When** el cliente reclama, **Then** se reabre una OT vinculada a la original.
5. **Given** el documento del cliente, **When** se genera, **Then** no contiene el costo interno de mano de obra.

---

### User Story 6 - Tablero de órdenes en curso e informe de servicios (Priority: P2)

El taller consulta las órdenes de trabajo en curso y su estado. Además existe un informe de servicios/arreglos con detalle por cliente, técnico, reloj y periodo: qué se arregló, fecha, técnico, repuestos usados y precio del arreglo.

**Why this priority**: Seguimiento diario del taller (§4.11.1) y trazabilidad del servicio prestado equivalente a la de las ventas (§6).

**Independent Test**: Abrir el tablero y comprobar el estado real; generar el informe de servicios filtrando por técnico y periodo y verificar el detalle.

**Acceptance Scenarios**:

1. **Given** varias OT en distintos estados, **When** se abre el tablero, **Then** cada una aparece en su estado actual, con filtros reactivos por técnico, estado y sucursal.
2. **Given** OT cerradas en un periodo, **When** se genera el informe de servicios filtrando por un técnico, **Then** cada fila muestra cliente, fecha, reloj (número de serie), trabajo realizado, repuestos usados y precio del arreglo, y se puede exportar.

---

### User Story 7 - Daño durante el servicio (Priority: P2)

Si un reloj o una pieza se daña durante el servicio, el técnico lo registra y el sistema deriva a un registro de merma (011) vinculado a la OT y al técnico.

**Why this priority**: §4.12 exige la trazabilidad interna del daño en servicio.

**Independent Test**: Registrar un daño en una OT y verificar la derivación a merma con los vínculos.

**Acceptance Scenarios**:

1. **Given** una OT en reparación, **When** el técnico registra un daño, **Then** se crea (o se deja lista para crear en 011) una merma "daño en servicio" vinculada a la OT y al técnico, sin sanción automática.

### Edge Cases

- ¿Qué pasa si se cambia el técnico asignado a mitad de la OT (prorrateo de mano de obra)?
- ¿Qué pasa si una pieza necesaria no tiene stock al confirmarla?
- ¿Qué pasa con una OT reabierta por garantía: su costo se cobra o no?
- ¿Qué pasa si el calibre del reloj no tiene ficha de lubricación?
- ¿Qué pasa si el reloj estaba "en tránsito" entre sucursales al abrir la OT?
- ¿Qué pasa si el precio manual deja un margen negativo?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir crear una orden de trabajo asociada a un reloj por número de serie, un cliente y un técnico asignado. [Esp. §4.7]
- **FR-002**: El sistema DEBE verificar que el reloj fue adquirido en la tienda; si no consta, DEBE advertir y requerir autorización para continuar. [Esp. §2.1]
- **FR-003**: La OT DEBE registrar motivo del servicio, diagnóstico y trabajo realizado. [Esp. §4.7]
- **FR-003a**: Al asignar un técnico a la OT, el sistema DEBE enviar al cliente un email (plantilla cuidada) con la información general del técnico (nombre, especialidades, certificaciones) y un email de contacto. El envío usa la capacidad compartida de correo (001); la plantilla la administra 014. [Necesidad del negocio; Const. Ppio XI]
- **FR-003b**: Tras el diagnóstico, el técnico DEBE poder armar un presupuesto con el precio del servicio y el detalle de piezas, ofreciendo por cada pieza la opción "original" y "no original de calidad equivalente" con su diferencia de precio. [Esp. §2.2, §4.5; necesidad del negocio]
- **FR-003c**: El sistema DEBE registrar la preferencia del cliente sobre las piezas (originales / no originales / mixto por ítem), quién la confirmó y cuándo. La comunicación con el cliente para aprobar el presupuesto ocurre fuera del sistema (medio informal); el sistema solo registra el resultado. [Necesidad del negocio; Esp. §4.5]
- **FR-003d**: La OT NO puede pasar a "en reparación" sin un presupuesto aprobado registrado; la fecha estimada de entrega se ingresa en ese momento, no antes. [Necesidad del negocio; Esp. §4.7]
- **FR-004**: La OT DEBE registrar las piezas usadas con su costo, descontando stock (003) al confirmarlas, sin permitir stock negativo. [Esp. §4.7, §4.5; Const. Ppio II]
- **FR-004a**: El técnico DEBE registrar las horas trabajadas en la OT; ese dato alimenta el costeo de mano de obra por tarifa horaria (005). [Esp. §5; decisión del negocio]
- **FR-005**: El sistema DEBE gestionar fichas de lubricación por calibre: marca/calibre, lista de puntos, producto Moebius recomendado por punto, notas técnicas. [Esp. §4.6]
- **FR-006**: El catálogo de productos Moebius DEBE incluir al menos los de la tabla de §4.6 y ser ampliable. [Esp. §4.6]
- **FR-007**: En la OT, por cada punto de lubricación DEBE registrarse producto recomendado, producto realmente usado, técnico que lo aplicó y fecha. [Esp. §4.6]
- **FR-008**: El sistema DEBE permitir que el producto usado difiera del recomendado y registrar la desviación sin bloquear. [Esp. §4.6]
- **FR-009**: El sistema DEBE calcular el consumo real de insumos de lubricación a partir de las OT. [Esp. §4.6]
- **FR-010**: El sistema DEBE calcular el costo interno del servicio = costo de mano de obra por tarifa horaria × horas registradas (o tiempo estimado si no hay horas), según 005, + costo de piezas + costo de insumos. [Esp. §5, §4.7]
- **FR-011**: El margen objetivo del servicio DEBE ser configurable (global, por tipo de servicio o por sucursal); cambiarlo recalcula el precio propuesto y el margen de las OT aún no entregadas (recálculo en cascada, Const.). [Esp. §5, §9.1, §9.4]
- **FR-012**: El precio del servicio DEBE poder calcularse como costo interno + margen objetivo y también fijarse manualmente. [Esp. §5]
- **FR-013**: El sistema DEBE calcular automáticamente el margen real = precio cobrado − costo interno, sin exponer el costo de mano de obra al cliente. [Esp. §4.7, §5]
- **FR-014**: Al aplicar un descuento o cupón a la OT, el sistema DEBE usar el servicio compartido de 006 y respetar el margen mínimo protegido. [Esp. §4.8.2]
- **FR-015**: La OT DEBE seguir el ciclo de estados: recibido, en diagnóstico, (presupuesto aprobado), en reparación, listo, entregado. "Listo" = terminado sin pagar ni retirar. [Esp. §4.7]
- **FR-016**: La OT DEBE registrar la fecha de ingreso al crearla, la fecha estimada de entrega al aprobarse el presupuesto (no antes), y la fecha real de entrega al retirarse. [Esp. §4.7; necesidad del negocio]
- **FR-016a**: El cobro del servicio se realiza al retiro: la OT NO pasa a "entregado" sin el pago registrado (total, con medios múltiples de `medio_pago` — efectivo, transferencia, cheque, tarjeta) o sin una entrega a crédito expresamente autorizada por Gerencia General que genera una CxC. [Necesidad del negocio; Esp. §4.10]
- **FR-016b**: Esta feature DEBE introducir en `backend/src/shared/` la capacidad de registrar pagos multimedios contra un documento facturable (OT o, más adelante, venta), calculando el saldo; la reutiliza 009. El ciclo del cheque (protesto, etc.) es de 010. [Const. Ppio X; Esp. §4.10]
- **FR-017**: El tiempo estimado de servicio por tipo de reparación DEBE ser configurable y usarse para medir cumplimiento. [Esp. §9.2, §5]
- **FR-018**: La OT DEBE registrar la garantía del servicio (periodo y cobertura); el periodo por tipo de servicio es configurable. [Esp. §4.7, §9.2, §7]
- **FR-019**: Al entregar la OT, el sistema DEBE generar en PDF el documento de la orden de trabajo y el certificado de garantía del servicio, y almacenarlo en `comprobantes-venta`, servido vía endpoint autenticado. [Const. Ppio III; Esp. §4.7, §7]
- **FR-020**: Una OT entregada DEBE poder reabrirse por garantía manteniendo la trazabilidad con la OT original. [Esp. §4.7, §6]
- **FR-021**: El sistema DEBE permitir registrar un daño ocurrido durante el servicio y derivarlo a un registro de merma (011) vinculado a la OT y al técnico, sin sanción automática. [Esp. §4.12]
- **FR-022**: El sistema DEBE marcar reprocesos/reclamos sobre el mismo reloj, dato que alimenta el indicador de calidad del bono (005). [Esp. §5]
- **FR-023**: El sistema DEBE ofrecer el reporte operativo "órdenes de trabajo en curso y su estado". [Esp. §4.11.1]
- **FR-023a**: El sistema DEBE ofrecer un informe de servicios/arreglos con detalle por cliente, técnico, reloj (número de serie) y periodo: trabajo realizado, fecha, técnico, repuestos usados y precio del arreglo; con filtros reactivos y exportación CSV/Excel/PDF. [Esp. §4.11.1, §6 (trazabilidad); necesidad del negocio]
- **FR-024**: Cada OT DEBE quedar en el historial de servicios del número de serie (003). [Esp. §4.4, §6]
- **FR-025**: El módulo DEBE declarar sus permisos bajo "Órdenes de trabajo" y "Lubricación"; un técnico solo puede editar las OT asignadas a él (scoping "solo las propias" de 001). [Esp. §3.1; Const. Ppio IV]
- **FR-026**: El costo interno y el margen DEBEN restringirse a roles administrativos y no aparecer en el documento del cliente. [Esp. §6, §5]
- **FR-027**: Los listados DEBEN tener filtros reactivos y paginación; el panel de trabajo usa el set estandarizado de acciones (incluye "Cerrar orden"); las confirmaciones y entradas puntuales usan el modal del design-system; los reportes se exportan en CSV/Excel/PDF. [Const. Ppio XI]
- **FR-028**: El sistema DEBE exponer los cambios de estado de la OT para que 014 notifique al cliente; el envío NO es responsabilidad de esta feature. [Const. "Stack"; Const. "Flujo de Trabajo" §014]

### Key Entities *(include if feature involves data)*

- **OrdenTrabajo**: reloj (número de serie), cliente, técnico asignado, sucursal, motivo, diagnóstico, trabajo realizado, horas trabajadas, precio cobrado, costo interno, margen real, garantía del servicio, cita vinculada (007), OT original (si es reapertura por garantía).
- **Presupuesto**: OT, precio del servicio, opciones de pieza (original / no original + diferencia), preferencia del cliente por ítem, quién confirmó, fecha de aprobación.
- **PagoOT**: OT, medio de pago, monto, referencia (usa el registro de pagos compartido).
- **HistorialEstadoOT**: OT, estado, timestamp, actor.
- **PiezaUsadaOT**: OT, pieza, tipo elegido (original / no original), cantidad, costo.
- **FichaLubricaciónCalibre**: calibre, puntos, producto recomendado por punto, notas.
- **PuntoLubricación**: nombre/ubicación en el calibre.
- **ProductoMoebius**: código, uso recomendado.
- **RegistroLubricaciónOT**: OT, punto, producto recomendado, producto usado, técnico, fecha, marca de desviación.
- **GarantíaServicio**: OT, periodo, cobertura.
- Parámetros configurables: margen objetivo de servicio, tiempo estimado por tipo de reparación, periodo de garantía de tienda por tipo de servicio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Crear una OT completa (reloj, cliente, técnico, motivo) toma menos de 3 minutos.
- **SC-002**: El margen real calculado coincide con precio cobrado − (mano de obra prorrateada + piezas + insumos) en el 100% de los casos de prueba (módulo con cobertura obligatoria).
- **SC-003**: Un descuento que viola el margen mínimo se bloquea salvo autorización de Gerencia General registrada (módulo con cobertura obligatoria).
- **SC-004**: El registro por punto permite comparar recomendado vs. usado en el 100% de las OT y produce el consumo real de insumos.
- **SC-005**: Al entregar una OT se genera su documento y su certificado de garantía en `comprobantes-venta`, accesibles solo con autenticación.
- **SC-006**: Un técnico solo puede editar sus propias OT (verificado en integración).
- **SC-007**: El tablero de OT en curso refleja el estado real de cada orden.
- **SC-008**: El 100% de las OT queda en el historial de servicios del número de serie.

## Assumptions

- 001, 003, 005 y 006 están implementadas (incluye el catálogo `medio_pago` y la capacidad compartida de correo de 001).
- El helper compartido de generación de PDF (documentos de OT y certificados) y el registro de pagos multimedios se introducen en `backend/src/shared/` en esta feature y los reutiliza 009.
- La comunicación con el cliente para aprobar el presupuesto y elegir tipo de piezas ocurre por medios informales fuera del sistema (WhatsApp, correo personal); el sistema solo registra el resultado.
- El costeo de mano de obra usa la tarifa horaria de 005 (sueldo mensual ÷ horas productivas estándar × horas registradas en la OT).
- La merma por daño en servicio se registra en 011; 008 solo detecta y deriva.
- Las notificaciones de cambio de estado al cliente las envía 014.
- Los reportes analíticos (margen por servicio comparado, tiempo medio de servicio, desviación de lubricación agregada, piezas más usadas) son 013.
- La facturación electrónica ante el SRI del servicio está fuera de alcance (§7 pendiente); el documento de la OT es un comprobante interno.
- Para relojes vendidos antes de la puesta en marcha del sistema, la verificación "adquirido en la tienda" se resuelve con override autorizado — **a confirmar** la política de datos históricos.
