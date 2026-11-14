# Feature Specification: Bootstrap de Infraestructura

**Feature Branch**: `000-bootstrap-infraestructura`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Levantar el esqueleto ejecutable del sistema: docker-compose con PostgreSQL, backend FastAPI (health-check), frontend Vue 3 + Vite + Tailwind con la paleta del Principio XI, MinIO con los buckets `reloj-imagenes` y `comprobantes-venta`, Alembic con migración inicial y tablas base de RBAC (rol, módulo, permiso) vacías. Estructura modular de backend y frontend con carpeta `shared/`. Sin features de negocio."

## Trazabilidad

Esta feature es el sustrato de ejecución de **todos** los módulos funcionales de la especificación (`especificacion_sistema_relojeria.md` §4.1–§4.12): su justificación de negocio es habilitar la construcción de la sección 4 completa. Las citas puntuales de cada requisito apuntan a los requisitos no funcionales (§6), a los reportes (§4.11), al modelo de permisos (§3.1) y a la constitución (`.specify/memory/constitution.md`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Levantar el stack completo con un comando (Priority: P1)

Un desarrollador clona el repositorio, copia `.env.example` a `.env` y con un único comando levanta PostgreSQL, backend, frontend y MinIO, todos en estado saludable, sin pasos manuales adicionales.

**Why this priority**: Sin una plataforma ejecutable reproducible, ninguna feature de negocio (001–014) puede empezar. Es la dependencia raíz de todo el proyecto (Const. "Flujo de Trabajo").

**Independent Test**: Desde un checkout limpio, ejecutar el comando de arranque y verificar que los cuatro servicios reportan estado saludable y que la app responde.

**Acceptance Scenarios**:

1. **Given** un repositorio recién clonado y `.env` creado desde el ejemplo, **When** el desarrollador ejecuta el comando de arranque, **Then** los servicios PostgreSQL, backend, frontend y MinIO quedan saludables sin intervención manual.
2. **Given** el stack levantado, **When** se detiene y se vuelve a levantar, **Then** los datos de PostgreSQL y los objetos de MinIO se conservan.
3. **Given** un puerto del host ya ocupado, **When** se intenta levantar, **Then** el fallo es explícito e indica qué servicio y puerto están en conflicto.

---

### User Story 2 - Salud del backend y shell del frontend (Priority: P2)

El backend expone un endpoint de salud que reporta la conectividad a PostgreSQL y a MinIO; el frontend muestra un shell navegable con la barra de navegación horizontal superior fija, pintado con la paleta oficial.

**Why this priority**: Da una señal verificable de que la plataforma funciona y fija la identidad visual y de navegación que todas las features heredan (Const. Ppio XI).

**Independent Test**: Llamar al endpoint de salud con y sin PostgreSQL disponible; abrir el frontend y comprobar el shell y los colores.

**Acceptance Scenarios**:

1. **Given** el stack saludable, **When** se llama `GET /health`, **Then** responde 200 con el estado de PostgreSQL y de MinIO.
2. **Given** PostgreSQL detenido, **When** se llama `GET /health`, **Then** responde 503 indicando la dependencia caída.
3. **Given** el frontend cargado, **When** se inspecciona la barra superior, **Then** usa el color Primary `#0F172A` y el texto cumple contraste AA (≥4.5:1).

---

### User Story 3 - Esquema base de RBAC vacío y migraciones idempotentes (Priority: P2)

Al aplicar las migraciones se crean las tablas `rol`, `modulo`, `permiso` y sus asociaciones de dos niveles, vacías de datos de negocio; re-aplicar las migraciones no produce cambios.

**Why this priority**: 001 (auth-rbac-configuracion) construye sobre este esquema; debe existir antes pero sin datos, para no adelantar alcance (Const. "Flujo de Trabajo" §000).

**Independent Test**: Aplicar migraciones sobre una base limpia, inspeccionar tablas, re-aplicar y comprobar ausencia de diffs; revertir a base y comprobar limpieza.

**Acceptance Scenarios**:

1. **Given** una base limpia, **When** se aplican las migraciones, **Then** existen `rol`, `modulo`, `permiso`, la asociación rol↔módulo y la asociación rol↔módulo↔operación, todas sin filas de negocio.
2. **Given** una base ya migrada, **When** se vuelven a aplicar las migraciones, **Then** no hay cambios ni errores.
3. **Given** una base migrada, **When** se revierte a base, **Then** las tablas se eliminan sin residuos.

---

### User Story 4 - Estructura modular impuesta (Priority: P3)

El repositorio impone la organización por módulos de negocio con una carpeta `shared/` para código reutilizable, tanto en backend como en frontend, de modo que añadir una feature nueva no obliga a tocar módulos existentes.

**Why this priority**: Evita el código espagueti desde el primer commit (Const. Ppio X, NON-NEGOTIABLE).

**Independent Test**: Añadir un módulo dummy en backend y frontend y comprobar que no se modificó ningún archivo de otro módulo.

**Acceptance Scenarios**:

1. **Given** la estructura del repo, **When** se revisa `backend/src/`, **Then** existe `shared/` y al menos un módulo de ejemplo con capas router → service → repository.
2. **Given** la estructura del repo, **When** se revisa `frontend/src/`, **Then** existe `shared/` con la capa de servicios API centralizada, `ui/dialogs.js` y `<DialogHost>` montado en `App.vue`.
3. **Given** un módulo nuevo dummy añadido, **When** se hace diff, **Then** no hay cambios fuera de su propia carpeta y del registro de rutas.

---

### User Story 5 - MinIO con los buckets de cara a la app (Priority: P3)

MinIO arranca con los buckets `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios` y `documentos` ya creados y con su política de acceso definida; `landing-zone` no existe todavía.

**Why this priority**: 003 (fotos de relojes), 009 (comprobantes/certificados), 001 (fotos de perfil) y 002/008/011 (documentos de soporte) los necesitan; `landing-zone` es exclusivo de 012 (Const. Ppio III, "Flujo de Trabajo").

**Independent Test**: Listar buckets tras el arranque; subir y recuperar un objeto de prueba en cada bucket de cara a la app.

**Acceptance Scenarios**:

1. **Given** MinIO levantado, **When** se listan los buckets, **Then** existen `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios` y `documentos`, y no existe `landing-zone`.
2. **Given** el bucket `reloj-imagenes`, **When** se sube y se solicita un objeto de prueba, **Then** se recupera correctamente.
3. **Given** los buckets `comprobantes-venta` y `documentos`, **When** un cliente no autenticado solicita un objeto, **Then** se le deniega el acceso (solo vía endpoint autenticado).
4. **Given** un re-arranque del stack, **When** MinIO vuelve a iniciar, **Then** no falla por buckets ya existentes.

### Edge Cases

- ¿Qué pasa cuando un puerto del host requerido ya está en uso?
- ¿Cómo se comporta el backend si arranca antes de que PostgreSQL acepte conexiones?
- ¿Qué pasa si `.env` falta o está incompleto? (debe fallar con mensaje claro, no crash silencioso)
- ¿Qué pasa si `alembic upgrade head` se corta a la mitad y se vuelve a ejecutar?
- ¿Qué pasa si los volúmenes persistentes se llenan o se borran?
- ¿Qué pasa si MinIO se reinicia con los buckets ya creados?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El repositorio DEBE proveer un `docker-compose.yml` único que defina los servicios PostgreSQL 16, backend, frontend y MinIO. [Const. "Stack y Restricciones Técnicas"; Const. "Flujo de Trabajo" §000]
- **FR-002**: El stack completo DEBE poder levantarse con un solo comando y alcanzar estado saludable sin más pasos manuales que crear `.env`. [Const. "Flujo de Trabajo" §000; Esp. §10 (base ejecutable para diseño e implementación)]
- **FR-003**: Todas las credenciales y secretos DEBEN provenir de `.env`, nunca hardcodeados; `.env.example` se versiona sin valores reales. [Const. Ppio IX "Seguridad"]
- **FR-004**: El backend DEBE exponer únicamente API REST/JSON y NO renderizar HTML. [Const. Ppio V]
- **FR-005**: El backend DEBE exponer `GET /health` que devuelva 200 e incluya el estado de conectividad a PostgreSQL y a MinIO, y 503 si una dependencia crítica no responde. [Const. "Flujo de Trabajo" §000; Esp. §6 "Respaldo de datos" / continuidad]
- **FR-006**: El backend DEBE esperar/reintentar la disponibilidad de PostgreSQL antes de aceptar tráfico. [Esp. §6 (robustez / escalabilidad multi-sucursal desde el modelo)]
- **FR-007**: El proyecto DEBE usar Alembic; la migración inicial crea el esquema base de RBAC. [Const. "Flujo de Trabajo" §000]
- **FR-008**: La migración inicial DEBE crear `rol`, `modulo`, `permiso`, la asociación rol↔módulo (acceso al módulo) y la asociación rol↔módulo↔operación (permiso granular), modelando que el acceso al módulo es prerrequisito del permiso granular. [Esp. §3.1; Const. Ppio IV]
- **FR-009**: El catálogo de operaciones DEBE contener exactamente Crear, Consultar, Editar, Eliminar. [Esp. §3.1]
- **FR-010**: Las tablas de RBAC se crean VACÍAS de datos de negocio (sin roles, módulos ni permisos poblados); su carga es responsabilidad de 001. [Const. "Flujo de Trabajo" §000]
- **FR-011**: `alembic upgrade head` sobre una base ya migrada NO produce cambios ni errores; `alembic downgrade base` deja la base limpia. [Esp. §6]
- **FR-012**: El backend DEBE organizarse por capas (router → service → repository) y por módulos de negocio, con `backend/src/shared/` para config, acceso a datos, utilidades, excepciones y schemas base; ningún módulo importa los internos de otro. [Const. Ppio X (NON-NEGOTIABLE)]
- **FR-013**: El bootstrap DEBE incluir un módulo plantilla/ejemplo que demuestre la estructura de capas para que las features nuevas lo repliquen. [Const. Ppio X, Ppio XII]
- **FR-014**: El frontend DEBE ser Vue 3 + Vite + Tailwind, con Tailwind configurado con la paleta del Principio XI (Primary `#0F172A`, Secondary `#B48E38`, Tertiary `#059669`, Neutral `#64748B`, Danger `#DC2626`, Warning `#D97706`), cada color con su escala 900→50. [Const. Ppio XI; Const. "Stack"]
- **FR-015**: El frontend DEBE renderizar un shell con la barra de navegación horizontal superior fija (sin sidebar) y las categorías de primer nivel previstas, aunque sin contenido de módulos. [Const. Ppio XI "Navegación"]
- **FR-016**: El frontend DEBE organizarse por módulos de negocio con `frontend/src/shared/` para componentes UI, utilidades y la capa de servicios API centralizada; ninguna llamada a la API vive fuera de esa capa. [Const. Ppio X, Ppio V]
- **FR-017**: El frontend DEBE incluir el helper compartido `frontend/src/shared/ui/dialogs.js` (`confirm()`/`prompt()`) con `<DialogHost>` montado una vez en `App.vue`, y el stub de `frontend/src/shared/exportar.js`. [Const. Ppio XI "Diálogos" y "Exportación de reportes"]
- **FR-018**: La configuración de tokens y de Tailwind producida por la skill `ui-ux-pro-max` DEBE quedar como base compartida; ninguna feature redefine estilo de componente por su cuenta. [Const. Ppio XII (NON-NEGOTIABLE)]
- **FR-019**: MinIO DEBE arrancar con los buckets `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios` y `documentos` creados y con su política de acceso definida: `reloj-imagenes` y `perfil-usuarios` servidos directo a la app; `comprobantes-venta` y `documentos` solo vía endpoint autenticado. [Const. Ppio III; Const. "Flujo de Trabajo" §000; Esp. §4.4, §4.7, §7, §4.12]
- **FR-020**: El bucket `landing-zone` y los servicios ClickHouse y Airflow NO se crean en esta feature. [Const. "Flujo de Trabajo" §012]
- **FR-021**: Se DEBE documentar y proveer un procedimiento de respaldo (backup) periódico de PostgreSQL. [Esp. §6 "Respaldo de datos (backup) periódico"]
- **FR-022**: La plataforma DEBE fijar el objetivo de rendimiento que las features heredan: operaciones CRUD estándar <1s en entorno de desarrollo. [Const. Ppio IX "Rendimiento"]
- **FR-023**: El backend DEBE exponer documentación OpenAPI navegable de su API. [Const. Ppio V; Esp. §10]
- **FR-024**: pgAdmin PUEDE incluirse como servicio opcional del `docker-compose.yml`. [Const. "Stack"]
- **FR-025**: El repositorio DEBE incluir un README de arranque y un documento de convenciones (snake_case backend, camelCase frontend). [Const. Ppio X]

### Key Entities *(include if feature involves data)*

- **Rol**: agrupación de permisos asignable a usuarios. Creada vacía.
- **Módulo**: unidad funcional a la que se concede o no acceso (Citas, Inventario, etc.). Creado vacío.
- **Operación**: catálogo fijo Crear / Consultar / Editar / Eliminar.
- **Permiso (acceso a módulo)**: asociación rol × módulo. Prerrequisito del permiso granular. Creada vacía.
- **Permiso (granular)**: asociación rol × módulo × operación. Creada vacía.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Desde un repo limpio, crear `.env` y ejecutar el comando de arranque deja los cuatro servicios saludables en menos de 5 minutos en una máquina de desarrollo estándar.
- **SC-002**: `GET /health` responde 200 con el estado de PostgreSQL y MinIO; con PostgreSQL detenido responde 503.
- **SC-003**: Tras aplicar migraciones existen las cinco estructuras de RBAC vacías; re-aplicarlas no genera diffs y revertir a base las elimina sin residuos.
- **SC-004**: El shell del frontend carga con la barra superior y un chequeo automatizado confirma contraste AA para texto sobre Primary y sobre Secondary.
- **SC-005**: Añadir un módulo dummy en backend y en frontend no modifica archivos de otros módulos (verificado por diff).
- **SC-006**: MinIO expone `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios` y `documentos`; subir y recuperar un objeto de prueba funciona en cada uno; `comprobantes-venta` y `documentos` rechazan el acceso no autenticado; `landing-zone` no existe.
- **SC-007**: Detener y relevantar el stack conserva el 100% de los datos de PostgreSQL y de MinIO.
- **SC-008**: Una revisión estática no encuentra ningún secreto hardcodeado: todos provienen de `.env`.

## Assumptions

- Docker Desktop está instalado en la máquina de desarrollo (Const. "Stack").
- Entorno de desarrollo local monositio; sin hardening de producción, TLS ni orquestación multi-nodo en esta fase.
- El login, la tabla `usuario`, el guard RBAC por endpoint y la carga de la matriz de permisos los entrega 001; 000 solo deja el esquema base vacío.
- El esquema de negocio (relojes, citas, etc.) llega desde 002+ mediante migraciones Alembic por feature; no hay un `01_operativo_postgres.sql` monolítico — el modelo operativo se construye incrementalmente y cada feature documenta su porción en su `data-model.md`.
- La skill `ui-ux-pro-max` está disponible en la ruta del Principio XII y define los tokens y componentes base.
- SendGrid, `reportlab`/`weasyprint`, ClickHouse y Airflow no se configuran en esta feature.
- El bucket `landing-zone` se añade en 012 sobre el MinIO que provisiona esta feature.
