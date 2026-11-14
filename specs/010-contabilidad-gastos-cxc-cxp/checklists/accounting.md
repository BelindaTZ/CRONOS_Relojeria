# Accounting Integrity Checklist: Contabilidad (010)

**Purpose**: Checklist adicional de integridad contable — valida que los requisitos garantizan libros correctos, cuadrados y auditables (Const. Ppio IX; §7 NIIF PYMES).
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Partida doble e integridad del diario

- [x] ACC001 ¿Se especifica que ningún asiento se guarda si `Σ debe ≠ Σ haber`? [Completeness, Spec §FR-002]
- [x] ACC002 ¿Se especifica que el libro mayor y el balance se derivan del diario (no se editan aparte)? [Consistency, research D2]
- [x] ACC003 ¿Se especifica que el balance de comprobación debe cumplir `Σ debe total = Σ haber total`? [Measurability, Spec §SC-003]
- [x] ACC004 ¿Se especifica el manejo de decimales/redondeo en montos? [Gap]

## Asientos automáticos

- [x] ACC005 ¿Cada evento de negocio (venta, compra/pago, gasto pagado, gasto por pagar, merma, cobro) tiene su regla de asiento? [Coverage, research D7, D11]
- [x] ACC005a ¿El asiento de un gasto "pagado ahora" acredita caja/bancos y el de un "por pagar" acredita cuentas por pagar? [Clarity, research D11]
- [x] ACC005b ¿Un gasto en borrador (de un recurrente) NO genera asiento ni CxP hasta confirmarse? [Consistency, Data-model regla 6]
- [x] ACC006 ¿Se especifica qué ocurre si un evento llega sin regla configurada? [Gap]
- [x] ACC007 ¿La merma imputa a una cuenta de pérdida extraordinaria distinta de gastos operativos? [Clarity, Spec §FR-013]
- [x] ACC008 ¿Se especifica la reversión contable ante una anulación de venta (009) o cancelación? [Gap, Spec §FR-014]

## Cierre de periodo

- [x] ACC009 ¿Tras el cierre, el original es inmutable y el ajuste es un asiento nuevo fechado y vinculado? [Completeness, Spec §FR-016]
- [x] ACC010 ¿Un cambio de parámetro configurable NO altera asientos de periodos cerrados? [Consistency, Const. "Parámetros configurables"]
- [x] ACC011 ¿Se especifica quién puede cerrar/reabrir un periodo? [Gap]

## Caja, bancos y cheques

- [x] ACC012 ¿El arqueo registra la diferencia entre efectivo esperado y contado? [Completeness, Spec §FR-005]
- [x] ACC013 ¿Un movimiento con fecha de sesión cerrada se rechaza o exige ajuste? [Clarity, research D3]
- [x] ACC014 ¿El protesto de cheque revierte el cobro y reactiva la CxC de forma atómica? [Consistency, Spec §FR-007]

## CxC / CxP

- [x] ACC015 ¿El saldo de cada cuenta se reduce exactamente con cada cobro/pago (parcial y total)? [Measurability, Spec §FR-008, §FR-009]
- [x] ACC015a ¿La CxP originada en un gasto y la originada en una compra (002) comparten el mismo aging y flujo de pagos? [Consistency, Data-model cuenta_por_pagar]
- [x] ACC015b ¿La `cuenta_por_pagar` garantiza exactamente una contraparte (proveedor xor beneficiario) y un origen (orden_compra xor gasto)? [Completeness, Data-model regla 11]
- [x] ACC016 ¿El aging clasifica por tramos definidos y con una fecha de corte parametrizable? [Clarity, research D5]
- [x] ACC017 ¿Las retenciones se registran como campos sin cálculo fiscal (compatibilidad SRI futura)? [Clarity, Spec §FR-009, §FR-021]

## Compatibilidad legal

- [x] ACC018 ¿El modelo del libro de cuentas admite incorporar facturación electrónica sin rediseño? [Completeness, Spec §FR-021]
- [x] ACC019 ¿Se documenta explícitamente que no hay transmisión al SRI en esta fase? [Assumption, Spec §FR-022]
