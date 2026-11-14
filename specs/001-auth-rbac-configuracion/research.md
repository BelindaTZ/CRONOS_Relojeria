# Research: Autenticación, RBAC de Dos Niveles y Configuración

**Feature**: `001-auth-rbac-configuracion` | **Phase**: 0 | **Date**: 2026-09-09

No quedan `NEEDS CLARIFICATION` (resueltos en el spec y en la constitución v1.6.0).

## D1 — Modelo de autorización de dos niveles

- **Decisión**: dos tablas de asociación — `permiso_modulo` (rol×módulo) y `permiso_operacion` (rol×módulo×operación) — más overrides por usuario en `permiso_usuario` (concede/revoca una operación puntual). El guard resuelve: (1) ¿el usuario tiene acceso al módulo por rol o por override? (2) ¿tiene la operación por rol o por override? La (1) es prerrequisito de la (2).
- **Rationale**: §3.1 exige los dos niveles independientes + excepción por usuario; Const. Ppio IV.
- **Alternativas**: permisos planos tipo scope string (`inventario:crear`) — pierde el prerrequisito explícito de módulo y complica la UI de matriz. Casbin — dependencia pesada no justificada (Ppio VII).

## D2 — Autenticación

- **Decisión**: JWT de acceso corto (config, def. 30 min) + refresh token opaco en DB (revocable). Password con bcrypt (`passlib`). `JWT_SECRET` desde `.env`.
- **Rationale**: Const. "Stack" (JWT sobre RBAC de PostgreSQL), Ppio IX.
- **Alternativas**: sesiones server-side con cookie — válido pero el frontend SPA + guard por endpoint encaja mejor con bearer token. OAuth2/OIDC externo — fuera de alcance (spec).

## D3 — Frescura de la autorización

- **Decisión**: el guard consulta permisos vigentes en cada petición (con caché en proceso de TTL corto, invalidada al guardar la matriz). El JWT solo transporta `user_id` y metadatos mínimos, no la lista de permisos.
- **Rationale**: FR-010 (reflejar rol/excepciones vigentes, no los del momento de emisión).
- **Alternativas**: meter permisos en el token — obliga a expiraciones muy cortas o listas de revocación.

## D4 — Restablecimiento de contraseña

- **Decisión**: solicitud por identificación/email → se genera contraseña temporal aleatoria, se guarda su hash + `expira_en` (config, def. 24 h) + `usada=false`, y se envía por correo (plantilla). Login con temporal válida ⇒ `must_change_password=true` ⇒ el token emitido solo permite el endpoint de cambio de contraseña hasta que se fije una nueva. Temporal caducada/usada ⇒ rechazo. Rate-limit por identificación e IP.
- **Rationale**: decisión del negocio (spec Q: "enviando la nueva al correo... temporal"). KISS.
- **Alternativas**: enlace de un solo uso con token firmado — más seguro pero requiere endpoint público de landing; se puede migrar luego sin cambiar el modelo.

## D5 — Scoping de datos

- **Decisión**: el guard expone helpers `scope_sucursal(query, user)` y `scope_propiedad(query, user, campo_owner)`. Cada endpoint de features siguientes declara si es "consolidado", "propia sucursal" o "solo propios" según el rol. Un usuario sin sucursal asignada no puede ejecutar operaciones "propia sucursal".
- **Rationale**: §3, §4.9, §3.1 ("solo las propias").
- **Alternativas**: RLS de PostgreSQL — potente pero acopla la lógica al motor y complica el testing; se evalúa a futuro.

## D6 — Parámetros de configuración y recálculo en cascada

- **Decisión**: tabla `parametro_configuracion` (clave, tipo, valor JSON, ámbito {global|sucursal|marca|producto|tipo_servicio}, `vigente_desde`, `creado_por`). Historial por inserción (nunca UPDATE destructivo). Cada parámetro declara `consumidores` (features que lo usan). Al guardar un valor nuevo, un servicio `recalcular(clave)` dispara, por cada consumidor, el recálculo de sus entidades "abiertas" (bonos de periodos no cerrados, márgenes de ventas/OT no confirmadas/no entregadas, niveles de fidelización, materializaciones de reportes). Documentos legales emitidos y periodos contables cerrados quedan intactos. Todo el efecto se audita.
- **Rationale**: decisión del negocio (Const. "Parámetros configurables — recálculo en cascada"), §9.4.
- **Alternativas**: recálculo perezoso al leer — impredecible para reportes; recálculo total incluyendo lo emitido — rompe integridad legal/contable.

## D7 — Auditoría

- **Decisión**: `registro_auditoria` (actor, accion, entidad, entidad_id, antes JSON, despues JSON, timestamp). Helper `shared/auditoria` invocado por servicios en cambios de permisos, catálogos, parámetros, inactivación de sucursal, autoservicio de usuario.
- **Rationale**: §6, §9.4.
- **Alternativas**: triggers de DB — opacos para el dominio y difíciles de testear.

## D8 — Capacidad compartida de correo

- **Decisión**: `shared/correo` con interfaz `enviar(plantilla: str, a: str, contexto: dict)`. Render con Jinja2 sobre plantillas HTML que heredan un layout con la paleta del Principio XI. Adaptador de proveedor (SendGrid o SMTP) elegido por `.env`. En 001 los envíos son directos; 014 añade cola, reintentos, panel y opt-out y toma la gestión de plantillas.
- **Rationale**: Const. Ppio X y XI; el patrón de "capacidad compartida introducida por la primera feature que la necesita".
- **Alternativas**: acoplar el envío a cada feature — duplicación (DRY).

## D9 — Anti-lockout de Gerencia General

- **Decisión**: una comprobación de servicio impide desactivar/eliminar o quitar el rol al último usuario activo con rol "Gerencia General".
- **Rationale**: FR-026, derivado de §9.4.

## D10 — Siembra de módulos

- **Decisión**: migración de datos que inserta en `modulo` la lista de §3.1 (`citas`, `proveedores`, `tecnicos`, `inventario_relojes`, `piezas`, `lubricacion`, `ordenes_trabajo`, `clientes_fidelizacion`, `multisucursal`, `contable`, `reportes`, `mermas`, `configuracion`) + `ventas` y `notificaciones`. Cada feature siguiente puede añadir el suyo si falta.
- **Rationale**: §3.1; FR-003.
