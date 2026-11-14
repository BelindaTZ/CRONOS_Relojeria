# Feature Specification: Contabilidad, Gastos, Cuentas por Cobrar y por Pagar

**Feature Branch**: `010-contabilidad-gastos-cxc-cxp`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Contabilidad básica con trazabilidad suficiente (§4.10): libro diario/mayor, balance de comprobación, estado de resultados, caja y bancos por sucursal, cheques, cuentas por cobrar (de 009) y por pagar (de 002), y registro de gastos operativos por sucursal y categoría (§4.10.1). Asientos automáticos desde los hechos de negocio; rentabilidad neta por sucursal. Modelo compatible con NIIF PYMES y con facturación electrónica futura (§7)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Libro diario y derivados (Priority: P1)

El contador registra asientos en el libro diario (con debe/haber balanceados) y consulta el libro mayor, el balance de comprobación y el estado de resultados derivados.

**Why this priority**: Es la base legal y de cálculo de márgenes reales (§4.10, §7).

**Independent Test**: Registrar varios asientos y verificar que el mayor y el balance cuadran.

**Acceptance Scenarios**:

1. **Given** el plan de cuentas, **When** se registra un asiento con debe = haber, **Then** se guarda y se refleja en el mayor.
2. **Given** un asiento con debe ≠ haber, **When** se intenta guardar, **Then** el sistema lo rechaza.
3. **Given** asientos de un periodo, **When** se consulta el balance de comprobación, **Then** la suma de debe iguala la de haber.

---

### User Story 2 - Caja y bancos por sucursal (Priority: P1)

El personal abre y cierra la caja de su sucursal, registra movimientos y realiza el arqueo, dejando constancia de las diferencias.

**Why this priority**: §4.9 exige que cada sucursal gestione su caja; Const. Ppio XI menciona la apertura/cierre de caja como acción estándar.

**Independent Test**: Abrir caja, registrar movimientos, cerrarla con un conteo distinto al esperado y verificar la diferencia registrada.

**Acceptance Scenarios**:

1. **Given** una caja abierta, **When** se cierra con efectivo contado menor al esperado, **Then** se registra la diferencia y el cierre queda auditado.
2. **Given** una caja cerrada, **When** se intenta registrar un movimiento con esa fecha, **Then** el sistema lo impide o exige un ajuste.

---

### User Story 3 - Cuentas por cobrar (Priority: P1)

Las ventas a crédito de 009 generan cuentas por cobrar; el personal registra los cobros (totales o parciales) y consulta el estado y la antigüedad; existe el reporte operativo de CxC pendientes.

**Why this priority**: §4.10 y §4.11.1 lo exigen; es seguimiento de liquidez.

**Independent Test**: Confirmar una venta a crédito en 009 y verificar la CxC, luego registrar un cobro parcial.

**Acceptance Scenarios**:

1. **Given** una venta a crédito de 009, **When** se consulta CxC, **Then** aparece por el saldo exacto a nombre del cliente.
2. **Given** una CxC, **When** se registra un cobro parcial, **Then** el saldo disminuye y el aging se recalcula.

---

### User Story 4 - Cuentas por pagar (Priority: P1)

Las compras de 002 generan cuentas por pagar; el personal registra los pagos y las retenciones aplicadas y consulta la antigüedad.

**Why this priority**: §4.10 y §7 (retenciones en la fuente).

**Independent Test**: Registrar una compra en 002 y verificar la CxP, luego un pago con retención.

**Acceptance Scenarios**:

1. **Given** una orden de compra de 002 con condiciones de pago, **When** se consulta CxP, **Then** aparece por el importe a pagar.
2. **Given** una CxP, **When** se registra un pago con retención en la fuente, **Then** el saldo y la retención quedan registrados.

---

### User Story 5 - Gastos operativos por sucursal y categoría, pagados o por pagar (Priority: P1)

El personal autorizado (Gerencia General) registra manualmente gastos atribuidos a una sucursal y a una categoría (local/operativos, personal, otros, mermas y pérdidas), con documento de soporte. Ejemplos: arriendo, luz, **agua**, **internet/wifi**, teléfono, seguridad. Al registrar el gasto se indica si está **"pagado ahora"** (genera un movimiento de caja/banco) o **"por pagar"** (genera una cuenta por pagar). La CxP puede ser a un proveedor registrado (002) o a un **beneficiario/acreedor de servicios** libre (ej. "EMAPA", "CNT").

**Why this priority**: §4.10.1: la categorización por sucursal y tipo es indispensable para la rentabilidad real; §4.10: control de caja y de cuentas por pagar.

