# Requirements Quality Checklist: Auth, RBAC y Configuración

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 001.
**Created**: 2026-09-09
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están definidas todas las operaciones del ciclo de vida del usuario (alta, edición, activación, desactivación, asignación de rol/sucursal)? [Completeness, Spec §FR-001, §FR-002]
- [x] CHK002 ¿Se especifica exactamente qué campos puede editar un usuario en el autoservicio y cuáles no? [Completeness, Spec §FR-011]
- [x] CHK003 ¿Está completo el flujo de restablecimiento (solicitud, generación, envío, caducidad, un solo uso, cambio forzado)? [Completeness, Spec §FR-013, §FR-014]
- [x] CHK004 ¿Se define el conjunto de catálogos que gestiona esta feature y sus valores sembrados? [Completeness, Spec §FR-019, §FR-020, §FR-021]
- [x] CHK005 ¿Están documentados los ámbitos posibles de un parámetro configurable? [Completeness, Spec §FR-022]
- [x] CHK006 ¿Se especifica qué eventos generan registro de auditoría? [Completeness, Spec §FR-025]
- [x] CHK007 ¿Se define el contenido del aviso de inactivación de sucursal y sus destinatarios? [Completeness, Spec §FR-017]

## Requirement Clarity

- [x] CHK008 ¿"Acceso al módulo prerrequisito del permiso granular" está definido de forma verificable? [Clarity, Spec §FR-005]
- [x] CHK009 ¿Está cuantificada la caducidad de la contraseña temporal? [Clarity, Spec §FR-013, Assumptions]
- [x] CHK010 ¿"Recálculo en cascada de lo abierto" define con precisión qué es "abierto" y qué queda excluido? [Clarity, Spec §FR-023]
- [x] CHK011 ¿Se define el comportamiento exacto ante 401 vs 403 vs falta de sucursal asignada? [Clarity, Spec §FR-008, §FR-018]
- [x] CHK012 ¿"Plantilla cuidada" se ata a un criterio (identidad visual del Principio XI)? [Clarity, Spec §FR-017, §FR-028]

## Requirement Consistency

- [x] CHK013 ¿La lista de módulos del spec coincide con §3.1 y con `research.md` D10? [Consistency, Spec §FR-003]
- [x] CHK014 ¿El catálogo `medio_pago` del spec coincide con los valores fijos de la constitución ("Stack")? [Consistency, Spec §FR-019]
- [x] CHK015 ¿La regla de recálculo del spec es consistente con la de la constitución ("Parámetros configurables")? [Consistency, Spec §FR-023]
- [x] CHK016 ¿El autoservicio (§FR-011) no entra en conflicto con la gestión administrativa de usuarios (§FR-001)? [Consistency]

## Acceptance Criteria Quality

- [x] CHK017 ¿Cada Success Criterion es medible (tiempos, códigos, conteos, cobertura)? [Measurability, Spec §SC-001..§SC-010]
- [x] CHK018 ¿Existe un criterio objetivo para "el 100% de los endpoints de negocio pasa por el guard"? [Measurability, Spec §SC-002]
- [x] CHK019 ¿El criterio de anti-lockout es verificable? [Measurability, Spec §SC-008]

## Scenario & Edge Case Coverage

- [x] CHK020 ¿Se cubre el token emitido antes de revocar permisos? [Edge Case, Spec Edge Cases, §FR-010]
- [x] CHK021 ¿Se cubren los permisos granulares huérfanos al retirar acceso al módulo? [Edge Case, Spec Edge Cases]
- [x] CHK022 ¿Se cubre la solicitud de restablecimiento de un usuario sin email? [Edge Case, Spec Edge Cases]
- [x] CHK023 ¿Se cubre inactivar una sucursal con transferencias en tránsito o cajas abiertas? [Edge Case, Spec Edge Cases]
- [x] CHK024 ¿Se aborda el usuario sin sucursal en operación scoped? [Coverage, Spec §FR-018]
- [x] CHK025 ¿Se cubre el cambio de un parámetro que afecta un documento ya emitido / periodo cerrado? [Coverage, Spec §FR-023, US6]

## Non-Functional Requirements

- [x] CHK026 ¿Hay requisitos anti fuerza bruta para login y restablecimiento? [Security, Spec §FR-027]
- [x] CHK027 ¿Se exige hash fuerte de contraseñas y secretos vía `.env`? [Security, Spec §FR-001, Assumptions]
- [x] CHK028 ¿Se define el objetivo de rendimiento de la autorización por petición? [Performance, Plan Technical Context]
- [x] CHK029 ¿Se exige cobertura de pruebas del guard de dos niveles? [Testing, Spec §SC-010]

## Dependencies & Assumptions

- [x] CHK030 ¿Se documenta la dependencia de 000 (tablas base, bucket `perfil-usuarios`)? [Dependency, Spec Assumptions]
- [x] CHK031 ¿Se documenta la dependencia del proveedor de email y su configuración por `.env`? [Dependency, Spec Assumptions]
- [x] CHK032 ¿Se valida la suposición de que los valores de negocio concretos los aporta cada feature dueña? [Assumption, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK033 ¿Queda claro si el enlace de restablecimiento es contraseña temporal o token firmado? [Ambiguity → resuelto: contraseña temporal, research D4]
- [x] CHK034 ¿"Delegado de Gerencia General" está definido (cómo se delega el acceso a Configuración)? [Gap, Spec §FR-024]
