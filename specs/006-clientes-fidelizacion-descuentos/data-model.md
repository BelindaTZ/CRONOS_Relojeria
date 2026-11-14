# Data Model: Clientes, Fidelización y Descuentos

**Feature**: `006-clientes-fidelizacion-descuentos` | **Phase**: 1 | **Date**: 2026-09-10

Migración real `0017_clientes` (spec inicial decía `0011`). Reutiliza `parametro_configuracion`, `registro_auditoria`, `usuario` (001).

## `cliente`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| tipo | varchar(10) | `natural` \| `juridica` |
| identificacion | varchar(20) | **única** (cédula/RUC); edición solo rol elevado |
| numero_afiliado | varchar(16) | **único**, autogenerado (`AF-######`), inmutable |
| nombre | varchar(200) | no nulo |
| telefono | varchar(40) | |
| email | varchar(160) | |
| direccion | varchar(255) | |
| fecha_nacimiento | date | nullable |
| preferencias | jsonb | marcas, complicaciones |
| notas | text | |
| nivel_fidelizacion_id | bigint FK → nivel_fidelizacion | |
| es_consumidor_final | boolean | default false (fila genérica única) |
| estado | varchar(12) | `activo` \| `inactivo` |
| creado_en, actualizado_en | timestamptz | |

## `consentimiento_datos`
`id`, `cliente_id` FK, `aceptado` boolean (true obligatorio al alta), `version_texto` int, `fecha` timestamptz.

## `nivel_fidelizacion`
`id`, `nombre` varchar(60) único, `orden` int (mayor = superior), `beneficios` jsonb, `es_base` boolean, `activo` boolean.

## `regla_nivel`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| nivel_fidelizacion_id | bigint FK | |
| criterio | varchar(14) | `monto_acumulado` \| `frecuencia` \| `combinacion` |
| ventana_meses | int | default 12 |
| umbral_monto | numeric(14,2) | nullable |
| umbral_frecuencia | int | nullable |
| vigente_desde | date | |
| creado_por | bigint FK | |

## `historial_nivel_cliente` (append-only)
`id`, `cliente_id` FK, `nivel_anterior_id` FK nullable, `nivel_nuevo_id` FK, `hecho_disparador` varchar(30) (`venta`|`servicio`|`recalculo_masivo`), `documento_id` bigint nullable, `fecha` timestamptz.

## `descuento` (general)
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| nombre | varchar(120) | |
| tipo | varchar(10) | `porcentaje` \| `monto` |
| valor | numeric(14,4) | |
| alcance | varchar(10) | `producto` \| `marca` \| `tienda` |
| alcance_ref | varchar(80) | null si `tienda` |
| segmento | varchar(10) | `todos` \| `nivel` \| `cliente` |
| segmento_ref | varchar(80) | nivel_id o cliente_id |
| vigencia_inicio, vigencia_fin | date | nullable si `evento` |
| evento | varchar(24) | `cumpleanos` \| `aniversario_tienda` \| null |
| limite_uso | varchar(12) | `una_vez` \| `n_veces` \| `por_cliente` \| `global` |
| max_usos | int | nullable |
| estado | varchar(10) | `activo` \| `inactivo` \| `vencido` |

## `cupon`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| codigo | varchar(24) | **único** |
| cliente_id | bigint FK | |
| tipo | varchar(10) | `porcentaje` \| `monto` |
| valor | numeric(14,4) | |
| alcance | varchar(10) | `producto` \| `marca` \| `tienda` |
| alcance_ref | varchar(80) | |
| vigencia_inicio, vigencia_fin | date | |
| evento | varchar(24) | nullable |
| limite_uso | varchar(12) | `una_vez` \| `n_veces` \| `por_cliente` \| `global` |
| max_usos | int | nullable |
| usos | int | default 0 |
| estado | varchar(10) | `activo` \| `usado` \| `vencido` |

## `parametro_margen_minimo` (se guarda como `parametro_configuracion` con clave `margen_minimo`)
Ámbito `global` / `marca` / `producto`; valor `{tipo: porcentaje_costo | monto, valor}`.

