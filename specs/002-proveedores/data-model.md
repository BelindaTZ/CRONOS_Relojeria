# Data Model: Proveedores y Órdenes de Compra

**Feature**: `002-proveedores` | **Phase**: 1 | **Date**: 2026-09-10

Migraciones `0007_*`. Reutiliza `sucursal`, `usuario`, `registro_auditoria` (001).

## `proveedor`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| razon_social | varchar(200) | no nula |
| nombre_comercial | varchar(200) | opcional |
| contacto_nombre | varchar(160) | |
| telefono | varchar(40) | |
| email | varchar(160) | |
| ruc_nit | varchar(20) | único |
| certificacion_autorizada | boolean | default false |
| condiciones_pago | varchar(255) | texto libre corto (descriptivo) |
| plazo_entrega_dias | int | pactado por defecto |
| estado | varchar(12) | `activo` \| `inactivo` |
| creado_en, actualizado_en | timestamptz | |

- **Tipos** (N—M): `proveedor_tipo` (`proveedor_id`, `tipo` ∈ {relojes, piezas_originales, piezas_no_originales, lubricantes, herramientas}).
- **Edición con historial**: campos `razon_social`, `ruc_nit` solo editables con rol elevado; el resto por `require_perm("proveedores","editar")`. Toda edición ⇒ auditoría.
- **Baja**: `activo` → `inactivo` (nunca DELETE si tiene historial).

## `proveedor_documento`
`id`, `proveedor_id` FK, `tipo` (`certificado` | `ruc` | `contrato` | `otro`), `objeto` (clave en bucket `documentos`), `nombre`, `subido_por`, `creado_en`.

## `calificacion_proveedor`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| proveedor_id | bigint FK | |
| nota_plazos | numeric(2,1) | 1.0–5.0, **derivada** del indicador de cumplimiento |
| nota_calidad | numeric(2,1) | 1.0–5.0, manual |
| nota_soporte | numeric(2,1) | 1.0–5.0, manual |
| nota_agregada | numeric(2,1) | promedio |
| autor_usuario_id | bigint FK | |
| creado_en | timestamptz | historial por inserción |

- **Indicador de plazos** (calculado, no persistido o materializado en `proveedor.indicador_plazos_dias`): promedio de `desfase_dias` de las últimas N recepciones.

## `orden_compra`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| proveedor_id | bigint FK | |
| sucursal_destino_id | bigint FK → sucursal | |
| tipo | varchar(12) | `puntual` \| `programada` |
| compra_programada_id | bigint FK | null si `puntual` |
| estado | varchar(14) | `borrador` \| `emitida` \| `parcial` \| `recibida` \| `cancelada` |
| fecha_emision | date | |
| fecha_confirmacion | date | fecha en que Gerencia confirma (0007) |
| confirmada_por | bigint FK → usuario | usuario que confirma la orden |
| fecha_pactada | date | |
| importe_a_pagar | numeric(14,2) | |
| condiciones_pago | varchar(255) | |
| retencion_aplicable | jsonb | `{tipo, valor}` opcional |
| creado_por | bigint FK | |

**Transiciones**: `borrador → emitida → (parcial) → recibida`; cualquiera excepto `recibida` → `cancelada`. Cancelar tras recepción parcial conserva lo recibido.

## `linea_orden_compra`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| orden_compra_id | bigint FK | |
| item_tipo | varchar(8) | `reloj` | `pieza` |
| item_ref | varchar(80) | referencia o código |
| descripcion | varchar(255) | especificaciones / descripción |
| cantidad | int | >0 |
| costo_unitario | numeric(14,2) | **nullable** (costo estimado; el proveedor lo confirma al recibir, 0013) |
| marca | varchar(120) | nullable (reloj, 0013) |
| calibre_codigo | varchar(60) | nullable (reloj, 0013) |
| anio | int | nullable (reloj, 0013) |
| numero_serie | varchar(80) | nullable (reloj específico opcional, 0014) |
| pieza_id | bigint FK → pieza | nullable (elegida de catálogo, 0014) |
| pieza_tipo | varchar(24) | nullable (pieza nueva: `original` | `no_original_equivalente`, 0014) |
| unidad_medida | varchar(16) | nullable (unidad, ml, g..., 0014) |
| marca_compatible | varchar(255) | nullable (marcas compatibles, 0014) |
| observaciones | varchar(255) | nullable (nota libre por línea, 0015) |

