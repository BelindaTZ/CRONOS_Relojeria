# Research: Servicio Técnico y Lubricación

**Feature**: `008-servicio-tecnico-lubricacion` | **Phase**: 0 | **Date**: 2026-09-10

Sin `NEEDS CLARIFICATION` (fecha estimada post-diagnóstico, presupuesto/piezas, cobro al retiro y costeo por tarifa horaria fueron decisiones del negocio).

## D1 — Ciclo de estados de la OT

- **Decisión**: `recibido → en_diagnostico → presupuesto → en_reparacion → listo → entregado`. Reglas de guarda:
  - `en_reparacion` solo si hay `presupuesto` en estado `aprobado`.
  - `fecha_estimada_entrega` se registra al aprobar el presupuesto (no en `recibido`).
  - `entregado` solo si `saldo(OT) == 0` **o** existe una entrega a crédito autorizada por Gerencia General (genera CxC).
  - `listo` = terminado sin pagar ni retirar.
- **Rationale**: §4.7 + decisiones del negocio.

## D2 — Reloj adquirido en la tienda

- **Decisión**: al abrir la OT se verifica que el `numero_serie` existe en `reloj` con al menos un `evento_serie` de `venta` (o marca "vendido antes del sistema" con override autorizado). Si no consta → advertencia + requiere autorización.
- **Rationale**: §2.1.

## D3 — Costeo del servicio

- **Decisión**: `costo_interno = costo_mano_obra + costo_piezas + costo_insumos`
  - `costo_mano_obra` = `POST /_internal/costeo/costo-mo-ot` (005) con `horas` registradas por el técnico; fallback `tiempo_estimado(tipo_reparacion)` (parámetro §9.2).
  - `costo_piezas` = Σ (pieza.costo_adquisicion × cantidad); descuenta stock (003) al confirmar.
  - `costo_insumos` = Σ consumo de lubricación valorado a costo del lote (003).
  - `precio_sugerido = costo_interno × (1 + margen_objetivo)`; el margen objetivo es parámetro (global / tipo de servicio / sucursal).
  - `margen_real = precio_cobrado − costo_interno` (calculado, nunca al cliente).
  - Al cerrar el periodo (005), se suma `bono_ot` al `costo_mano_obra` en los reportes de margen.
- **Rationale**: §5, §4.7.

## D4 — Presupuesto y elección de piezas

- **Decisión**: `presupuesto` (OT, precio_servicio, líneas de pieza con `opcion_original` y `opcion_no_original` + diferencia de precio, `estado` ∈ {borrador, enviado, aprobado, rechazado}). El técnico marca la `preferencia_cliente` por ítem (`original`|`no_original`|`mixto`) y registra `confirmado_por` (texto: nombre/medio) y `fecha_confirmacion`. La comunicación real es externa (WhatsApp/correo personal).
- **Rationale**: necesidad del negocio; §4.5.

## D5 — Lubricación

- **Decisión**: `ficha_lubricacion_calibre` (1—1 con `calibre` de 003) con `punto_lubricacion` (nombre, producto recomendado, notas). En la OT, `registro_lubricacion_ot` (punto, producto_recomendado, producto_usado, tecnico, fecha, `desviacion` bool). El consumo de insumos se deriva de `producto_usado` y se descuenta del stock de piezas (los productos Moebius son piezas perecederas de 003).
- **Rationale**: §4.6.

## D6 — Aviso al cliente del técnico asignado

- **Decisión**: al asignar técnico, `shared/correo.enviar("tecnico_asignado", cliente.email, {tecnico: {nombre, especialidades, certificaciones}, contacto_email})`. Plantilla administrada por 014.
- **Rationale**: necesidad del negocio; Const. Ppio XI.

## D7 — Cobro al retiro y pagos multimedios

- **Decisión**: `shared/pagos.registrar_pago(documento_tipo, documento_id, medio_pago, monto, referencia)` y `saldo(documento)`. La OT no pasa a `entregado` con `saldo > 0` salvo `autorizacion_credito` (Gerencia General) que crea la CxC (010). Cheque como medio; su ciclo (protesto) es de 010.
- **Rationale**: §4.10 + decisión del negocio ("sin pago no se lo devuelven"); Const. "Entidades compartidas".

## D8 — Documento de OT y certificado de garantía

- **Decisión**: al `entregar`, `shared/pdf` renderiza dos documentos (OT y certificado de garantía del servicio) con identidad visual, se suben a `comprobantes-venta` (privado, endpoint autenticado). No exponen costos internos.
- **Rationale**: Const. Ppio III; §4.7, §7.

## D9 — Reapertura por garantía

- **Decisión**: OT `entregado` dentro del periodo de garantía puede generar una OT `reapertura` con `ot_original_id`; hereda el reloj y el cliente; su cobro se decide por caso (garantía cubre o no).
- **Rationale**: §4.7 ("Garantía del servicio").

## D10 — Merma por daño en servicio

- **Decisión**: `POST /ordenes-trabajo/{id}/reportar-dano` crea el payload para `POST /mermas` (011, causa `dano_servicio`) vinculado a la OT y al técnico, sin sanción automática.
- **Rationale**: §4.12.

## D11 — Informe de servicios/arreglos

- **Decisión**: `GET /informe-servicios?cliente_id=&tecnico_id=&reloj=&desde=&hasta=` con columnas: cliente, fecha, reloj (serie), trabajo realizado, repuestos usados, precio del arreglo. Versión operativa; el analítico es 013.
- **Rationale**: necesidad del negocio; §4.11.1; §6.
