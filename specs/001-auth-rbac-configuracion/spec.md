# Feature Specification: Autenticación, RBAC de Dos Niveles y Configuración

**Feature Branch**: `001-auth-rbac-configuracion`

**Created**: 2026-09-09

**Status**: Implemented

**Input**: User description: "Usuarios (con autoservicio de datos propios y restablecimiento de contraseña), roles y la matriz de permisos de dos niveles (acceso a módulo + operación CRUD), con excepciones por usuario. Login JWT y un guard reutilizable que autoriza cada endpoint. Entidad `sucursal` (inactivar exige motivo y avisa a su personal) y su scoping de datos. Catálogos (`medio_pago`, categorías de gasto, canales de cita) y parámetros configurables de la sección 9, editables solo por Gerencia General y auditados, con recálculo en cascada. Capacidad compartida de envío de correo con plantillas cuidadas."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Definir roles y la matriz de permisos (Priority: P1)

Gerencia General crea roles y, para cada rol, define a qué módulos entra y qué operaciones (Crear/Consultar/Editar/Eliminar) puede realizar en cada módulo habilitado.

**Why this priority**: El RBAC de dos niveles es NON-NEGOTIABLE y prerrequisito de que cualquier otra feature exponga endpoints con autorización (Const. Ppio IV, Ppio IX).

**Independent Test**: Crear un rol con acceso a un subconjunto de módulos y operaciones, asignarlo a un usuario y verificar que ese usuario ve y puede hacer exactamente eso.

**Acceptance Scenarios**:

1. **Given** el módulo de Configuración, **When** Gerencia General habilita "Citas" para el rol Vendedor con Crear+Consultar+Editar pero no Eliminar, **Then** un usuario Vendedor puede crear/consultar/editar citas y recibe 403 al intentar eliminar.
2. **Given** un rol sin acceso al módulo "Contable", **When** un usuario con ese rol llama a cualquier endpoint contable, **Then** recibe 403 aunque tuviera marcada la operación.
3. **Given** una operación marcada en un módulo no habilitado, **When** se guarda la matriz, **Then** el sistema indica que el acceso al módulo es prerrequisito.

---

### User Story 2 - Iniciar sesión y autorizar cada petición (Priority: P1)

Un usuario inicia sesión con sus credenciales y recibe un token; cada petición a un endpoint protegido se autoriza contra su acceso a módulo y operación.

**Why this priority**: Sin login ni guard no hay forma segura de exponer las features de negocio (Const. Ppio IX).

**Independent Test**: Autenticarse, llamar endpoints con y sin permiso, y con token ausente/expirado.

**Acceptance Scenarios**:

1. **Given** credenciales válidas, **When** el usuario hace login, **Then** recibe un token con vigencia definida y puede renovarlo.
2. **Given** un token válido sin el permiso requerido, **When** llama al endpoint, **Then** recibe 403; **Given** ningún token o uno expirado, **Then** recibe 401.
3. **Given** un usuario cuyo rol cambió durante la sesión, **When** hace la siguiente petición, **Then** la autorización refleja el rol actual.

---

### User Story 3 - Autoservicio del usuario (Priority: P1)

Cada usuario puede ver sus propios datos y editar un subconjunto acotado: su email y su foto de perfil. No puede cambiar su rol, sus permisos, sus sucursales asignadas ni su identificación.

**Why this priority**: Necesidad expresada por el negocio; reduce carga administrativa y mantiene datos de contacto al día. El técnico también es un usuario y usa este mismo autoservicio para sus datos de contacto (005 no permite que edite su costo ni sus certificaciones).

**Independent Test**: Como usuario no administrador, ver los datos propios, cambiar el email y subir una foto de perfil; intentar cambiar el rol propio y verificar el rechazo.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado, **When** abre "Mis datos", **Then** ve su identificación, nombre, rol, sucursales, email y foto (identificación, nombre, rol y sucursales en solo lectura).
2. **Given** el autoservicio, **When** el usuario cambia su email o sube una foto de perfil, **Then** se guarda (la foto en el bucket `perfil-usuarios`) y queda auditado.
3. **Given** el autoservicio, **When** el usuario intenta modificar su rol o sus permisos, **Then** el sistema lo rechaza.