## `recepcion_compra`
`id`, `orden_compra_id` FK, `fecha_real` date, `responsable_usuario_id` FK, `desfase_dias` int nullable, `numero_factura` varchar(60) nullable (0014), `numero_guia` varchar(60) nullable (0014), `creado_en`.

## `recepcion_linea`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| recepcion_compra_id | bigint FK | |
| linea_orden_compra_id | bigint FK | |
| cantidad_recibida | int | >0 |
| lote | varchar(60) | obligatorio si el ítem es perecedero (003) |
| fecha_caducidad | date | obligatoria si el ítem es perecedero |
| sobre_entrega | boolean | true si `cantidad_recibida` > pendiente de la línea |

- **Efecto**: al confirmar la recepción, se notifica a 003 para dar de alta las unidades (relojes) o sumar stock (piezas) y crear `lote_pieza` si aplica. `desfase_dias = fecha_real − orden.fecha_pactada` alimenta el indicador de plazos.

## `compra_programada`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| proveedor_id | bigint FK | |
| sucursal_destino_id | bigint FK | |
| frecuencia | varchar(12) | `semanal` \| `mensual` \| `trimestral` |
| proxima_generacion | timestamptz | |
| estado | varchar(10) | `activa` \| `pausada` \| `cancelada` |
| plantilla_lineas | jsonb | lista de {item_tipo, item_ref, cantidad, costo_unitario} |

- **Regla**: cuando `estado = activa` y `proxima_generacion ≤ now()`, el scheduler crea una `orden_compra` (`tipo = programada`, `estado = borrador`) y avanza `proxima_generacion` según `frecuencia`.

## Reglas de negocio (validación en backend)

1. `orden_compra.estado` no editable directamente; solo por transiciones.
2. Corrección de una compra `recibida` o de sus recepciones ⇒ rol elevado + `motivo` + auditoría.
3. Recepción de ítem perecedero ⇒ `lote` y `fecha_caducidad` obligatorios.
4. Proveedor con órdenes ⇒ no DELETE; solo `inactivo`.
5. Calificación: `nota_plazos` no se edita a mano (derivada); `nota_calidad` y `nota_soporte` sí.

---

## Cambios v2 — aprobados por el usuario (2026-09-10)

Migración `0008_proveedores_v2`.

1. **`orden_compra.estado`** añade **`confirmada`**: `borrador → emitida → confirmada → parcial → recibida` (o `cancelada` desde cualquiera excepto `recibida`). `confirmada` = un rol elevado (Gerencia General / Gerente de Sucursal) registró que el proveedor **aceptó** el pedido según lo acordado por otro canal. **La recepción solo procede desde `confirmada`/`parcial`.** Campos nuevos: `fecha_confirmacion`, `confirmada_por` (FK usuario).
2. **`condicion_pago`** (catálogo maestro editable en `configuracion`): `id`, `nombre` único, `dias_credito`, `activo`. Sembrado: Contado / 15 / 30 / 45 / 60 días / 50% anticipo. `proveedor.condicion_pago_id` FK (reemplaza el texto libre `proveedor.condiciones_pago`, que queda como campo legado sin uso). `orden_compra.condiciones_pago` sigue siendo un **snapshot de texto** copiado al crear la orden.
3. **`medio_pago`**: se retira el CHECK de claves fijas. Se pueden **agregar** medios nuevos (sin pasarela en línea, sigue prohibida) e **inactivar** (`activo=false`) los que estén en uso; nunca DELETE.
4. **Regla de cancelación de OC**: bloqueada si `now >= fecha_pactada − oc_horas_min_cancelacion` (parámetro configurable, def. 24 h). Exige `motivo`. Al cancelar se envía correo al proveedor (plantilla `cancelacion_orden`).
5. **Alta de usuario (001)**: la contraseña temporal la **genera el sistema** (`must_change_password=true`), se muestra una vez a quien crea y se envía por correo (`usuario_bienvenida`). El endpoint ya no acepta `password`.

