# Requirements Quality Checklist: Notificaciones Automatizadas por Email

**Purpose**: Validar la calidad de los requisitos del `spec.md` de la feature 014.
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 ¿Están los tres disparadores automáticos definidos (OT, cupón/nivel, recordatorio de cita)? [Completeness, Spec §FR-002, §FR-003, §FR-004]
- [x] CHK002 ¿Se define que 014 gestiona también las plantillas de 001 y 008? [Completeness, Spec §FR-004a]
- [x] CHK003 ¿Se define el ciclo de estados de un envío? [Completeness, Data-model; Spec §FR-007]
- [x] CHK004 ¿Se define la cola con reintentos y el backoff? [Completeness, Spec §FR-008; research D2]
- [x] CHK005 ¿Se define el opt-out por tipo y las excepciones críticas? [Completeness, Spec §FR-011; research D6]
- [x] CHK006 ¿Se define la deduplicación por disparo? [Completeness, Spec §FR-012; research D5]
- [x] CHK007 ¿Se define el reporte operativo de envíos? [Completeness, Spec §FR-014]

## Requirement Clarity

- [x] CHK008 ¿"Desacoplado del camino transaccional" está definido (INSERT local + worker)? [Clarity, Spec §FR-017; research D3]
- [x] CHK009 ¿"Ningún disparo se pierde silenciosamente" es verificable (todo disparo → un `envio` con estado)? [Clarity, Spec §FR-008]
- [x] CHK010 ¿La antelación del recordatorio es un parámetro configurable? [Clarity, Spec §FR-004]
- [x] CHK011 ¿"Sin destinatario" evita reintentos en bucle? [Clarity, Spec §FR-013]
- [x] CHK012 ¿"Plantilla cuidada" se ata a la identidad visual (Ppio XI/XII)? [Clarity, Spec §FR-006]

## Requirement Consistency

- [x] CHK013 ¿El envío usa `shared/correo` de 001 de forma consistente (no un cliente nuevo)? [Consistency, Spec §FR-001, §FR-004a]
- [x] CHK014 ¿La cancelación del recordatorio ante cita cancelada es consistente con 007? [Consistency, Spec §FR-010; research D8]
- [x] CHK015 ¿El worker NO usa Airflow (reservado a 012)? [Consistency, Plan Complexity Tracking]
- [x] CHK016 ¿Los eventos de dominio que disparan los correos son los que 006/007/008 emiten? [Consistency, research D1]

## Acceptance Criteria Quality

- [x] CHK017 ¿Cada Success Criterion es medible? [Measurability, Spec §SC-001..§SC-008]
- [x] CHK018 ¿"Confirmar venta/OT/cita nunca falla por email" es objetivamente verificable? [Measurability, Spec §SC-005]

## Scenario & Edge Case Coverage

- [x] CHK019 ¿Se cubre el email con formato inválido? [Edge Case, Spec Edge Cases]
- [x] CHK020 ¿Se cubre el proveedor caído durante horas? [Coverage, Spec Edge Cases]
- [x] CHK021 ¿Se cubre una OT que rebota entre estados en minutos? [Edge Case, Spec Edge Cases]
- [x] CHK022 ¿Se cubre la zona horaria al programar un recordatorio? [Edge Case, Spec Edge Cases]
- [x] CHK023 ¿Se cubre el fallo de email mientras se confirma una venta / se cierra una OT? [Coverage, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK024 ¿Las credenciales del proveedor vienen de `.env`? [Security, Spec §FR-001]
- [x] CHK025 ¿Cada envío queda auditado (destinatario, tipo, origen, timestamps, estado)? [Security, Spec §FR-015]
- [x] CHK026 ¿Las plantillas solo las edita Gerencia General / delegado? [Security, Spec §FR-016]
- [x] CHK027 ¿Hay objetivo de latencia para el disparo (< 1 min) sin bloquear la transacción? [Performance, Plan Technical Context]

## Dependencies & Assumptions

- [x] CHK028 ¿Se documenta que la capacidad de envío ya existe desde 001 y 014 construye el módulo completo encima? [Dependency, Spec Assumptions]
- [x] CHK029 ¿Se documenta que no hay procesamiento de correo entrante? [Assumption, Spec Assumptions]
- [x] CHK030 ¿Se documenta que los recordatorios de mantenimiento preventivo quedan fuera de alcance (§8)? [Assumption, Spec §FR-018]

## Ambiguities & Conflicts

- [x] CHK031 ¿Está claro qué es el "hito" para la dedup de `ot_estado` (estado destino)? [Ambiguity → resuelto, research D5]
- [x] CHK032 ¿Está claro que el worker es un poller in-proceso y no Airflow? [Ambiguity → resuelto, Plan/research D2]
