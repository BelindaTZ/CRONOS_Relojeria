# Data Model: Inventario de Relojes y Piezas

**Feature**: `003-inventario-relojes-piezas` | **Phase**: 1 | **Date**: 2026-09-10

Migraciones `0008_*`. Reutiliza `sucursal`, `proveedor` (002), `usuario`, `parametro_configuracion`, `registro_auditoria` (001).

## `calibre`
`id`, `codigo` varchar(60) único, `marca` varchar(80), `descripcion` varchar(255). (008 añade `ficha_lubricacion_calibre`.)

## `reloj` (unidad física)
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| numero_serie | varchar(80) | **único**, no nulo |
| marca | varchar(80) | no nula |
| referencia | varchar(120) | no nula |
| calibre_id | bigint FK → calibre | nullable |
| anio_fabricacion | int | nullable |
| material_caja | varchar(120) | |
| material_brazalete | varchar(120) | |
| color_esfera | varchar(80) | |
| tipo_cristal | varchar(40) | `zafiro` \| `mineral` \| `acrilico` \| `otro` |
| resistencia_agua | varchar(40) | |
| estado_producto | varchar(10) | `nuevo` \| `usado` |
| costo_adquisicion | numeric(14,2) | **restringido a rol administrativo** |
| precio_venta | numeric(14,2) | |
| fecha_ingreso | date | |
| proveedor_id | bigint FK → proveedor | |
| recepcion_linea_id | bigint FK | origen de compra (002), nullable |
| full_set | boolean | |
| full_set_detalle | varchar(255) | caja, papeles, garantía, eslabones… |
| sucursal_actual_id | bigint FK → sucursal | |
| disponibilidad | varchar(14) | `disponible` \| `reservado` \| `en_transito` \| `vendido` \| `en_servicio` \| `dado_de_baja` |
| creado_en, actualizado_en | timestamptz | |

- **Transiciones de `disponibilidad`**: `disponible` → `reservado`/`en_transito`/`vendido`/`en_servicio`; `vendido`/`dado_de_baja` conservan ficha e historial (no se elimina la fila).
- **Validación**: `numero_serie` inmutable salvo corrección con rol elevado + motivo.

## `marca_reloj` (catálogo rico, migración 0012)
`id`, `nombre` varchar(120) único, `pais` varchar(80) nullable, `sitio_web` varchar(200) nullable, `nota` varchar(500) nullable, `activo` boolean, `creado_en`.

## `material` (catálogo para caja y brazalete, migración 0012)
`id`, `nombre` varchar(120) único, `activo` boolean, `creado_en`.

## `color` (catálogo de esfera, migración 0012)
`id`, `nombre` varchar(80) único, `hex` varchar(7) nullable, `activo` boolean, `creado_en`.

## `foto_reloj`
`id`, `reloj_id` FK, `objeto` varchar(255) (clave en `reloj-imagenes`), `orden` int, `creado_en`.

## `documento_reloj`
`id`, `reloj_id` FK, `objeto` (clave en `documentos`), `tipo` (`papeles_full_set` | `factura_compra` | `otro`), `nombre`.

## `evento_serie` (append-only)
| Campo | Tipo |
|---|---|
| id | bigint PK |
| numero_serie | varchar(80) (no FK dura: sobrevive a correcciones) |
| reloj_id | bigint FK |
| tipo | varchar(14): `ingreso` \| `venta` \| `servicio` \| `transferencia` \| `baja` \| `reingreso` \| `correccion` |
| fecha | timestamptz |
| documento_tipo | varchar(30) (`recepcion_compra`, `orden_venta`, `orden_trabajo`, `transferencia`, `merma`) |
| documento_id | bigint |
| detalle | jsonb |

- **Inmutable**: solo INSERT.

## `pieza`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| codigo | varchar(60) | único |
| descripcion | varchar(255) | |
| tipo | varchar(16) | `original` \| `no_original_equivalente` |
| proveedor_id | bigint FK | nullable |
| costo_adquisicion | numeric(14,2) | **restringido a rol administrativo** |
| precio_venta_suelta | numeric(14,2) | nullable |
| stock_minimo | int | default 0 |
| perecedera | boolean | default false |
| activo | boolean | default true |

- **Calibres compatibles** (N—M): `pieza_calibre` (`pieza_id`, `calibre_id`).

## `stock_pieza`
`pieza_id` FK, `sucursal_id` FK, `stock_actual` int (**≥ 0, invariante**), único (`pieza_id`, `sucursal_id`).

## `movimiento_stock_pieza` (append-only)
| Campo | Tipo |
|---|---|
| id | bigint PK |
| pieza_id | bigint FK |
| sucursal_id | bigint FK |
| tipo | varchar(16): `ingreso` \| `consumo_ot` \| `venta_suelta` \| `ajuste` \| `merma` \| `transferencia_salida` \| `transferencia_entrada` |
| cantidad | int (signed) |
| lote_id | bigint FK → lote_pieza (nullable) |
| documento_tipo, documento_id | | referencia al hecho |
| creado_por | bigint FK |
| creado_en | timestamptz |

