# Quickstart: Autenticación, RBAC de Dos Niveles y Configuración

**Feature**: `001-auth-rbac-configuracion` | **Phase**: 1

Valida login, guard de dos niveles, autoservicio, restablecimiento, sucursales con aviso, parámetros con recálculo y auditoría. No contiene código de implementación.

## Prerrequisitos

- Feature 000 implementada y corriendo (`docker compose up`, migraciones al día)
- Correo: `.env` con credenciales del proveedor (o adaptador SMTP local tipo MailHog para pruebas)
- Migraciones `0002`–`0006` aplicadas

## Setup

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed_gerencia   # crea 1 usuario Gerencia General inicial desde .env
```

## Escenarios

### V1 — Matriz de permisos (US1)
1. Login como Gerencia General → token.
2. `POST /roles` `{nombre:"Vendedor"}`; `PUT /roles/{id}/permisos` habilita módulo `citas` con `crear,consultar,editar`.
3. Crear usuario Vendedor, asignarle el rol.
- **Esperado**: como Vendedor, `POST /citas` permitido (cuando exista 007), `DELETE /citas/{id}` → 403; cualquier endpoint de `contable` → 403.

### V2 — Guard: 401 vs 403 (US2)
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/roles            # sin token → 401
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer <vendedor>" http://localhost:8000/roles   # 403
```
- **Esperado**: 401 sin token, 403 sin permiso. Cambiar el rol del usuario y repetir: la autorización refleja el cambio sin re-login.

### V3 — Autoservicio (US3)
- Login como Vendedor → `GET /perfil` muestra identificación, nombre, rol, sucursales (solo lectura), email, foto.
- `PATCH /perfil` cambia `email` y sube foto (a `perfil-usuarios`).
- `PATCH /perfil {rol_id: X}` → 403 / campo ignorado.
- **Esperado**: cambios de email/foto aplicados y auditados; rol inmutable desde autoservicio.

### V4 — Restablecimiento de contraseña (US4)
```bash
curl -s -XPOST http://localhost:8000/auth/olvide-contrasena -d '{"identificacion":"1712345678"}'
# revisar bandeja (MailHog) → contraseña temporal
curl -s -XPOST http://localhost:8000/auth/login -d '{"identificacion":"1712345678","password":"<temporal>"}'
```
- **Esperado**: el login con la temporal devuelve un token con `must_change_password`; cualquier endpoint distinto de `POST /auth/cambiar-contrasena` → 409/403 hasta cambiarla. Temporal reutilizada o caducada → 401.

### V5 — Sucursal: inactivación con aviso (US5)
1. `POST /sucursales` (activa); asignar 2 usuarios y 1 técnico (cuando exista 005, usar usuarios).
2. `POST /sucursales/{id}/inactivar` sin `motivo` → 422.
3. `POST /sucursales/{id}/inactivar {motivo:"cierre temporal"}`.
- **Esperado**: `estado=inactiva`, `motivo_inactivacion` guardado, auditado; cada usuario asignado recibe un email con plantilla (verificar en MailHog).

### V6 — Catálogos (US5)
```bash
curl -s http://localhost:8000/catalogos/medio-pago     # efectivo, transferencia, cheque, tarjeta
curl -s http://localhost:8000/catalogos/canal-cita     # correo_electronico, presencial
```

### V7 — Parámetro con recálculo y auditoría (US6)
1. `PUT /parametros/margen_objetivo_servicio {valor: 0.5, ambito_tipo:"global"}`.
2. Consultar `GET /parametros/margen_objetivo_servicio` y `GET /auditoria?entidad=parametro_configuracion`.
- **Esperado**: nuevo valor vigente; registro de auditoría con antes/después; el motor de recálculo se invoca para los consumidores (sin efecto visible aún porque 005/008 no existen; verificar el log/registro de la corrida). Un periodo contable cerrado (cuando exista 010) no se altera.

### V8 — Anti-lockout
- Intentar `PATCH /usuarios/{gerencia}/estado {estado:"inactivo"}` siendo el único Gerencia General activo → 409.

### V9 — Scoping por sucursal
- Con datos de 2 sucursales (mock), un usuario "gerente de sucursal A" que llama un endpoint scoped solo obtiene A; Gerencia General obtiene consolidado.

## Contratos

- [`contracts/auth.openapi.yaml`](./contracts/auth.openapi.yaml)
- [`contracts/rbac.openapi.yaml`](./contracts/rbac.openapi.yaml)
- [`contracts/configuracion.openapi.yaml`](./contracts/configuracion.openapi.yaml)

## Criterio de "listo"

V1–V9 pasan; cobertura de pruebas del guard de dos niveles (Const. Ppio IX); prueba de contrato que rechaza cualquier endpoint de negocio sin `require_perm`.