---

### User Story 4 - Cambio y restablecimiento de contraseña (Priority: P1)

Un usuario que conoce su contraseña puede cambiarla. Un usuario que la olvidó solicita el restablecimiento: el sistema genera una contraseña temporal de un solo uso, la envía al email registrado, y obliga a cambiarla en el primer inicio de sesión.

**Why this priority**: Requisito de seguridad y de operación diaria (Const. Ppio IX).

**Independent Test**: Solicitar restablecimiento, recibir la contraseña temporal por email, iniciar sesión y comprobar que se fuerza el cambio.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado, **When** cambia su contraseña indicando la actual y una nueva válida, **Then** la contraseña se actualiza.
2. **Given** un usuario que olvidó su contraseña, **When** solicita el restablecimiento con su identificación/email, **Then** recibe por email una contraseña temporal de un solo uso con caducidad.
3. **Given** una contraseña temporal vigente, **When** el usuario inicia sesión con ella, **Then** el sistema exige fijar una contraseña nueva antes de permitir cualquier otra operación.
4. **Given** una contraseña temporal caducada o ya usada, **When** se intenta iniciar sesión con ella, **Then** el sistema la rechaza.

---

### User Story 5 - Sucursales y catálogos de configuración organizativa (Priority: P2)

Gerencia General administra el catálogo de sucursales (nombre, dirección, responsable, estado) y los catálogos: `medio_pago`, categorías de gasto operativo y canales de solicitud de citas. Inactivar una sucursal exige un motivo obligatorio y avisa por email a los usuarios y técnicos asignados a ella.

**Why this priority**: `sucursal` es entidad transversal usada desde 003 en adelante; los catálogos son requisito de §9.3; el aviso al inactivar es una necesidad del negocio.

**Independent Test**: Crear una sucursal y una categoría de gasto; inactivar una sucursal con personal asignado y verificar el motivo obligatorio y los avisos generados.

**Acceptance Scenarios**:

1. **Given** el módulo de Configuración, **When** se crea una sucursal activa, **Then** queda disponible como opción en selectores de otras features.
2. **Given** una sucursal con usuarios y técnicos asignados, **When** se intenta inactivarla sin motivo, **Then** el sistema lo impide; **When** se inactiva con un motivo, **Then** el motivo queda registrado y se genera un aviso por email (con plantilla cuidada) a cada usuario y técnico de esa sucursal.
3. **Given** el catálogo de canales de cita, **When** Gerencia General lo edita, **Then** los valores disponibles cambian sin tocar código (§9.3).
4. **Given** el catálogo `medio_pago`, **When** se consulta, **Then** contiene Efectivo, Transferencia Bancaria, Cheque y Tarjeta vía datáfono.

---

### User Story 6 - Parámetros configurables, recálculo y auditoría (Priority: P2)

Todo valor que dependa de una decisión de negocio (márgenes objetivo, umbrales, fórmulas de bono, niveles de fidelización, margen mínimo protegido, etc.) se gestiona como parámetro configurable con vigencia. Cambiar un parámetro recalcula en cascada todo lo abierto que depende de él; lo ya emitido y los periodos cerrados conservan su valor. Cada cambio queda auditado.

**Why this priority**: Principio transversal de §9 ("sin requerir cambios de código"), obligación de auditoría de §9.4 y §6, y regla de recálculo confirmada por el negocio.

**Independent Test**: Cambiar un parámetro con dependencias abiertas y cerradas y verificar qué se recalcula y qué no, y el registro de auditoría.

**Acceptance Scenarios**:

1. **Given** un parámetro configurable, **When** Gerencia General lo modifica, **Then** se registra en auditoría el valor previo, el nuevo, el usuario y el timestamp, y se recalculan los valores derivados abiertos (bonos de periodos no cerrados, márgenes de operaciones no confirmadas, niveles de fidelización, reportes).
2. **Given** un comprobante ya emitido o un periodo contable cerrado, **When** se cambia un parámetro que los afectaba, **Then** conservan su valor histórico y el cambio queda registrado como aplicable solo hacia lo abierto.
3. **Given** un usuario que no es Gerencia General (ni delegado), **When** intenta abrir Configuración, **Then** recibe 403.

