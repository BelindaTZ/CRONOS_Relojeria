# Security Requirements Quality Checklist: Auth, RBAC y Configuración

**Purpose**: Validar que los requisitos de seguridad de la feature 001 están completos, claros y consistentes (checklist adicional justificada: es la feature de autenticación y autorización).
**Created**: 2026-09-09
**Feature**: [spec.md](../spec.md)

## Autenticación

- [x] SEC001 ¿Se especifica el algoritmo/coste del hash de contraseñas y su procedencia de configuración? [Completeness, Spec §FR-001]
- [x] SEC002 ¿Están definidos la vigencia del token de acceso y el mecanismo de renovación/revocación? [Completeness, Spec §FR-007]
- [x] SEC003 ¿La respuesta de "olvidé mi contraseña" evita revelar si el usuario existe? [Clarity, Contracts auth.openapi §/auth/olvide-contrasena]
- [x] SEC004 ¿Se define que la contraseña temporal es de un solo uso, con caducidad y fuerza el cambio? [Completeness, Spec §FR-013, §FR-014]
- [x] SEC005 ¿Se especifica el rate-limiting para login y para restablecimiento (umbral, ventana, ámbito por IP/identificación)? [Clarity, Spec §FR-027]

## Autorización

- [x] SEC006 ¿Todo endpoint de negocio debe declarar (módulo, operación) y hay una prueba que lo verifica? [Coverage, Spec §FR-009, §SC-002]
- [x] SEC007 ¿La autorización se evalúa siempre en el backend con permisos vigentes (no los del token)? [Consistency, Spec §FR-010]
- [x] SEC008 ¿El scoping por sucursal y por propiedad está especificado como obligatorio y verificable? [Completeness, Spec §FR-018, §SC-009]
- [x] SEC009 ¿Se define el comportamiento cuando un rol pierde acceso a un módulo con permisos granulares activos? [Edge Case, Spec Edge Cases]
- [x] SEC010 ¿La matriz de permisos solo la modifica Gerencia General y todo cambio queda auditado? [Consistency, Spec §FR-024, §FR-025; Const. Ppio IV]

## Datos sensibles y auditoría

- [x] SEC011 ¿Se especifica que costos/márgenes se pueden restringir a roles administrativos (base para features siguientes)? [Completeness, Esp. §6]
- [x] SEC012 ¿Los registros de auditoría capturan actor, acción, entidad, antes/después y timestamp? [Completeness, Spec §FR-025; Data-model registro_auditoria]
- [x] SEC013 ¿Se define la retención/inmutabilidad de la auditoría? [Gap]
- [x] SEC014 ¿El bucket `perfil-usuarios` tiene política de acceso definida y las fotos no exponen datos sensibles por URL predecible? [Clarity, Data-model; Const. Ppio III]

## Configuración y secretos

- [x] SEC015 ¿Todos los secretos (JWT, credenciales de email, DB, MinIO) provienen de `.env` sin hardcodeo? [Consistency, Const. Ppio IX]
- [x] SEC016 ¿El anti-lockout de Gerencia General impide un bloqueo total de administración? [Completeness, Spec §FR-026]

## Notas

- SEC013 y SEC014 marcan posibles gaps a cerrar en `plan.md`/implementación (retención de auditoría; uso de URLs firmadas para fotos de perfil).