## `lote_pieza`
`id`, `pieza_id` FK, `sucursal_id` FK, `numero_lote` varchar(60), `fecha_caducidad` date, `cantidad` int (≥0), `estado` (`vigente` | `proximo_vencer` | `vencido`).

## `alerta_stock` (materializada)
`id`, `ambito` (`modelo` | `pieza`), `ref` (marca+referencia o pieza_id), `sucursal_id` FK, `tipo` (`cerca_maximo` | `ultima_unidad` | `bajo_minimo` | `caducidad_proxima` | `lote_vencido`), `estado` (`abierta` | `resuelta`), `creado_en`.

## Reglas de negocio (backend)

1. `stock_pieza.stock_actual` nunca < 0; consumo que lo violaría ⇒ error, transacción abortada.
2. `evento_serie` y `movimiento_stock_pieza` son append-only.
3. Consumo de piezas perecederas ⇒ FEFO por `lote_pieza.fecha_caducidad`.
4. Alertas se recalculan tras cada movimiento; no bloquean.
5. `costo_adquisicion` (reloj y pieza) oculto para roles sin permiso `ver_costos`.
6. Corrección de `numero_serie` / ficha ⇒ rol elevado + motivo + `evento_serie(correccion)` + auditoría.
7. Reloj `vendido`/`dado_de_baja` ⇒ fuera del stock activo, ficha e historial persisten.

## Migraciones

- `0008_inventario` — `calibre`, `reloj`, `foto_reloj`, `documento_reloj`, `evento_serie`, `pieza`, `pieza_calibre`, `stock_pieza`, `movimiento_stock_pieza`, `lote_pieza`, `alerta_stock`
- Datos: parámetros `stock_maximo_modelo` (12), `umbral_reposicion_relojes`, `umbral_reposicion_piezas`, `umbral_caducidad_dias` (30)

## Cambios por feedback del usuario (2026-09-10)

- **marca / material / color dejan de ser texto libre** (migración `0012_ficha_reloj_catalogos`):
  - `marca_reloj` (nombre único, país, sitio_web, nota, activo) — catálogo rico.
  - `material` (nombre único, activo) — compartido para caja y brazalete.
  - `color` (nombre único, hex opcional, activo).
  - `reloj` gana `marca_id`, `material_caja_id`, `material_brazalete_id`, `color_esfera_id`.
    Se conserva `reloj.marca` (texto, denormalizado desde el catálogo) porque
    `alerta_stock` indexa por `marca|referencia`. Retro-carga automática de los
    valores de texto existentes. Los catálogos se administran en Configuración y
    se pueden crear al vuelo con «+» desde la ficha de reloj.
- **Alta de unidad**: exige `recepcion_linea_id` (línea de recepción de compra
  pendiente de fichar) **o** `motivo_alta_manual` (inventario inicial, recompra a
  cliente, consignación…). El motivo queda en `evento_serie(ingreso)` con
  `documento_tipo = 'alta_manual'`. El flujo principal es "Recibir" en la orden de
  compra → fichar cada unidad recibida (encadenado en `RelojFormModal`).
- **Restricción de costo/margen**: la respuesta lleva `costos_visibles: bool`.

## Cambios en `registro_auditoria` (feedback 2026-09-10, migración `0011_auditoria_ip`)

- Columna `ip_origen` (varchar 45), capturada por un middleware HTTP en `main.py`
  (contextvar `shared/request_context`) — sin cambiar la firma de `registrar_cambio`.
- El endpoint `/auditoria` devuelve `actor_nombre` + `actor_identificacion` (join a
  `usuario`) además del id.

## Cambios en `pieza` (feedback 2026-09-10, 3ª ronda — migración `0014`)

- `unidad_medida` (varchar 16, server_default `unidad`): unidad, ml, g, mm, par,
  juego, metro, litro. Cómo se cuenta y se pide la pieza.
- `marca_compatible` (varchar 255, nullable): marcas de reloj compatibles
  ("Rolex, Tudor"); vacío = universal.
- Ambos se muestran en `PiezaFormModal` / `FichaPieza` / `ListaPiezas` y los
  propaga `piezas.datos_pieza`. Al recibir una OC con una "pieza nueva",
  `recibir_de_compra` crea la pieza con estos datos + `descripcion` (nombre) +
  `pieza_tipo` de la línea de compra.


## Ajustes en implementación (2026-09-10)

- **Migración `0009_inventario`**: tablas base de reloj, pieza, stock, eventos y lotes.
- **Migración `0012_ficha_reloj_catalogos`**: catálogos `marca_reloj`, `material`, `color` con resolución busca-o-crea; columnas FK en `reloj`.
- **Migración `0014_oc_lineas_detalle_y_factura`**: `pieza.unidad_medida` y `pieza.marca_compatible`.
- **Alta manual de reloj**: si no proviene de recepción de compra (`recepcion_linea_id` null), exige `motivo_alta_manual`.
- **Búsqueda global**: `GET /relojes/buscar-global` para consultar disponibilidad en todas las sucursales.