**Independent Test**: Registrar un gasto de agua "por pagar" a un beneficiario y verificar la CxP y su aging; registrar un gasto de wifi "pagado ahora" y verificar el movimiento de caja/banco.

**Acceptance Scenarios**:

1. **Given** el catálogo de categorías (001), **When** se registra un gasto de arriendo en la sucursal A, **Then** queda atribuido a A y a la categoría "local/operativos" y genera su asiento.
2. **Given** un gasto sin categoría, **When** se intenta guardar, **Then** el sistema exige elegir una del catálogo.
3. **Given** un gasto de agua marcado "por pagar" con beneficiario "EMAPA", **When** se guarda, **Then** aparece en el subledger de cuentas por pagar por su importe y entra en el aging; luego admite pagos totales/parciales.
4. **Given** un gasto de wifi marcado "pagado ahora" con medio "transferencia", **When** se guarda, **Then** genera el movimiento de banco y el asiento correspondiente, sin CxP.
5. **Given** un usuario Gerente de Sucursal, **When** intenta registrar un gasto, **Then** recibe 403 (solo puede consultar).

---

### User Story 5b - Gastos recurrentes (Priority: P2)

Gerencia General define gastos recurrentes (categoría, beneficiario/proveedor, monto estimado, frecuencia — mensual, bimestral, trimestral). En cada ciclo el sistema crea el gasto en estado borrador para que Gerencia ajuste el monto real y lo confirme.

**Why this priority**: agua, wifi, arriendo y teléfono se repiten cada periodo; automatizar el recordatorio evita olvidos y da previsibilidad de caja.

**Independent Test**: Configurar un gasto recurrente mensual y verificar que se genera el borrador al llegar el ciclo; pausarlo y verificar que deja de generar.

**Acceptance Scenarios**:

1. **Given** un gasto recurrente mensual de "internet", **When** llega la fecha del ciclo, **Then** se crea un gasto en borrador con el monto estimado, pendiente de confirmación.
2. **Given** un gasto recurrente, **When** se pausa o cancela, **Then** deja de generar borradores.
3. **Given** un borrador generado, **When** Gerencia ajusta el monto real y lo confirma como "por pagar", **Then** genera su CxP como cualquier gasto.

---

### User Story 6 - Asientos automáticos y rentabilidad por sucursal (Priority: P2)

Cada hecho de negocio (venta, compra/pago, gasto, merma) genera su asiento según reglas parametrizadas; el sistema produce la rentabilidad neta por sucursal.

**Why this priority**: §4.10 y §5: los reportes de margen dependen de que los costos y gastos estén asentados.

**Independent Test**: Confirmar una venta y verificar el asiento generado; consultar la rentabilidad de la sucursal.

**Acceptance Scenarios**:

1. **Given** una regla de asiento para ventas, **When** 009 confirma una venta, **Then** se genera el asiento correspondiente.
2. **Given** ingresos, costos y gastos de una sucursal, **When** se consulta su rentabilidad neta, **Then** descuenta los gastos operativos, no solo el margen bruto.

### Edge Cases

