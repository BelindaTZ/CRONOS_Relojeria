# Data Model: Técnicos y Productividad

**Feature**: `005-tecnicos-productividad` | **Phase**: 1 | **Date**: 2026-09-10

Migración `0010_tecnicos`. Reutiliza `usuario`, `sucursal`, `parametro_configuracion`, `registro_auditoria` (001).

## `tecnico`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| usuario_id | bigint FK → usuario | nullable, único |
| nombre | varchar(160) | no nulo |
| certificaciones | text | descriptivo |
| estado | varchar(12) | `activo` \| `inactivo` (inactivación: solo Técnico Jefe / Gerencia General) |
| creado_en, actualizado_en | timestamptz | |

- **Especialidades** (N—M): `tecnico_especialidad` (`tecnico_id`, `especialidad` varchar(60)) — catálogo `especialidad`.
- **Sucursales** (N—M): `tecnico_sucursal` (`tecnico_id`, `sucursal_id`).

## `especialidad`
`id`, `nombre` varchar(60) único (marca o tipo de complicación).

## `esquema_costo_mano_obra`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| tecnico_id | bigint FK | |
| sueldo_mensual | numeric(14,2) | **restringido a rol administrativo** |
| vigente_desde | date | |
| creado_por | bigint FK | historial por inserción |

- **Derivado**: `tarifa_hora = sueldo_mensual / parametro("horas_productivas_estandar_mes")`.

## `regla_bono`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| nombre | varchar(120) | |
| periodicidad | varchar(10) | `mensual` \| `trimestral` |
| vigente_desde | date | |
| creado_por | bigint FK | |

## `componente_bono`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| regla_bono_id | bigint FK | |
| tipo | varchar(20) | `monto_por_meta` \| `porcentaje_margen` \| `combinacion` |
| indicador | varchar(24) | `ot_completadas` \| `cumplimiento_tiempos` \| `margen_generado` \| `calidad` |
| umbral | numeric(14,4) | valor a superar |
| valor | numeric(14,4) | monto o porcentaje |

## `periodo_liquidacion`
`id`, `fecha_inicio` date, `fecha_fin` date, `estado` (`abierto` | `cerrado`), `cerrado_por` FK nullable, `cerrado_en` nullable.

## `bono_acumulado`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| tecnico_id | bigint FK | |
| periodo_liquidacion_id | bigint FK | |
| regla_bono_id | bigint FK | la vigente al calcular |
| valor_total | numeric(14,2) | **≥ 0** |
| desglose | jsonb | por indicador: {valor_indicador, umbral, aporta, monto} |
| estado | varchar(10) | `preliminar` (periodo abierto) \| `definitivo` (periodo cerrado) |
| calculado_en | timestamptz | |

- **Regla**: `valor_total ≥ 0` (bono nunca negativo).
- **Prorrateo**: al calcular, se produce `bono_ot` por cada OT cerrada del periodo (`bono_ot = valor_total × costo_mo_ot / Σ costo_mo_ot`); 008 lo consume.

## `bono_ot`
`id`, `bono_acumulado_id` FK, `orden_trabajo_id` bigint (de 008), `monto` numeric(14,2).

## Reglas de negocio (backend)

1. `sueldo_mensual` y `desglose`/`valor_total` del bono ocultos para roles sin permiso administrativo; nunca en documentos del cliente.
2. Bono `valor_total ≥ 0`; periodo sin OT ⇒ 0.
3. Cambiar `regla_bono` o `horas_productivas_estandar_mes` ⇒ recálculo de `bono_acumulado` de periodos `abierto`; periodos `cerrado` intactos; auditoría.
4. Técnico no puede editar su costo, especialidades, certificaciones, ni inactivarse.
5. `costo_mo_ot` (función de `costeo.py`) = `tarifa_hora × horas_registradas` o `tarifa_hora × tiempo_estimado(tipo_reparacion)`.

## Migración

- `0010_tecnicos` — todas las tablas anteriores + `especialidad`
- Datos: parámetro `horas_productivas_estandar_mes = 160`; registrar el consumidor del recálculo en `shared/parametros`

---

## Ajustes en implementación (2026-09-10)

- **Migración `0016_tecnicos`** (no `0010`, que lo tomó 004). Añade también `especialidad.activo` y `regla_bono.activa` (solo una regla vigente a la vez; la nueva desactiva la anterior).
- `bono_acumulado.desglose` guarda `{componentes: [...], indicadores: {ot_completadas, cumplimiento_tiempos, margen_generado, calidad}}` y, en su caso, `sin_regla_vigente` / `sin_ot_en_el_periodo`.
- `esquema_costo_mano_obra` es historial por inserción (sin `id` de "vigente", se toma el de `vigente_desde` más reciente ≤ fecha).
- Parámetros sembrados: `horas_productivas_estandar_mes = 160`, `tiempo_estimado_horas_default = 2` (fallback del tiempo estimado por tipo de reparación hasta que 008 defina su catálogo `tiempo_estimado_horas__<tipo>`).
- La fuente de OT la conecta 008 vía `tecnicos.registrar_proveedor_ot(fn)`; `fn(db, desde, hasta, tecnico_id|None) -> [OrdenTrabajoInfo]`.