## `aplicacion_descuento` (registro sobre venta/OT — la fila la crea 008/009, el modelo lo define 006)
`id`, `documento_tipo` (`venta`|`orden_trabajo`), `documento_id`, `linea_id`, `origen` (`descuento`|`cupon`), `origen_id`, `precio_lista` numeric, `precio_final` numeric, `margen_resultante` numeric, `autorizacion_id` bigint FK nullable.

## `autorizacion_margen_minimo`
`id`, `documento_tipo`, `documento_id`, `autorizador_usuario_id` FK (rol Gerencia General), `margen_resultante` numeric, `motivo` varchar(255), `fecha` timestamptz.

## Reglas de negocio (backend)

1. `identificacion` y `numero_afiliado` únicos; identificación editable solo con rol elevado + auditoría.
2. `consentimiento_datos.aceptado = true` obligatorio para crear el cliente.
3. Nivel: recálculo del cliente al confirmarse venta/servicio; `historial_nivel_cliente` si cambia (sin duplicar si no cambia).
4. Cambio de `regla_nivel` ⇒ recálculo masivo diferido; historial conservado; auditoría.
5. **Descuento y cupón mutuamente excluyentes** en una misma venta/OT (422 si se intentan ambos).
6. Cupón de uso único ⇒ lock; `usos` no supera `max_usos`.
7. Margen mínimo: `decision` ∈ {permitir, bloquear, requiere_autorizacion}; sin `autorizacion_margen_minimo` la operación no se confirma cuando `requiere_autorizacion`.
8. Todo cálculo de nivel y de margen mínimo en backend.
9. `cliente` con transacciones ⇒ no DELETE; `inactivo` o anonimización según necesidad legal.

## Migración

- `0011_clientes` — todas las tablas anteriores
- Datos: `nivel_fidelizacion` base (Bronce) + parámetros `margen_minimo` (global), `texto_consentimiento_lopdp` (v1), `monto_max_consumidor_final`; fila `cliente` genérica `es_consumidor_final = true`; registrar consumidores en `shared/parametros`

---

## Ajustes en implementación (2026-09-10)

- **Migración `0017_clientes`** (no `0011`). `regla_nivel.criterio` = `varchar(20)` (cabe `monto_acumulado`).
- `nivel_fidelizacion` gana `creado_en`; `descuento` y `cupon` ganan `usos` (int) y `creado_por` FK.
- `aplicacion_descuento.autorizacion_id` es FK a `autorizacion_margen_minimo` (SET NULL) creada al final de la migración para evitar dependencia circular en el orden de `create_table`.
- `historial_nivel_cliente` tiene trigger `cronos_append_only` (BEFORE UPDATE OR DELETE).
- Parámetros sembrados: `margen_minimo` (json `{tipo: porcentaje_costo, valor: 0.15}`), `margen_minimo_politica` (`"autorizar"`), `monto_max_consumidor_final` (500), `fidelizacion_ventana_meses` (12), `texto_consentimiento_lopdp` (json `{version:1, texto:…}`).
- Índice único parcial `uq_cliente_consumidor_final` garantiza una sola fila `es_consumidor_final = true`.
- La fuente de transacciones (compras/servicios) la conectan 008/009 vía `clientes.registrar_proveedor_transacciones(fn)`.

## Ampliación 2026-09-10 (riesgo de abandono + sucursal en transacciones)

- **Migración `0018_clientes_riesgo_y_sucursal_tx`** — solo semilla de parámetros (§9), sin tablas:
  `churn_piso_dias = 90`, `churn_factor_cadencia = 2`, `churn_min_transacciones = 3`,
  `churn_ventana_analisis_meses = 24`. `clientes.registrar_consumidores` no los engancha al recálculo
  en cascada (son de lectura para un reporte en caliente).
- **`TransaccionCliente`** (DTO de 008/009, no tabla) gana `sucursal_id`; `MovimientoHistorialOut`
  expone `sucursal_id` + `sucursal_nombre`.
- El reporte de riesgo (`GET /reportes/clientes-en-riesgo`) y la emisión del cupón de reactivación
  (`POST /cupones/reactivacion`, `require_gerencia_o_delegado`) no persisten nada nuevo salvo el
  `cupon` resultante.