- ¿Qué pasa con un cobro parcial y luego un cheque protestado sobre esa CxC?
- ¿Qué pasa si la retención es mayor que el pago?
- ¿Qué pasa al cambiar la categoría de un gasto ya registrado?
- ¿Qué pasa si se cambia un gasto de "pagado ahora" a "por pagar" (o viceversa) después de guardarlo?
- ¿Qué pasa con un gasto recurrente cuyo beneficiario se inactiva, o con un borrador no confirmado del ciclo anterior?
- ¿Qué pasa con un ajuste sobre un periodo contable ya cerrado?
- ¿Qué pasa si se registra un asiento con fecha en un periodo cerrado?
- ¿Qué pasa con la caja si dos usuarios la cierran a la vez?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mantener un plan de cuentas compatible con NIIF para PYMES. [Esp. §7, §4.10]
- **FR-002**: El sistema DEBE registrar el libro diario con asientos de debe/haber balanceados; no se guarda un asiento descuadrado. [Esp. §4.10]
- **FR-003**: El sistema DEBE derivar el libro mayor y el balance de comprobación del libro diario. [Esp. §4.10]
- **FR-004**: El sistema DEBE producir el estado de resultados (ingresos por ventas + servicios − costos − gastos). [Esp. §4.10]
- **FR-005**: El sistema DEBE gestionar caja y bancos por sucursal, con apertura y cierre de caja, movimientos y arqueo con registro de diferencias. [Esp. §4.9, §4.10; Const. Ppio XI]
- **FR-006**: El sistema DEBE registrar cheques emitidos y recibidos (estos últimos originados como medio de pago en 008 y 009) con su estado (en cartera, depositado, cobrado, protestado/devuelto). [Esp. §4.10]
- **FR-007**: Un cheque recibido que se protesta DEBE revertir el cobro asociado y reactivar la cuenta por cobrar. [Esp. §4.10 — regla de integridad derivada]
- **FR-008**: El sistema DEBE mantener el subledger de cuentas por cobrar alimentado desde las ventas a crédito (009) y las órdenes de trabajo entregadas a crédito con autorización (008), con cobros totales/parciales y estado. [Esp. §4.10]
- **FR-009**: El sistema DEBE mantener el subledger de cuentas por pagar alimentado desde (a) las compras a proveedores (002) y (b) los **gastos registrados como "por pagar"** (servicios y otros), con pagos totales/parciales y retenciones en la fuente aplicadas. Una CxP tiene como contraparte un proveedor registrado o un **beneficiario/acreedor de servicios** libre. [Esp. §4.10, §4.10.1, §7]
- **FR-009a**: El sistema DEBE gestionar un catálogo de **beneficiarios/acreedores de servicios** (nombre, identificación opcional, tipo de servicio) para las CxP que no corresponden a un proveedor de mercadería. [Esp. §4.10.1 — derivado]
- **FR-010**: El sistema DEBE calcular la antigüedad (aging) de cuentas por cobrar y por pagar. [Esp. §4.11.2]
- **FR-011**: El sistema DEBE ofrecer el reporte operativo "cuentas por cobrar pendientes". [Esp. §4.11.1]
- **FR-012**: El sistema DEBE permitir registrar manualmente gastos operativos por sucursal y por categoría (catálogo de 001: local/operativos, personal, otros, mermas y pérdidas), con documento de soporte. Cada gasto se marca "pagado ahora" (⇒ movimiento de caja/banco) o "por pagar" (⇒ cuenta por pagar, FR-009). Ejemplos: arriendo, luz, agua, internet/wifi, teléfono. [Esp. §4.10.1, §9.3, §4.10]
- **FR-012a**: El sistema DEBE permitir definir **gastos recurrentes** (categoría, beneficiario/proveedor, monto estimado, frecuencia mensual/bimestral/trimestral) que generan un gasto en borrador cada ciclo para revisión y confirmación por Gerencia General; un recurrente se puede pausar o cancelar. [Esp. §4.10.1 — derivado; necesidad del negocio]
- **FR-012b**: Todo gasto generado (asiento automático) y toda CxP originada en un gasto quedan trazados al gasto de origen. [Esp. §4.10, §6]
- **FR-013**: El costo de las mermas (011) DEBE registrarse como gasto/pérdida extraordinaria, separado de los gastos operativos regulares. [Esp. §4.12, §4.10.1]
- **FR-014**: El sistema DEBE permitir definir reglas de asiento automático para ventas, compras/pagos, gastos (pagados y por pagar) y mermas. [Esp. §4.10, §5]
- **FR-015**: El sistema DEBE producir la rentabilidad neta por sucursal (ingresos − costos − gastos operativos) como reporte operativo. [Esp. §4.11.2 — versión operativa]
- **FR-016**: El sistema DEBE soportar el cierre de periodo contable; tras el cierre, los ajustes requieren un asiento de ajuste fechado y auditado, no la edición del original. Un cambio de parámetro configurable NO recalcula asientos de periodos cerrados (conservan su valor histórico); sí afecta lo posterior (Const. "Parámetros configurables — recálculo en cascada"). [Esp. §6, §7, §9.4]
- **FR-017**: El scoping por sucursal (001) DEBE aplicarse: un gerente de sucursal ve su contabilidad; Gerencia General ve el consolidado. [Esp. §3, §4.9, §6]
- **FR-018**: El módulo DEBE declarar sus permisos bajo "Contable": Vendedor y Técnico sin acceso, Gerente de Sucursal solo Consultar, Gerencia General CRUD. El registro y la confirmación de gastos, gastos recurrentes y pagos de CxP requieren rol Gerencia General. [Esp. §3.1; Const. Ppio IV]
- **FR-019**: Todo asiento, cobro, pago y gasto DEBE auditarse con actor y timestamp. [Esp. §6]
- **FR-020**: Los listados DEBEN tener filtros reactivos y paginación; los reportes se exportan en CSV/Excel/PDF (solo CSV si superan ~5 000 filas). [Const. Ppio XI]
- **FR-021**: El modelo del libro de cuentas DEBE ser compatible con la incorporación futura de facturación electrónica y declaraciones ante el SRI, sin rediseño. [Esp. §7]
- **FR-022**: El sistema NO implementa integración real con el SRI ni motor de forecasting en esta fase. [Const. "Stack"; §7]

