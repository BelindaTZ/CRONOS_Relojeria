# Feature Specification: Plataforma de Datos Táctico-Estratégica (ELT)

**Feature Branch**: `012-plataforma-datos-tactico-estrategico`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Agregar ClickHouse y Airflow al docker-compose y el bucket `landing-zone` al MinIO existente; construir desde cero los DAGs del flujo ELT (Extract desde PostgreSQL → Load raw a `landing-zone` → Load a ClickHouse → Transform in-warehouse) y el modelo de warehouse que soporta todos los reportes analíticos de §4.11.2. La app operativa no debe depender de estos servicios para funcionar."

## Trazabilidad

Esta feature es la infraestructura analítica que habilita los reportes complejos de `especificacion_sistema_relojeria.md` §4.11.2 y el panel de Gerencia de §4.11.3. Su justificación de negocio es la sección 4.11.2 completa; las citas apuntan además a Const. Ppio III (separación de motores y flujo ELT) y a Const. "Flujo de Trabajo" §012 (qué construye esta feature de infraestructura).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Levantar la plataforma analítica (Priority: P1)

Con el mismo `docker-compose.yml`, se levantan ClickHouse y Airflow (webserver + scheduler, `LocalExecutor`) y se crea el bucket `landing-zone` en el MinIO ya provisionado por 000; el resto del stack sigue funcionando igual.

**Why this priority**: Sin estos servicios no hay warehouse ni orquestación; es la base de 013.

**Independent Test**: Levantar el stack y verificar que ClickHouse y Airflow están saludables, que existe `landing-zone` y que `GET /health` de 000 sigue en 200.

**Acceptance Scenarios**:

1. **Given** el stack de 000 en marcha, **When** se aplica esta feature y se levanta, **Then** ClickHouse y Airflow quedan saludables y `landing-zone` existe junto a los buckets de 000.
2. **Given** la plataforma analítica detenida, **When** se usa la app operativa, **Then** funciona con normalidad.

---

### User Story 2 - Extracción a la zona de aterrizaje (Priority: P1)

Un DAG de Airflow extrae, en solo lectura, los datos operativos de PostgreSQL y los deposita como archivos raw en `landing-zone`, que nunca se consulta como fuente de negocio.

**Why this priority**: Es el paso "Extract → Load raw" del flujo ELT (Const. Ppio III).

**Independent Test**: Ejecutar el DAG de extracción y verificar los archivos raw en `landing-zone` y que PostgreSQL no fue modificado.

**Acceptance Scenarios**:

1. **Given** datos operativos en PostgreSQL, **When** corre el DAG de extracción, **Then** aparecen los archivos raw en `landing-zone` con marca de la corrida.
2. **Given** el DAG de extracción, **When** se ejecuta, **Then** no realiza ninguna escritura sobre PostgreSQL.

---

### User Story 3 - Carga y transformación en ClickHouse (Priority: P1)

Un DAG carga desde `landing-zone` a ClickHouse y ejecuta las transformaciones in-warehouse que producen los modelos de agregación para los reportes de §4.11.2.

**Why this priority**: Es el paso "Load → Transform in-warehouse" y lo que 013 consume.

**Independent Test**: Tras una corrida completa, consultar en ClickHouse un modelo (p. ej. margen por marca) y compararlo con el operativo.

**Acceptance Scenarios**:

1. **Given** archivos raw en `landing-zone`, **When** corre el DAG de carga+transformación, **Then** los modelos de §4.11.2 quedan poblados en ClickHouse.
2. **Given** una corrida ya ejecutada, **When** se vuelve a ejecutar, **Then** no se duplican filas (idempotencia).

---

### User Story 4 - Incrementalidad y frescura (Priority: P2)

La extracción es incremental (watermark por tabla) y reprocesable; el pipeline expone su estado (última corrida exitosa, frescura de datos) para que 013 muestre "datos actualizados a HH:MM".

**Why this priority**: Evita reprocesar todo y da transparencia al usuario (Const. Ppio IX "carga asíncrona").

**Independent Test**: Insertar datos nuevos en el origen, correr el pipeline y verificar que solo se cargó el delta y que la frescura se actualizó.

**Acceptance Scenarios**:

1. **Given** una corrida previa con watermark, **When** se añaden registros y corre el pipeline, **Then** solo se procesan los nuevos.
2. **Given** una corrida fallida, **When** se reintenta, **Then** termina sin duplicar datos.
3. **Given** una venta anulada en el origen, **When** corre el pipeline, **Then** el warehouse refleja la anulación en la siguiente actualización.
4. **Given** el pipeline con corrida horaria, **When** un usuario pulsa "actualizar ahora", **Then** se dispara una corrida manual fuera del horario; **When** se ajusta la frecuencia en configuración, **Then** las corridas siguientes usan el nuevo intervalo.

### Edge Cases

