# Implementation Plan: Autenticación, RBAC de Dos Niveles y Configuración

**Branch**: `001-auth-rbac-configuracion` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Primera feature de negocio. Construye: la entidad `usuario` (con autoservicio de datos propios y restablecimiento de contraseña por email temporal); el RBAC de dos niveles (acceso a módulo + operación CRUD, con excepciones por usuario) sobre las tablas base de 000; el login JWT y un **guard reutilizable** que autoriza cada endpoint y aplica scoping por sucursal / por propiedad; la entidad `sucursal` (inactivar exige motivo y notifica a su personal); los catálogos `medio_pago`, `categoria_gasto`, `canal_cita`; el mecanismo de **parámetros de configuración** con vigencia y **recálculo en cascada**; la **auditoría** transversal; y la **capacidad compartida de correo con plantillas** en `backend/src/shared/`.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI (backend), Vue 3 (frontend)

**Primary Dependencies**: SQLAlchemy 2.x, Alembic, `passlib[bcrypt]` (hash), `pyjwt`, `pydantic`, proveedor de email (SendGrid SDK o SMTP), `jinja2` (plantillas de correo); frontend: Pinia (store de sesión), Vue Router (guards de navegación)

**Storage**: PostgreSQL (todas las entidades); MinIO bucket `perfil-usuarios` (fotos de perfil)

**Testing**: `pytest` (guard RBAC de dos niveles — módulo crítico Const. Ppio IX), `vitest`

**Target Platform**: idem 000

**Project Type**: Web (módulos `auth`, `usuarios`, `rbac`, `sucursales`, `configuracion` en backend y frontend; `shared/correo`, `shared/auditoria`, `shared/parametros`)

**Performance Goals**: login < 500 ms; autorización por petición < 20 ms (cacheable); CRUD de configuración < 1 s

**Constraints**: sin secretos hardcodeados; toda validación de permisos en backend; sin SSO externo; contraseña temporal de un solo uso con caducidad; anti-lockout de Gerencia General

**Scale/Scope**: decenas de usuarios, ~13 módulos, 4 operaciones, 1–N sucursales

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | Cada FR cita §3, §3.1, §6, §9, §9.4 o necesidad del negocio. ✅ |
| II | Usuarios, sucursales, parámetros y auditoría son INSERT/UPDATE reales; sin estados simulados. ✅ |
| III | PostgreSQL OLTP; foto de perfil → `perfil-usuarios`. Sin ClickHouse/Airflow. ✅ |
| IV | **Esta feature implementa el Principio IV**: guard rol→módulo→operación, acceso a módulo prerrequisito, sin rutas paralelas, cambios solo por Gerencia General y auditados. ✅ |
| V | Backend valida permisos y recálculo; frontend solo consume. ✅ |
| VI | Referencia 000 (tablas base) y la especificación; no las redefine. ✅ |
| VII | Sin SSO, sin motor de reglas externo; parámetros como key-value tipado. ✅ |
| VIII | Documentos generados de corrido tras aprobación del spec. ✅ |
| IX | Cobertura obligatoria del guard RBAC de dos niveles; secretos por `.env`; anti fuerza bruta. ✅ |
| X | Módulos `auth/`, `usuarios/`, `rbac/`, `sucursales/`, `configuracion/`; `shared/correo`, `shared/auditoria`, `shared/parametros`, `shared/guard`. ✅ |
| XI | Listados con búsqueda multi-criterio; modales del design-system; sin `window.confirm`. ✅ |
| XII | Pantallas con `ui-ux-pro-max`; plantillas de correo con la paleta. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/
├── shared/
│   ├── guard.py            # require_perm(modulo, operacion), scoping por sucursal / propiedad
│   ├── auditoria/          # registrar_cambio(actor, entidad, antes, despues)
│   ├── parametros/         # get_parametro(clave, ambito, fecha), motor de recálculo en cascada
│   └── correo/             # enviar(plantilla, destinatario, contexto) + render Jinja2
├── auth/                   # login, refresh, logout, cambio y restablecimiento de contraseña
│   ├── router.py service.py repository.py schemas.py
├── usuarios/               # CRUD usuario, autoservicio (mis datos, email, foto), asignación de rol/sucursal
├── rbac/                   # roles, módulos (catálogo), matriz permiso_modulo/permiso_operacion, excepciones de usuario
├── sucursales/             # CRUD sucursal, inactivación con motivo + disparo de correo
└── configuracion/          # catálogos (medio_pago, categoria_gasto, canal_cita), parámetros, delegación

frontend/src/
├── shared/                 # (de 000) + guard de navegación por permisos, store de sesión (Pinia)
├── auth/                   # login, "olvidé mi contraseña", forzar cambio de contraseña
├── perfil/                 # "Mis datos" (ver, editar email/foto, cambiar contraseña)
├── usuarios/  rbac/  sucursales/  configuracion/
```

**Structure Decision**: 5 módulos de backend + 4 utilidades en `shared/`. El `guard` y `parametros` son consumidos por todas las features siguientes.

## Complexity Tracking

*Sin violaciones.* El motor de recálculo en cascada se justifica por decisión explícita del negocio (Const. "Parámetros configurables") y se mantiene simple: cada parámetro declara sus consumidores; el recálculo recorre solo entidades "abiertas".