## Cambios por feedback del usuario (2026-09-10, migración `0013`)

- **`linea_orden_compra`**: campos estructurados para el pedido de un reloj —
  `marca` (varchar), `calibre_codigo` (varchar), `anio` (int). `item_ref` es la
  referencia/modelo (reloj) o el código (pieza); `descripcion` queda para
  especificaciones y notas ("esfera azul, para cliente X"). `costo_unitario`
  pasa a **NULLABLE**: en el pedido es un estimado opcional — el costo real lo
  informa el proveedor **al recibir**.
- **`recepcion_linea.costo_unitario`** (NUEVO, nullable): costo real por línea
  informado en la recepción. `orden_compra.importe_a_pagar` se recalcula con los
  costos reales cuando existen, sino con los estimados.
- **`proveedor_marca_autorizada`** (NUEVA, N—M `proveedor` ↔ `marca_reloj`):
  cuando `proveedor.certificacion_autorizada` es true, las marcas para las que el
  proveedor es distribuidor oficial. Al desmarcar la certificación se limpian.
- **`proveedor.plazo_entrega_dias`**: se conserva la columna (legado) pero **ya no
  se pide en el alta** — el plazo relevante es `orden_compra.fecha_pactada`.
- El flujo de recepción ficha cada unidad de reloj recibida en el mismo modal
  (asistente de 2 pasos), heredando marca/calibre/año/costo de la línea.

## Cambios por feedback del usuario (2026-09-10, 3ª ronda — migraciones `0014`, `0015`)

- **`linea_orden_compra`** (`0014`): `numero_serie` (reloj, opcional al pedir),
  `pieza_id` (FK `pieza` ON DELETE SET NULL — elegir del catálogo, hereda
  tipo/unidad/marca-compatible/perecedera), y para piezas nuevas `pieza_tipo`,
  `unidad_medida`, `marca_compatible`.
- **`linea_orden_compra.observaciones`** (`0015`, nullable): nota libre del pedido,
  independiente de `descripcion`. Para relojes `descripcion` = observaciones; para
  una pieza nueva `descripcion` = nombre/descripción de la pieza (se usa como
  nombre en el catálogo al recibir) y `observaciones` = nota libre.
- **`recepcion_compra`** (`0014`): `numero_factura`, `numero_guia` del proveedor,
  capturados en el paso 1 del asistente de recepción. `_orden_out` los expone
  (última recepción registrada).
- **`pieza`** (`0014`): `unidad_medida` (varchar, server_default `unidad`),
  `marca_compatible` (varchar). `piezas.buscar_o_crear_por_codigo` /
  `recibir_de_compra` los reciben de la línea de compra al dar de alta una pieza
  nueva.
- **Último precio conocido**: `GET /ordenes-compra/ultimo-precio` → `{costo, fecha,
  fuente}` (`recepcion` = costo real ya pagado, `orden` = estimado de una OC
  previa). El precio en la OC siempre es opcional.
- **Producto 100% nuevo para la tienda**: no se pre-registra — se pide como "pieza
  nueva" (o como línea de reloj) y la recepción lo da de alta. La unidad física de
  un reloj nace al fichar la recepción, nunca antes.


## Ajustes en implementación y migraciones reales (2026-09-10)

- **`0007_proveedores` / `0008_proveedores_v2`**: tablas base de proveedores, órdenes y recepciones.
- **`0013_oc_relojes_y_costo_al_recibir`**: `linea_orden_compra` gana `marca`, `calibre_codigo`, `anio`, `costo_unitario` nullable; `recepcion_linea` gana `costo_unitario` real; creación de tabla `proveedor_marca_autorizada`.
- **`0014_oc_lineas_detalle_y_factura`**: `linea_orden_compra` gana `numero_serie`, `pieza_id`, `pieza_tipo`, `unidad_medida`, `marca_compatible`; `recepcion_compra` gana `numero_factura` y `numero_guia`.
- **`0015_linea_oc_observaciones`**: `linea_orden_compra` gana columna `observaciones`.
- **`0027_flujo_principal`**: `orden_compra` gana flag `urgente`.
