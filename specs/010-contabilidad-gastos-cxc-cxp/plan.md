# Implementation Plan: Contabilidad, Gastos, CxC y CxP

**Branch**: `010-contabilidad-gastos-cxc-cxp` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Contabilidad básica con trazabilidad suficiente (§4.10): **plan de cuentas** compatible NIIF PYMES, **libro diario** (asientos balanceados), libro mayor y balance de comprobación derivados, **estado de resultados**, **caja y bancos por sucursal** (apertura/cierre/arqueo), **cheques** (emitidos y recibidos, con protesto), **subledger de CxC** (de ventas/OT a crédito de 009/008) y **de CxP** (de compras de 002) con **aging**, **registro de gastos operativos** por sucursal y categoría (§4.10.1), **reglas de asiento automático** desde los hechos de negocio (venta, compra/pago, gasto, merma), **rentabilidad neta por sucursal**, y **cierre de periodo contable** (ajustes solo por asiento nuevo). Modelo compatible con facturación electrónica futura; sin SRI ni forecasting.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic, `APScheduler` (scheduler in-proceso para gastos recurrentes — mismo patrón que 002, **sin Airflow**); `shared/guard` (scope por sucursal), `shared/auditoria`, `shared/parametros`; consume 009 (ventas, CxC), 008 (OT a crédito), 002 (compras, CxP, proveedores), 011 (mermas), 001 (`categoria_gasto`, `medio_pago`), `documentos` (bucket para soporte de gastos)

**Storage**: PostgreSQL; MinIO `documentos` (soporte de gastos)

**Testing**: `pytest` — asientos balanceados, aging (CxC y CxP de compra y de gasto), arqueo, protesto de cheque, gasto pagado/por-pagar, generación de gastos recurrentes, rentabilidad por sucursal; `vitest`

**Project Type**: Web — módulo `contabilidad`

**Performance Goals**: registrar un gasto < 2 min; balance de comprobación < 2 s

**Constraints**: asiento descuadrado nunca se guarda; periodo cerrado inmutable (ajuste = asiento nuevo); scope por sucursal; sin integración SRI; sin forecasting

**Scale/Scope**: cientos de asientos/mes, pocas sucursales

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.10, §4.10.1, §4.9, §7, §4.11.1, §4.11.2, §6, §4.12. ✅ |
| II | Asientos, cobros, pagos, gastos, sesiones de caja son registros reales. ✅ |
| III | PostgreSQL OLTP; soporte de gastos a `documentos`. ✅ |
| IV | Módulo `contable`: Vendedor/Técnico sin acceso, Gerente solo consultar, Gerencia CRUD. ✅ |
| V | Reglas de asiento, aging y cierre en backend. ✅ |
| VI | Referencia 002, 008, 009, 011, 001; no los redefine. ✅ |
| VII | "Sin llegar a un ERP contable completo"; sin SRI ni ML. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | Cobertura de asientos balanceados, aging, arqueo, protesto, rentabilidad. ✅ |
| X | Módulo `contabilidad/` con capas. ✅ |
| XI | Filtros reactivos; exportación (solo CSV si > 5 000 filas); modales. ✅ |
| XII | Pantallas con `ui-ux-pro-max`. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/contabilidad/
├── router.py     # /plan-cuentas, /asientos, /mayor, /balance, /estado-resultados,
│                 # /caja, /cheques, /cxc, /cxp, /beneficiarios, /gastos, /gastos-recurrentes,
│                 # /reglas-asiento, /periodos, /rentabilidad-sucursal
├── service.py    # libro diario, derivados, aging, cierre, rentabilidad
├── gastos.py     # registro pagado/por-pagar, confirmación de borradores, CxP de gasto
├── recurrentes.py + scheduler.py  # gastos recurrentes (genera borradores por ciclo)
├── asientos_auto.py  # motor de reglas de asiento automático
├── caja.py       # apertura/cierre/arqueo
├── repository.py
└── schemas.py

frontend/src/contabilidad/
├── components/ (PlanCuentas, LibroDiario, BalanceComprobacion, EstadoResultados, PanelCaja,
│                Cheques, AgingCxC, AgingCxP, PanelGastos, RentabilidadSucursal)
├── composables/ stores/ services/
```

**Structure Decision**: Un módulo. El motor de asiento automático (`asientos_auto.py`) escucha eventos de dominio de otras features (venta confirmada, compra pagada, gasto, merma) y produce el asiento según `regla_asiento_automatico`.

## Complexity Tracking

| Elemento | Por qué | Alternativa más simple rechazada porque |
|---|---|---|
| Motor de asiento automático | §4.10 + §5 (los reportes de margen dependen de que costos y gastos estén asentados) | Asientos 100% manuales: inviable operativamente y propenso a error |
| Cierre de periodo con inmutabilidad | §7 (NIIF) + §6 (auditoría) | Editar asientos históricos: rompe la integridad contable/legal |
| Scheduler in-proceso para gastos recurrentes | §4.10.1 (agua/wifi/arriendo mensuales) + necesidad del negocio | Registro 100% manual cada mes: el negocio pidió automatizarlo; Airflow está reservado a 012 |
| CxP con contraparte proveedor **o** beneficiario libre | §4.10 (cuentas por pagar) aplicado a servicios (agua, telecom) que no son proveedores de mercadería (002) | Forzar los servicios como proveedores de 002: el flujo de "orden de compra" no encaja con un recibo de agua |
