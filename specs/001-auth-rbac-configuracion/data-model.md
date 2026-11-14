# Data Model: Autenticación, RBAC de Dos Niveles y Configuración

**Feature**: `001-auth-rbac-configuracion` | **Phase**: 1 | **Date**: 2026-09-09

Convenciones: `snake_case`, PK `id` bigint identity, `creado_en`/`actualizado_en` timestamptz. Migraciones Alembic `0002_*`..`0006_*`. Reutiliza `rol`, `modulo`, `operacion`, `permiso_modulo`, `permiso_operacion` de 000 (los completa).

## Entidades

### `usuario`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| identificacion | varchar(20) | única, no nula (cédula/RUC) |
| nombre | varchar(160) | no nulo |
| email | varchar(160) | único, no nulo (destino de restablecimiento) |
| password_hash | varchar(255) | bcrypt |
| foto_perfil_objeto | varchar(255) | clave en bucket `perfil-usuarios`, opcional |
| estado | varchar(12) | `activo` \| `inactivo` |
| must_change_password | boolean | default false |
| creado_en, actualizado_en | timestamptz | |

- **Relaciones**: N—M con `rol` vía `usuario_rol`; N—M con `sucursal` vía `usuario_sucursal`; 1—N con `permiso_usuario`, `refresh_token`, `solicitud_restablecimiento`.
- **Validación**: no se puede pasar a `inactivo`, ni quitar el rol Gerencia General, si es el último usuario activo con ese rol.

### `usuario_rol`
`usuario_id` FK, `rol_id` FK, único (`usuario_id`, `rol_id`).

### `usuario_sucursal`
`usuario_id` FK, `sucursal_id` FK, único (`usuario_id`, `sucursal_id`).

### `permiso_usuario` (excepción individual)
| Campo | Tipo | Reglas |
|---|---|---|
| usuario_id | bigint FK | |
| modulo_id | bigint FK | |
| operacion_id | bigint FK | nullable (null ⇒ excepción a nivel de acceso a módulo) |
| efecto | varchar(8) | `conceder` \| `revocar` |
| — | | único (`usuario_id`, `modulo_id`, `operacion_id`) |

### `refresh_token`
`id`, `usuario_id` FK, `token_hash`, `expira_en`, `revocado_en` nullable, `creado_en`.

### `solicitud_restablecimiento`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| usuario_id | bigint FK | |
| password_temporal_hash | varchar(255) | bcrypt |
| expira_en | timestamptz | now() + parámetro (def. 24 h) |
| usada | boolean | default false |
| creado_en | timestamptz | |

- **Transiciones**: `vigente` → `usada` (login exitoso con la temporal) | `caducada` (expira_en < now()). Una temporal `usada`/`caducada` es rechazada.

### `sucursal`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| nombre | varchar(120) | única, no nula |
| direccion | varchar(255) | |
| responsable_usuario_id | bigint FK → usuario | nullable |
| estado | varchar(12) | `activa` \| `inactiva` |
| motivo_inactivacion | varchar(500) | obligatorio si `estado = inactiva` |
| inactivada_en | timestamptz | nullable |

- **Transición** `activa` → `inactiva`: exige `motivo_inactivacion`; dispara `shared/correo` a cada usuario/técnico de `usuario_sucursal`.

### `medio_pago`
`id`, `clave` única (`efectivo` | `transferencia` | `cheque` | `tarjeta`), `nombre`, `activo`. Sembrado con los 4 valores fijos (Const. "Stack").

### `categoria_gasto`
`id`, `nombre` única, `tipo` (`local_operativos` | `personal` | `otros` | `mermas_perdidas`), `activo`.

### `canal_cita`
`id`, `nombre` única (sembrado: `correo_electronico`, `presencial`), `activo`.

### `parametro_configuracion`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| clave | varchar(80) | no nula (ej. `margen_objetivo_servicio`) |
| tipo | varchar(16) | `numero` \| `porcentaje` \| `monto` \| `json` \| `texto` |
| valor | jsonb | no nulo |
| ambito_tipo | varchar(16) | `global` \| `sucursal` \| `marca` \| `producto` \| `tipo_servicio` |
| ambito_ref | varchar(80) | null si `global` |
| vigente_desde | timestamptz | no nulo |
| creado_por | bigint FK → usuario | |
| creado_en | timestamptz | |

- **Historial**: solo INSERT. El valor vigente es el de mayor `vigente_desde` ≤ ahora para (clave, ámbito).
- **Recálculo**: al insertar, `recalcular(clave)` procesa consumidores registrados sobre entidades "abiertas".

### `registro_auditoria`
| Campo | Tipo |
|---|---|
| id | bigint PK |
| actor_usuario_id | bigint FK |
| accion | varchar(40) (`crear`/`editar`/`eliminar`/`inactivar`/`login`/`reset_password`/…) |
| entidad | varchar(60) |
| entidad_id | varchar(40) |
| antes | jsonb nullable |
| despues | jsonb nullable |
| ip_origen | varchar(45) nullable (origen de la petición, añadido en 0011) |
| creado_en | timestamptz |

## Reglas de negocio transversales (validación en backend)

1. Acceso a módulo prerrequisito de la operación (guard).
2. Anti-lockout de Gerencia General.
3. Autoservicio: `usuario` solo puede modificar sus propios `email` y `foto_perfil_objeto`; nunca `rol`, `permiso_usuario`, `usuario_sucursal`, `identificacion`.
4. Cambio de parámetro ⇒ recálculo en cascada de lo abierto + auditoría; nunca toca documentos emitidos ni periodos cerrados.
5. Todo cambio en RBAC, catálogos, parámetros, sucursal y autoservicio ⇒ `registro_auditoria`.

## Migraciones

- `0002_usuario_y_sesion` — `usuario`, `usuario_rol`, `usuario_sucursal`, `refresh_token`, `solicitud_restablecimiento`
- `0003_rbac_datos` — `permiso_usuario`; siembra `modulo` (§3.1 + `ventas`, `notificaciones`)
- `0004_sucursal`
- `0005_catalogos` — `medio_pago` (sembrado), `categoria_gasto`, `canal_cita` (sembrado)
- `0006_parametros_y_auditoria` — `parametro_configuracion`, `registro_auditoria`
- `0011_auditoria_ip` — añade columna `ip_origen` en `registro_auditoria` (feedback del usuario)
- `0024_roles_negocio` — siembra canónica de los 5 roles de negocio (Gerente de Sucursal, Vendedor, Técnico, Técnico Jefe, Contador) con sus matrices por defecto
