# Research: Clientes, Fidelización y Descuentos

**Feature**: `006-clientes-fidelizacion-descuentos` | **Phase**: 0 | **Date**: 2026-09-10

Sin `NEEDS CLARIFICATION` (exclusividad descuento/cupón, reclasificación y consumidor final fueron decisiones del negocio).

## D1 — Número de afiliado

- **Decisión**: `numero_afiliado` = secuencia con prefijo (`AF-000123`), autogenerado al alta, único, inmutable. La cédula/RUC sigue siendo el identificador legal; el número de afiliado es el de fidelización/búsqueda.
- **Rationale**: necesidad del negocio (spec Q).

## D2 — Consentimiento LOPDP

- **Decisión**: `consentimiento_datos` (aceptado boolean, fecha, version_texto). Obligatorio (`aceptado = true`) para crear el cliente. El texto versionado vive en un parámetro de 001 (`texto_consentimiento_lopdp`, versión incremental).
- **Rationale**: necesidad del negocio; §7 (marco legal ecuatoriano).

## D3 — Motor de nivel de fidelización

- **Decisión**: `regla_nivel` (nombre, criterio ∈ {monto_acumulado, frecuencia, combinacion}, `ventana_meses` (def. 12), `umbral_monto`, `umbral_frecuencia`, orden). El nivel del cliente = el nivel de mayor `orden` cuyos umbrales cumple con su histórico (compras 009 + servicios 008) en la ventana. Nivel base ("Bronce") si no cumple ninguno. Función pura `nivel.py`.
- **Rationale**: §4.8.1; configurable por Gerencia General.
- **Alternativas**: puntos acumulables tipo "millas" — más complejo; el negocio pidió monto/frecuencia.

## D4 — Recálculo del nivel

- **Decisión**: (a) al confirmarse una compra (009) o un servicio (008) ⇒ recálculo del nivel de ESE cliente; si cambia, `historial_nivel_cliente`. (b) al cambiar `regla_nivel` ⇒ job diferido que recalcula TODOS los clientes; el historial previo se conserva. Registrado como consumidor en `shared/parametros`.
- **Rationale**: §4.8.1 + decisión del negocio ("recalcula todo lo que lo usa").

## D5 — Servicio de aplicación de descuento y margen mínimo

- **Decisión**: `shared/descuentos/aplicar.py`:
  - `aplicar(item_ref, costo, precio_lista, descuento|cupon) -> { precio_final, monto_descontado, margen_resultante, decision }`
  - `decision` ∈ {`permitir`, `bloquear`, `requiere_autorizacion`} según `margen_minimo.py`, que compara `margen_resultante` contra el parámetro `margen_minimo` del ámbito (producto → marca → global).
  - `bloquear` si por debajo y no hay política de autorización; `requiere_autorizacion` si la hay: la venta/OT no se confirma sin `autorizacion_margen_minimo` (quién, cuándo, sobre qué).
  - **Exclusividad**: el servicio recibe UN descuento O UN cupón; si se pasan ambos ⇒ error 422.
- **Rationale**: §4.8.2; decisión del negocio (exclusividad).
- **Alternativas**: cálculo en el frontend — prohibido (Ppio V).

## D6 — Cupones

- **Decisión**: `cupon` (codigo único, cliente_id, tipo `porcentaje`|`monto`, valor, alcance {producto|marca|tienda}, vigencia/evento, limite_uso {una_vez|n_veces|por_cliente|global}, estado {activo|usado|vencido}). Consumo con lock sobre el cupón (uso único no aplicable dos veces, aun en concurrencia).
- **Rationale**: §4.8.2.

## D7 — Descuentos generales

- **Decisión**: `descuento` (tipo, valor, alcance, `segmento` {todos|nivel|cliente}, vigencia|evento, limite_uso). Se resuelve automáticamente el descuento aplicable a un cliente/ítem en un momento dado (el de mayor beneficio si hay varios, salvo regla en contra).
- **Rationale**: §4.8.2.

## D8 — Reportes operativos

- **Decisión**: `clientes por nivel` (distribución), `mejores clientes` (Σ compras + servicios, top N), `historial de cliente` (compras, servicios, citas). El analítico (efectividad de fidelización, comparativos) es 013.
- **Rationale**: §4.8.1, §4.11.1, §4.11.2.

## D9 — Consumidor final (para 009)

- **Decisión**: 006 define un "cliente genérico consumidor final" (una fila especial, sin datos personales, sin fidelización) que 009 usa solo para piezas sueltas bajo el parámetro `monto_max_consumidor_final`. No se le calcula nivel ni se le emiten cupones.
- **Rationale**: decisión del negocio.

## D10 — Clientes en riesgo de abandono (ampliación 2026-09-10, confirmada por el usuario)

- **Decisión**: reporte operativo (no analítico — el comparativo entre periodos es 013). Función pura `clientes/riesgo.py::analizar(transacciones, *, hoy, piso_dias, factor_cadencia, min_transacciones, ventana_meses)`:
  - filtra las transacciones del cliente a la ventana (`churn_ventana_analisis_meses`, def. 24);
  - exige `>= churn_min_transacciones` (def. 3) para tener patrón;
  - `cadencia = mediana` de los intervalos (días) entre transacciones consecutivas;
  - `silencio = hoy − última transacción`; **en riesgo** si `silencio >= churn_piso_dias` (def. 90) **y** `silencio >= churn_factor_cadencia × cadencia` (def. 2,0);
  - `severidad = "critico"` si `ratio (silencio/cadencia) >= 2 × factor`, si no `"atencion"`.
- **Alcance**: solo niveles **no base** (Plata/Oro) — un cliente Bronce de una sola compra no tiene patrón ni justifica un cupón de incentivo (decisión del usuario).
- **Acción**: `POST /cupones/reactivacion` emite un cupón puntual de uso único (`REACT-<afiliado>`, vigencia 60 días por defecto) — el reporte enlaza a esta acción (Ppio XI).
- **Parámetros** (§9, editables por Gerencia): `churn_piso_dias`, `churn_factor_cadencia`, `churn_min_transacciones`, `churn_ventana_analisis_meses`.
- **Rationale**: §4.8.2 ("cupón de reactivación para clientes inactivos"), §4.11.1 (reporte operativo). El envío del cupón por correo es 014.

## D11 — Sucursal de la transacción

- **Decisión**: `TransaccionCliente` (DTO que 008/009 aportan) gana `sucursal_id`; el `historial_cliente` lo muestra (resuelve el nombre vía `shared.models.Sucursal`). Sin columna nueva en 006 — el dato vive en la venta/OT de 008/009.
- **Rationale**: §4.9 (operación multi-sucursal); necesidad del negocio (saber dónde compró cada cliente).