---

### User Story 7 - Scoping de datos por sucursal y por propiedad (Priority: P3)

El guard permite limitar el alcance de un endpoint a "solo mi sucursal" o "solo mis registros" según el rol, de forma transversal y reutilizable por las demás features.

**Why this priority**: §3 y §4.9 exigen que un gerente de sucursal no vea otras sucursales y que un técnico solo vea lo asignado a él.

**Independent Test**: Con datos de dos sucursales, verificar que un gerente de sucursal A no obtiene nada de B en ningún endpoint scoped.

**Acceptance Scenarios**:

1. **Given** datos en sucursales A y B, **When** un gerente de A lista registros scoped, **Then** solo obtiene los de A.
2. **Given** Gerencia General, **When** lista los mismos registros, **Then** obtiene los consolidados de todas las sucursales.
3. **Given** un técnico, **When** lista órdenes de trabajo, **Then** solo ve las asignadas a él (mecanismo reutilizado por 008).

### Edge Cases

- ¿Qué pasa al intentar borrar/desactivar el último usuario activo con rol Gerencia General? (candado anti-lockout)
- ¿Qué pasa con un token emitido antes de que se revoquen los permisos del usuario?
- ¿Qué pasa si un usuario sin sucursal asignada intenta una operación scoped por sucursal?
- ¿Qué ocurre con los permisos granulares de un módulo cuando se le retira el acceso a ese módulo? (quedan inertes, no huérfanos)
- ¿Qué pasa si se solicita el restablecimiento de contraseña de un usuario sin email registrado?
- ¿Qué pasa si se inactiva una sucursal con transferencias de inventario en tránsito o cajas abiertas?
- ¿Qué pasa con intentos de fuerza bruta de login o de restablecimiento?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE gestionar usuarios (alta, edición, activación/desactivación, asignación de rol y sucursal) con contraseña almacenada con hash fuerte. [Esp. §3, §6; Const. Ppio IX]
- **FR-002**: El sistema DEBE gestionar roles (CRUD) y asignar uno o varios roles a cada usuario. [Esp. §3, §3.1]
- **FR-003**: El sistema DEBE poblar el catálogo de módulos con los de §3.1 y permitir ampliarlo cuando una feature nueva declare su módulo. [Esp. §3.1]
- **FR-004**: El sistema DEBE permitir configurar, por rol, el acceso a cada módulo y, dentro de cada módulo habilitado, las operaciones Crear/Consultar/Editar/Eliminar de forma independiente. [Esp. §3.1; Const. Ppio IV]
- **FR-005**: El acceso al módulo DEBE ser prerrequisito del permiso granular. [Esp. §3.1; Const. Ppio IV]
- **FR-006**: El sistema DEBE permitir excepciones de permiso a nivel de usuario individual (conceder o revocar una operación sin cambiar el rol). [Esp. §3.1]
- **FR-007**: El sistema DEBE exponer un endpoint de login que emita un token JWT con vigencia configurable y un mecanismo de renovación y de cierre de sesión. [Const. Ppio IX; Const. "Stack"]
- **FR-008**: El backend DEBE proveer un guard/dependencia reutilizable que autorice cada endpoint contra (acceso a módulo + operación), devolviendo 401 sin token válido y 403 sin permiso. [Const. Ppio IX; Esp. §3.1]
- **FR-009**: Ningún endpoint de negocio (features 002+) puede exponerse sin declarar su (módulo, operación) requerido. [Const. Ppio IV]
- **FR-010**: La autorización DEBE reflejar el rol y las excepciones vigentes en el momento de cada petición. [Esp. §6]
- **FR-011**: Cada usuario DEBE poder consultar sus propios datos y editar únicamente su email y su foto de perfil (almacenada en `perfil-usuarios`); NO puede modificar su rol, sus permisos, sus sucursales ni su identificación. [Esp. §6 (usabilidad); necesidad del negocio]
- **FR-012**: El sistema DEBE permitir a un usuario cambiar su contraseña indicando la actual. [Const. Ppio IX]
- **FR-013**: El sistema DEBE exponer un flujo de restablecimiento de contraseña: a solicitud, genera una contraseña temporal de un solo uso con caducidad y la envía al email registrado del usuario. [Const. Ppio IX; necesidad del negocio]
- **FR-014**: Un inicio de sesión con contraseña temporal DEBE obligar a fijar una contraseña nueva antes de permitir cualquier otra operación; una temporal caducada o ya usada se rechaza. [Const. Ppio IX]
- **FR-015**: El sistema DEBE gestionar el catálogo de sucursales (nombre, dirección, responsable, estado activo/inactivo). [Esp. §4.9, §9.3]
- **FR-016**: El sistema DEBE permitir asignar una o varias sucursales a un usuario y a un técnico. [Esp. §3, §4.3]
- **FR-017**: Inactivar una sucursal DEBE exigir un motivo obligatorio (texto) y generar un aviso por email —con plantilla cuidada de identidad visual— a cada usuario y técnico asignado a ella. [Necesidad del negocio; Const. Ppio XI]
- **FR-018**: El guard DEBE soportar scoping de datos por sucursal ("propia" vs. "consolidada") y por propiedad del registro ("solo los propios"), reutilizable por las demás features. [Esp. §3, §4.9, §3.1]
- **FR-019**: El sistema DEBE gestionar el catálogo `medio_pago` con los valores fijos Efectivo, Transferencia Bancaria, Cheque y Tarjeta vía datáfono; sin pasarela de pago en línea. [Const. "Stack"]
- **FR-020**: El sistema DEBE gestionar el catálogo de categorías de gasto operativo (tipos: local/operativos, personal, otros, mermas y pérdidas). [Esp. §9.3, §4.10.1]
- **FR-021**: El sistema DEBE gestionar el catálogo de canales de solicitud de citas (por defecto: correo electrónico, presencial). [Esp. §9.3, §4.1]
- **FR-022**: El sistema DEBE proveer un mecanismo genérico de parámetros de configuración tipados, con ámbito (global / por sucursal / por marca / por producto / por tipo de servicio) y fecha de vigencia. [Esp. §9, §9.1, §9.2]
- **FR-023**: Al cambiar un parámetro, el sistema DEBE recalcular en cascada todos los valores derivados abiertos que dependen de él (bonos de periodos no cerrados, márgenes de operaciones no confirmadas/no entregadas, niveles de fidelización, reportes). Los documentos legales ya emitidos y los periodos contables cerrados conservan su valor histórico. Todo el efecto queda auditado. [Esp. §9.4; decisión del negocio; Const. "Parámetros configurables"]
- **FR-024**: Las pantallas y endpoints de Configuración SOLO son accesibles para Gerencia General o quien delegue explícitamente. [Esp. §9.4]
- **FR-025**: Todo cambio en la matriz de permisos, en las excepciones de usuario, en los catálogos y en los parámetros DEBE registrarse en auditoría con actor, timestamp y valor anterior/nuevo, y ser consultable. [Esp. §6, §9.4]
- **FR-026**: El sistema NO DEBE permitir dejar cero usuarios activos con rol Gerencia General. [Esp. §9.4 — regla de integridad derivada]
- **FR-027**: El sistema DEBE mitigar ataques de fuerza bruta en login y en restablecimiento (p. ej. bloqueo temporal tras N intentos fallidos). [Const. Ppio IX]
- **FR-028**: El backend DEBE introducir en `backend/src/shared/` la capacidad compartida de envío de correo (integración con el proveedor de email vía `.env`) y de render de plantillas con identidad visual, reutilizable por las demás features; el módulo completo de notificaciones automatizadas es 014. [Const. Ppio XI, Ppio X; Const. "Stack"]
- **FR-029**: Los listados de usuarios/roles/parámetros/sucursales DEBEN tener filtros reactivos y búsqueda multi-criteria (nombre, identificación, email), sin botón "Buscar", y paginación. [Const. Ppio XI]
- **FR-030**: Toda confirmación o entrada puntual (revocar acceso, delegar Configuración, motivo de inactivación) se resuelve con el modal del design-system, nunca con `window.confirm`/`prompt`. [Const. Ppio XI]