### Key Entities *(include if feature involves data)*

- **CuentaContable**: código, nombre, tipo, plan compatible NIIF PYMES.
- **Asiento** / **LíneaAsiento**: fecha, glosa, origen (manual / automático desde venta, compra, gasto, merma), líneas de debe/haber.
- **Caja** (por sucursal) / **SesiónCaja**: apertura, cierre, efectivo esperado, efectivo contado, diferencia.
- **MovimientoCaja**: sesión, tipo, monto, referencia.
- **Cheque**: tipo (emitido/recibido), estado, monto, fecha, banco.
- **CuentaPorCobrar** / **CobroCxC**: cliente, venta origen, saldo, aging.
- **CuentaPorPagar** / **PagoCxP** / **RetenciónFuente**: origen (compra de 002 o gasto), proveedor o beneficiario, saldo, aging.
- **Beneficiario**: acreedor de servicios (nombre, identificación opcional, tipo) para CxP que no son de proveedores de mercadería.
- **Gasto**: sucursal, categoría, beneficiario/proveedor, monto, fecha, estado de pago (`pagado` / `por_pagar`), documento de soporte, gasto recurrente de origen (si aplica), asiento generado.
- **GastoRecurrente**: categoría, beneficiario/proveedor, monto estimado, frecuencia (mensual/bimestral/trimestral), próxima generación, estado (activo/pausado/cancelado).
- **ReglaAsientoAutomático**: hecho de negocio, cuentas debe/haber.
- **PeriodoContable**: rango, estado (abierto/cerrado).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Registrar un gasto operativo con categoría y soporte toma menos de 2 minutos y queda atribuido a su sucursal.
- **SC-001a**: Un gasto de servicio marcado "por pagar" (agua, wifi) aparece en el subledger de CxP por su importe exacto, entra en el aging y admite pagos parciales; uno marcado "pagado ahora" genera el movimiento de caja/banco sin CxP.
- **SC-001b**: Un gasto recurrente activo genera un gasto en borrador en cada ciclo; pausado, no genera.
- **SC-002**: El 100% de las ventas a crédito de 009 aparece como CxC por el saldo exacto y su cobro la salda.
- **SC-003**: El balance de comprobación cuadra (Σ debe = Σ haber) en todo momento.
- **SC-004**: El aging de CxC/CxP clasifica correctamente por tramos de días sobre casos de prueba.
- **SC-005**: El cierre de caja registra la diferencia entre el efectivo esperado y el contado.
- **SC-006**: Un cheque protestado revierte el cobro y reactiva la CxC.
- **SC-007**: La rentabilidad neta por sucursal descuenta los gastos operativos de esa sucursal, no solo el margen bruto.
- **SC-008**: Vendedores y técnicos reciben 403 en todos los endpoints contables.

## Assumptions

- 001, 002 y 009 están implementadas.
- El posteo del costo de las mermas lo dispara 011 llamando a la API de asientos de 010; hasta entonces la regla de asiento de merma queda definida sin datos.
- Los reportes analíticos comparados (rentabilidad por sucursal entre periodos, aging analítico) son 013.
- La integración con el SRI y el forecasting están fuera de alcance (Const. "Stack"; §7 pendiente).
- El nivel de detalle es el de §4.10 ("sin llegar a un ERP contable completo"); se prioriza trazabilidad y cálculo de márgenes reales.
- La nómina se registra como gasto de categoría "personal"; su cálculo queda fuera de alcance (solo el bono de técnicos, calculado en 005, se refleja como costo).
- El catálogo `medio_pago` proviene de 001; el registro de pagos multimedios contra un documento facturable es el helper compartido introducido en 008.
- Las cuentas por cobrar se originan tanto en ventas a crédito (009) como en órdenes de trabajo entregadas a crédito con autorización (008).
- Las cuentas por pagar se originan en compras a proveedores (002) y en gastos marcados "por pagar" (servicios y otros); estos últimos pueden tener como contraparte un proveedor registrado o un beneficiario libre.
- Los gastos recurrentes usan un scheduler in-proceso (igual patrón que las compras programadas de 002); NO se añade Airflow ni servicios al `docker-compose.yml` (Const. "Flujo de Trabajo").
- El registro manual de gastos, gastos recurrentes y pagos de CxP es exclusivo del rol Gerencia General; el Gerente de Sucursal solo consulta.
