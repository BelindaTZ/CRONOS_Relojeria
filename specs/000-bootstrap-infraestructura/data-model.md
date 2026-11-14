# Data Model: Bootstrap de Infraestructura

**Feature**: `000-bootstrap-infraestructura` | **Phase**: 1 | **Date**: 2026-09-09

Solo el esquema base de RBAC, **creado vacío de datos de negocio** (migración `0001_rbac_base`). La carga de roles, módulos y permisos, y la tabla `usuario`, son responsabilidad de `001`. Convenciones: `snake_case`, PK `id` (bigint identity), timestamps `creado_en` / `actualizado_en`.

## Entidades

### `rol`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | identity |
| nombre | varchar(80) | único, no nulo |
| descripcion | varchar(255) | opcional |
| creado_en, actualizado_en | timestamptz | default now() |

- **Relaciones**: 1—N con `permiso_modulo`, `permiso_operacion`. (N—M con `usuario` lo define 001.)
- **Estado inicial**: sin filas.

### `modulo`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| clave | varchar(60) | única, no nula (ej. `inventario_relojes`) |
| nombre | varchar(120) | no nulo |
| descripcion | varchar(255) | opcional |

- **Relaciones**: 1—N con `permiso_modulo` y `permiso_operacion`.
- **Estado inicial**: sin filas. (001 siembra los módulos de §3.1.)

### `operacion`
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| clave | varchar(20) | única: `crear` \| `consultar` \| `editar` \| `eliminar` |
| nombre | varchar(40) | no nulo |

- **Estado inicial**: **4 filas sembradas** (Crear, Consultar, Editar, Eliminar). Es enum de dominio fijo, no dato de negocio.

### `permiso_modulo` (acceso a módulo — prerrequisito del granular)
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| rol_id | bigint FK → rol | no nulo |
| modulo_id | bigint FK → modulo | no nulo |
| — | | único (`rol_id`, `modulo_id`) |

- **Estado inicial**: sin filas.

### `permiso_operacion` (permiso granular)
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint PK | |
| rol_id | bigint FK → rol | no nulo |
| modulo_id | bigint FK → modulo | no nulo |
| operacion_id | bigint FK → operacion | no nulo |
| — | | único (`rol_id`, `modulo_id`, `operacion_id`) |

- **Regla de integridad (aplicada por 001 en el guard, modelada aquí)**: no debería existir `permiso_operacion` sin su `permiso_modulo` correspondiente. En 000 se documenta como invariante; 001 la hace cumplir.
- **Estado inicial**: sin filas.

## Migraciones

- `0001_rbac_base` — crea las 5 tablas anteriores + siembra `operacion`. `downgrade` elimina las 5 tablas. Idempotencia verificada por `quickstart.md`.

## Objetos MinIO (no son tablas; se listan por completitud)

| Bucket | Acceso | Creado en |
|---|---|---|
| `reloj-imagenes` | lectura directa app | 000 |
| `perfil-usuarios` | lectura directa app | 000 |
| `comprobantes-venta` | privado, solo backend autenticado | 000 |
| `documentos` | privado, solo backend autenticado | 000 |
| `landing-zone` | — | **012** (no en esta feature) |

## No incluido (otras features)

- `usuario`, sesiones, tokens, restablecimiento → 001
- catálogos `medio_pago`, `categoria_gasto`, `canal_cita`, `parametro_configuracion` → 001
- Todo el esquema de negocio (relojes, citas, OT, ventas, contabilidad…) → 002+