### Key Entities *(include if feature involves data)*

- **Usuario**: identificación, credenciales (hash), estado, rol(es), sucursal(es), email, foto de perfil (`perfil-usuarios`). Enlaza con Técnico (005) y con los actores de §3.
- **Rol**: agrupación de permisos. Relación con Usuario (N:M).
- **Módulo / Operación / Permiso**: definidos en 000; esta feature los puebla y asocia. Permiso = (rol|usuario) × módulo [× operación], con marca de excepción.
- **Sucursal**: nombre, dirección, responsable, estado, motivo de inactivación. Referenciada por casi todas las features.
- **SolicitudRestablecimiento**: usuario, contraseña temporal (hash), caducidad, estado (vigente/usada/caducada).
- **MedioPago**: catálogo fijo (Efectivo, Transferencia Bancaria, Cheque, Tarjeta vía datáfono).
- **CategoríaGasto / CanalCita**: catálogos para 010 y 007.
- **ParámetroConfiguración**: clave, tipo, valor, ámbito, fecha de vigencia; historial versionado; dependencias declaradas para el recálculo.
- **RegistroAuditoría**: actor, acción, entidad, valor previo, valor nuevo, timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gerencia General configura un rol nuevo con acceso a 3 módulos y operaciones específicas en menos de 3 minutos, y un usuario con ese rol ve exactamente esos módulos y operaciones.
- **SC-002**: El 100% de los endpoints de negocio pasa por el guard RBAC — verificado por una prueba de contrato que falla si algún endpoint no declara su (módulo, operación).
- **SC-003**: Petición sin permiso de operación → 403; sin acceso a módulo → 403; sin token válido → 401 (verificado en integración).
- **SC-004**: Un usuario cambia su email y su foto de perfil desde el autoservicio y no puede alterar su rol ni sus permisos.
- **SC-005**: Un usuario que olvidó su contraseña la restablece vía email en menos de 2 minutos y el primer inicio de sesión le obliga a cambiarla.
- **SC-006**: Inactivar una sucursal sin motivo se bloquea; con motivo, el 100% de su personal recibe el aviso por email.
- **SC-007**: Cambiar un parámetro recalcula los valores abiertos dependientes y deja intactos los documentos emitidos y los periodos cerrados, con el cambio auditado.
- **SC-008**: No es posible dejar el sistema sin ningún usuario Gerencia General activo.
- **SC-009**: Un gerente de sucursal A no obtiene ningún dato de la sucursal B en ningún endpoint scoped.
- **SC-010**: La lógica del guard RBAC de dos niveles tiene cobertura de pruebas unitarias/integración (Const. Ppio IX).

## Assumptions

- 000 está implementada (tablas base de RBAC vacías, MinIO con los cuatro buckets, esqueleto modular).
- La lista inicial de módulos es la de §3.1; se amplía cuando una feature declara su módulo.
- El proveedor de email (SendGrid o equivalente) y su API key se configuran vía `.env`; el diseño de las plantillas usa la skill del Principio XII.
- La contraseña temporal de restablecimiento caduca en un plazo configurable (por defecto 24 h) y es de un solo uso.
- Los valores de negocio concretos (márgenes objetivo, umbral de merma, niveles de fidelización, fórmula de bono) los define y consume su feature dueña; 001 aporta el mecanismo, la pantalla, el recálculo en cascada y la auditoría.
- Integración con un proveedor de identidad externo (SSO/OAuth) está fuera de alcance (Const. Ppio VII).
- La entidad `usuario` y el catálogo `medio_pago` son creados por esta feature; 005 enlaza `usuario` con la ficha de RRHH técnico; 009 y 008 consumen `medio_pago`.
