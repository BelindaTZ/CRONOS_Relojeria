# Requirements Quality Checklist: Bootstrap de Infraestructura

**Purpose**: Validar la calidad, claridad y completitud de los requisitos del `spec.md` de la feature 000 antes de planificar/implementar.
**Created**: 2026-09-09
**Feature**: [spec.md](../spec.md)

**Review Ownership**: reviewer-owned. Marcar `[x]` solo cuando el criterio de calidad del requisito esté satisfecho.

## Requirement Completeness

- [x] CHK001 ¿Están definidos todos los servicios que el `docker-compose.yml` debe contener y lo que se excluye explícitamente? [Completeness, Spec §FR-001, §FR-020]
- [x] CHK002 ¿Se especifica el conjunto exacto de buckets a crear y su política de acceso por bucket? [Completeness, Spec §FR-019]
- [x] CHK003 ¿Están definidas las tablas del esquema base de RBAC y su estado inicial (vacío vs. sembrado)? [Completeness, Spec §FR-008, §FR-009, §FR-010]
- [x] CHK004 ¿Se documenta qué provee 000 respecto a autenticación y qué queda para 001? [Completeness, Spec Assumptions]
- [x] CHK005 ¿Existen requisitos para el procedimiento de respaldo de PostgreSQL? [Completeness, Spec §FR-021]
- [x] CHK006 ¿Se define la estructura modular mínima esperada de backend y frontend? [Completeness, Spec §FR-012, §FR-016, §FR-017]
- [x] CHK007 ¿Hay requisitos sobre la documentación de arranque y convenciones? [Completeness, Spec §FR-025]

## Requirement Clarity

- [x] CHK008 ¿Está cuantificado "estado saludable" y en qué tiempo debe alcanzarse? [Clarity, Spec §FR-002, §SC-001]
- [x] CHK009 ¿Se define con precisión el comportamiento de `GET /health` en cada estado (200 vs. 503) y qué dependencias evalúa? [Clarity, Spec §FR-005]
- [x] CHK010 ¿"Migraciones idempotentes" está definido de forma verificable (no produce cambios / no errores)? [Clarity, Spec §FR-011]
- [x] CHK011 ¿La paleta y sus escalas están especificadas con valores concretos y regla de contraste? [Clarity, Spec §FR-014]
- [x] CHK012 ¿"Ningún módulo importa los internos de otro" es un criterio verificable? [Clarity, Spec §FR-012]

## Requirement Consistency

- [x] CHK013 ¿La lista de buckets del spec coincide con la de la constitución (Principio III) y con `data-model.md`? [Consistency, Spec §FR-019]
- [x] CHK014 ¿El alcance "sin lógica de negocio" es coherente con todos los FR (ninguno introduce reglas de negocio)? [Consistency, Spec Requirements]
- [x] CHK015 ¿La separación 000 vs. 012 (ClickHouse/Airflow/`landing-zone`) es consistente en spec, plan y data-model? [Consistency, Spec §FR-020]

## Acceptance Criteria Quality

- [x] CHK016 ¿Cada Success Criterion es medible y objetivo (tiempos, conteos, códigos HTTP)? [Measurability, Spec §SC-001..§SC-008]
- [x] CHK017 ¿Existe un criterio medible para la modularidad (verificación por diff)? [Measurability, Spec §SC-005]
- [x] CHK018 ¿El criterio de contraste AA es objetivamente verificable? [Measurability, Spec §SC-004]

## Scenario & Edge Case Coverage

- [x] CHK019 ¿Se cubren los escenarios de fallo de arranque (puerto ocupado, `.env` ausente, DB no lista)? [Coverage, Spec Edge Cases]
- [x] CHK020 ¿Se cubre la re-ejecución de migraciones a medias y el re-arranque de MinIO con buckets existentes? [Edge Case, Spec Edge Cases]
- [x] CHK021 ¿Se cubre la persistencia de datos tras `down`/`up`? [Coverage, Spec §SC-007]
- [x] CHK022 ¿Se aborda el acceso anónimo denegado a los buckets privados? [Edge Case, Spec §FR-019, §SC-006]

## Non-Functional Requirements

- [x] CHK023 ¿Están especificados los requisitos de seguridad de secretos (solo `.env`, `.env.example` sin valores)? [Completeness, Spec §FR-003]
- [x] CHK024 ¿Se fija el objetivo de rendimiento heredado (CRUD < 1 s) y el de `/health`? [Clarity, Spec §FR-022]
- [x] CHK025 ¿Hay requisito de que el backend exponga OpenAPI navegable? [Completeness, Spec §FR-023]

## Dependencies & Assumptions

- [x] CHK026 ¿Se documenta la dependencia de Docker Desktop y el entorno monositio de desarrollo? [Assumption, Spec Assumptions]
- [x] CHK027 ¿Se valida la suposición de que el esquema de negocio llega por migraciones por feature (sin `01_operativo_postgres.sql` monolítico)? [Assumption, Spec Assumptions]
- [x] CHK028 ¿Se documenta la dependencia de la skill `ui-ux-pro-max` para tokens/Tailwind? [Dependency, Spec Assumptions]

## Ambiguities & Conflicts

- [x] CHK029 ¿Queda claro si `operacion` se siembra o no (el spec dice "vacías de datos de negocio")? [Ambiguity, Spec §FR-009, §FR-010 → resuelto en data-model.md: enum de dominio sembrado]
- [x] CHK030 ¿Hay conflicto entre "servido directo a la app" y "vía endpoint autenticado" para algún bucket? [Conflict, Spec §FR-019 → resuelto: 2 públicos, 2 privados]

## Notes

- CHK029/CHK030 se resolvieron en `data-model.md` y en la redacción final de `FR-019`; se listan para trazabilidad.