- ¿Qué pasa si ClickHouse está caído durante una corrida?
- ¿Qué pasa si dos corridas del mismo DAG se solapan?
- ¿Qué pasa si `landing-zone` crece sin límite?
- ¿Qué pasa cuando una feature futura añade tablas nuevas en PostgreSQL?
- ¿Qué pasa con datos que llegan con fecha futura o zona horaria distinta?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Esta feature DEBE agregar al `docker-compose.yml` los servicios ClickHouse y Airflow (webserver + scheduler, `LocalExecutor`) y crear el bucket `landing-zone` en el MinIO ya provisionado por 000. [Const. "Flujo de Trabajo" §012; Const. "Stack"]
- **FR-002**: Ninguna feature fuera de 000 y 012 modifica el `docker-compose.yml`, la configuración de Airflow, los DAGs ni el esquema de ClickHouse. [Const. "Flujo de Trabajo"]
- **FR-003**: El flujo DEBE ser ELT (no ETL): Extract desde PostgreSQL → Load raw a `landing-zone` → Load a ClickHouse → Transform in-warehouse. [Const. Ppio III]
- **FR-004**: El bucket `landing-zone` contiene el raw del Extract y NUNCA se consulta como fuente de negocio. [Const. Ppio III]
- **FR-005**: La orquestación DEBE realizarse con DAGs de Airflow construidos en esta feature, con tareas explícitas y nombradas por fase — Extract (desde PostgreSQL), Load raw (a `landing-zone`), Load warehouse (a ClickHouse), Transform (in-warehouse) — observables por separado en la UI de Airflow. [Const. "Flujo de Trabajo" §012; Const. Ppio III]
- **FR-006**: La extracción DEBE ser de solo lectura sobre PostgreSQL, sin alterar datos ni esquema operativo. [Const. Ppio III; Esp. §6]
- **FR-007**: La extracción DEBE ser incremental (watermark por tabla) y reprocesable; un reintento no duplica datos en ClickHouse. [Esp. §4.11.3; Const. Ppio VII]
- **FR-008**: El modelo de ClickHouse DEBE soportar todos los reportes analíticos de §4.11.2: mejores clientes; margen por reloj vendido; margen por servicio/OT; margen por marca y modelo; rotación de stock; piezas más usadas y su costo; productividad por técnico; valor total del inventario; comparativo costo vs. precio de venta; tiempo medio de servicio; tasa de reposición de piezas; rentabilidad neta por sucursal; tasa de conversión de citas; desviación de lubricación; aging de CxC/CxP; efectividad de fidelización y descuentos; clientes por nivel de fidelización; mermas y pérdidas. [Esp. §4.11.2]
- **FR-009**: El modelo DEBE permitir filtros por periodo, sucursal, marca y técnico en esos reportes. [Esp. §4.11.3]
- **FR-010**: El pipeline DEBE exponer su estado (última corrida exitosa por dominio, frescura de datos) de forma consultable por 013. [Const. Ppio IX; Esp. §4.11.3]
- **FR-011**: Si ClickHouse o Airflow no están disponibles, la aplicación operativa (001–011) DEBE seguir funcionando sin degradación; solo los reportes analíticos se ven afectados. [Const. Ppio IX; Const. Ppio III]
- **FR-012**: El `landing-zone` DEBE tener una política de retención para no crecer sin límite. [Const. Ppio VII]
- **FR-013**: Las anulaciones y bajas en el origen (venta anulada, merma, cambio de nivel) DEBEN reflejarse en el warehouse en la siguiente corrida. [Esp. §6; §4.11.2]
- **FR-014**: El acceso a Airflow y a ClickHouse DEBE protegerse con credenciales vía `.env`, nunca hardcodeadas. [Const. Ppio IX]
- **FR-015**: Se DEBE documentar y proveer respaldo del esquema y los datos de ClickHouse y de los DAGs. [Esp. §6 "Respaldo de datos"]
- **FR-016**: NO se implementa forecasting ni ML en el warehouse en esta fase. [Const. "Stack"]
- **FR-017**: Las corridas DEBEN ejecutarse cada hora por defecto, con un disparo manual disponible ("actualizar ahora") y la frecuencia ajustable por configuración. [Esp. §4.11.3; decisión del negocio]
- **FR-018**: El pipeline DEBE tolerar la aparición de tablas o columnas nuevas en el origen sin romperse; los dominios sin modelo simplemente no se cargan hasta añadirlo. [Const. Ppio VI]

### Key Entities *(include if feature involves data)*

- **ArchivoLandingZone**: raw de una corrida, por dominio, versionado; nunca fuente de negocio.
- **ModeloWarehouse (ClickHouse)**: tablas de hechos y dimensiones que cubren §4.11.2, con claves de periodo, sucursal, marca y técnico.
- **CorridaPipeline**: dominio, inicio, fin, estado, filas procesadas, watermark.
- **EstadoFrescura**: por dominio, timestamp del dato más reciente cargado; consultable por 013.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al levantar el stack, ClickHouse, Airflow y `landing-zone` quedan disponibles y `GET /health` de 000 sigue en 200.
- **SC-002**: Tras una corrida completa, cada reporte de §4.11.2 tiene su modelo poblado en ClickHouse y devuelve resultados coherentes con el operativo.
- **SC-003**: Reejecutar una corrida no duplica filas.
- **SC-004**: Con ClickHouse detenido, la app operativa responde con normalidad; solo los reportes analíticos fallan de forma controlada.
- **SC-005**: El estado de frescura es consultable y permite a 013 mostrar la hora de la última actualización.
- **SC-006**: Una venta anulada en el origen se refleja en el warehouse en la siguiente corrida.
- **SC-007**: Una revisión estática no encuentra credenciales hardcodeadas en los DAGs ni en las configuraciones.

## Assumptions

- 000 está implementada (MinIO ya existe; esta feature solo añade el bucket `landing-zone`).
- Las features 001–011 existen como fuente de extracción; 012 puede desarrollarse en paralelo pero necesita datos operativos para validar los modelos.
- El volumen del negocio es pequeño (§4.11.3): el diseño evita sobre-ingeniería (sin streaming, sin CDC complejo) — Const. Ppio VII.
- La frecuencia por defecto es horaria; el negocio puede ajustarla y disparar corridas manuales cuando lo necesite (decisión del negocio).
- La visualización (gráficos, panel de Gerencia, KPIs) es responsabilidad de 013; 012 solo entrega el warehouse y su estado.
- Las herramientas de exploración de ClickHouse son opcionales.
- El forecasting/ML queda fuera de alcance (Const. "Stack").
