# CRONOS (Sistema de Gestión Integral para Relojería de Alta Gama) — Constitution
 
*Nombre de trabajo sugerido — ajústalo libremente. Identidad, alcance y reglas de negocio completas del sistema en `especificacion_sistema_relojeria.md` — esta constitución no los repite, la referencia.*
 
## Core Principles
 
### I. Trazabilidad al Contexto de Negocio
Toda feature, endpoint o tabla nueva debe trazarse a al menos una necesidad documentada en `especificacion_sistema_relojeria.md` (módulo, regla de negocio o reporte). No se implementa funcionalidad que no resuelva algo ahí documentado. Si el negocio adopta más adelante una jerarquía formal de objetivos (OO/OT/OE tipo Balanced Scorecard), esta constitución se actualiza para exigir esa trazabilidad explícita.
 
### II. Nivel Operativo = Registro Real (NON-NEGOTIABLE)
Toda operación de nivel operativo es un INSERT/UPDATE/DELETE sobre un registro concreto, ligado a un documento de negocio real (orden de venta de un reloj, orden de trabajo de servicio técnico, ingreso a stock, registro de merma, apertura/cierre de caja, transferencia entre sucursales, etc.). Nada de simulacros ni "estados" sin persistencia transaccional real en PostgreSQL.
 
### III. Separación de Motores por Responsabilidad
PostgreSQL = único motor operativo (OLTP). MinIO guarda archivos estáticos servidos directo a la app (no datos transaccionales), en buckets separados por responsabilidad:
- `reloj-imagenes` — fotos de cada reloj en stock, servidas directo a la app.
- `comprobantes-venta` — PDF de venta, documento de orden de trabajo y certificado de garantía/autenticidad, generados al confirmar cada transacción, servidos vía endpoint autenticado.
- `perfil-usuarios` — foto de perfil de cada usuario.
- `documentos` — adjuntos generales de negocio (documento de soporte de merma: acta/fotos/denuncia; certificados y documentos legales de proveedor; cotizaciones/actas de servicio), servidos vía endpoint autenticado.
- `landing-zone` — raw del Extract del ELT, **nunca** consultado como fuente de negocio.

Los cinco primeros (`reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios`, `documentos`) se provisionan en `000`; `landing-zone` se provisiona en `012`. ClickHouse = warehouse para las agregaciones tácticas/estratégicas (sección 4.11.2 de la especificación). Flujo ELT (no ETL): Extract desde PostgreSQL → Load raw a MinIO (`landing-zone`) → Load a ClickHouse → Transform in-warehouse, orquestado por Airflow. Ninguna feature mezcla responsabilidades entre motores ni entre buckets.
 
### IV. RBAC de Dos Niveles Obligatorio
Toda funcionalidad nueva declara sus permisos en el esquema existente: rol→módulo y rol→módulo→operación (Crear/Consultar/Editar/Eliminar), respetando que el acceso al módulo es prerrequisito del permiso granular (ver sección 3.1 de la especificación). No se crean rutas de acceso paralelas. Los cambios a esta matriz solo los realiza la Gerencia General (sección 9.4 de la especificación) y quedan auditados.
 
### V. Backend y Frontend Desacoplados
El backend (FastAPI) expone únicamente API REST/JSON — no renderiza HTML. El frontend (Vue 3 + Vite) consume esa API y es el único responsable de la interfaz. Ninguna lógica de negocio vive en el frontend (p. ej. el cálculo de margen mínimo protegido en descuentos, sección 4.8.2, se valida siempre en el backend); ninguna lógica de presentación vive en el backend.
 
### VI. Features Autocontenidas
Cada spec en `specs/NNN-feature/` es independiente y completa. Una feature no redefine lo ya fijado en esta constitución, en `especificacion_sistema_relojeria.md`, ni en el modelo de datos operativo (`01_operativo_postgres.sql`) — los referencia.
 
### VII. Simplicidad Justificada (DRY/KISS)
No se añade tabla, motor, microservicio o dependencia nueva sin justificarla contra la necesidad de negocio que resuelve. No se duplica lógica que ya existe en otra capa (DRY); se prefiere siempre la solución más simple que cumpla el requisito (KISS). Esto es lo que descarta, por ejemplo, una pasarela de pago en línea o un motor de forecasting mientras el negocio no los necesite (ver sección "Stack y Restricciones Técnicas").
 
### VIII. Guardrails de la IA sobre Specs (NON-NEGOTIABLE)
Ningún spec, plan, tasks o constitution.md existente se borra o reescribe sin confirmación explícita del usuario. El `spec.md` de cada feature se valida con el usuario antes de continuar; a partir de ahí, `plan.md`, `research.md`, `data-model.md`, `quickstart.md` y `tasks.md` se generan de corrido sin pausas adicionales — salvo que aparezca una ambigüedad o una contradicción con esta constitución o con `especificacion_sistema_relojeria.md`, en cuyo caso se pregunta al usuario antes de asumir. Esta restricción aplica a documentos de especificación, no al código de implementación.
 
### IX. Calidad, Testing y Seguridad
**Testing:** cobertura obligatoria de pruebas unitarias/integración en la lógica de negocio crítica de cada feature — cálculo de margen (venta y servicio técnico), margen mínimo protegido tras descuentos/cupones, cálculo de nivel de fidelización, cálculo de bono por productividad, RBAC de dos niveles, y registro/costeo de mermas. No se exige 100% del proyecto, sí de estos módulos.
**Seguridad:** credenciales y secretos solo vía `.env` (nunca hardcodeados), sanitización de toda entrada de usuario, autenticación JWT + autorización RBAC en cada endpoint.
**Rendimiento:** operaciones CRUD estándar responden en <1s en entorno de desarrollo; reportes/dashboards agregados (ClickHouse) pueden tardar más, sin bloquear la interfaz (carga asíncrona).
 
### X. Convenciones de Código y Arquitectura (Modularidad NON-NEGOTIABLE)
**Modularidad obligatoria (NON-NEGOTIABLE):** tanto `backend/` como `frontend/` se organizan en módulos de negocio nítidamente separados, cada uno en su propia carpeta con una frontera clara. Prohibido el código espagueti: nada de archivos "cajón de sastre" (`utils.py` gigante, `helpers.js` que lo mezcla todo), nada de un módulo importando los internos de otro saltándose su capa pública, nada de lógica de un dominio filtrada dentro de otro. Todo lo que se comparte entre dos o más módulos vive en una única carpeta de código reutilizable (`shared/` o `core/`) y se importa desde ahí — no se copia ni se duplica. Un módulo depende de `shared/`/`core/` y de la API pública de otros módulos, nunca de sus detalles internos. Una feature que necesite tocar varios módulos lo hace respetando esas fronteras, no borrándolas.

**Backend:** snake_case (Python/SQL), arquitectura por capas (router → service → repository), sin lógica de negocio en los routers. El código se organiza por módulos de negocio (inventario, citas, clientes, servicio técnico, etc.) en lugar de por tipo técnico (todos los routers juntos, todos los services juntos). Cada módulo tiene su propia carpeta con sus routers, services, repositories y schemas. El código reutilizable entre módulos (helpers, utilidades, configuración base) vive en una carpeta `shared/` o `core/` separada.

**Estructura backend**:
```
backend/src/
├── shared/          # Código reutilizable: config, database, auth, exceptions, schemas base
├── inventario/      # Módulo de inventario de relojes y piezas
│   ├── routers.py
│   ├── services.py
│   ├── repositories.py
│   └── schemas.py
├── citas/           # Módulo de gestión de citas
│   ├── routers.py
│   ├── services.py
│   ├── repositories.py
│   └── schemas.py
└── ...              # Resto de módulos de negocio
```

**Frontend:** camelCase (JS/Vue), componentes + composables, sin llamadas directas a la API fuera de una capa de servicios centralizada. El código se organiza por módulos de negocio (mismo criterio y misma frontera estricta que backend). Cada módulo tiene sus propios componentes, composables, stores (Pinia) y servicios API. El código reutilizable (componentes UI, utilidades, helpers) vive en una carpeta `shared/` separada; ningún módulo importa componentes o stores internos de otro módulo.

**Estructura frontend**:
```
frontend/src/
├── shared/          # Código reutilizable: componentes UI, utilidades, helpers, API base
├── inventario/      # Módulo de inventario
│   ├── components/
│   ├── composables/
│   ├── stores/
│   └── services/
├── citas/           # Módulo de citas
│   ├── components/
│   ├── composables/
│   ├── stores/
│   └── services/
└── ...              # Resto de módulos de negocio
```
 
### XI. Usabilidad y Diseño de Interfaz
Los filtros de búsqueda son reactivos/automáticos — sin botón "Buscar" o "Filtrar", se aplican al cambiar el criterio. Todo listado de registros usa paginación (nunca carga completa en una sola vista). Cada panel de trabajo (work panel) sigue un set estandarizado de acciones (Agregar, Editar, Eliminar, y las que correspondan a la entidad — ej. "Confirmar"/"Cancelar" para citas, "Cerrar orden" para servicio técnico, "Autorizar baja" para mermas por encima del umbral configurado) con la misma ubicación/estilo en toda la aplicación.
 
**Diálogos:** toda confirmación (aceptar/rechazar) y toda entrada de un dato puntual (motivo de merma, causa, fecha, id que autoriza) se resuelve con un modal in-app del design-system — nunca con `window.confirm` / `window.prompt` / `window.alert`. El helper compartido es `frontend/src/shared/ui/dialogs.js` (`confirm()` / `prompt()`), pintado por `<DialogHost>` (montado una vez en `App.vue`). Un selector siempre ofrece las opciones válidas existentes (`<select>` poblado desde el backend) en vez de un campo libre donde se pueda teclear un valor inexistente.

**Entrada de datos — minimizar texto libre:** salvo los campos genuinamente descriptivos (notas, diagnóstico, observaciones), la entrada de datos se resuelve con selección + filtrado sobre opciones existentes, no con texto libre. Toda pantalla de listado ofrece **búsqueda multi-criterio**: personas por nombre, cédula/RUC, email o teléfono (y número de afiliado en el caso de clientes); productos por nombre, código/número/referencia, calibre o proveedor. El objetivo es "escribir para filtrar", no "escribir para crear un valor nuevo".

**Correo transaccional — plantillas cuidadas:** todo email que el sistema envía (cambio de estado de orden de trabajo, cupones y beneficios de fidelización, recordatorio de cita, aviso de inactivación de sucursal, datos del técnico asignado, contraseña temporal, etc.) usa una plantilla con la identidad visual del sistema (paleta del Principio XI, encabezado y pie coherentes), no texto plano. Las plantillas son configurables por Gerencia General. La capacidad compartida de envío + render de plantillas se introduce en `001` (en `backend/src/shared/`); el módulo completo de notificaciones automatizadas (disparadores, panel de entregas, opt-out, cola y reintentos) es la feature `014`.
 
**Acciones que no llevan a nada:** ningún botón puede quedarse en un mensaje de "listo" sin efecto real. Toda acción o bien ejecuta su operación contra el backend, o bien navega a la pantalla/modal donde se resuelve (con el contexto ya cargado). Un botón que "recomienda" o "sugiere" algo debe abrir el flujo concreto (ej. "Reponer stock" → abre la orden de compra al proveedor con el modelo y la cantidad sugerida puestas).
 
**Exportación de reportes:** toda pantalla de reporte ofrece la descarga en CSV, Excel y PDF mediante el helper compartido `frontend/src/shared/exportar.js` (`opcionesExportacion()` → menú de 3 formatos). CSV y Excel salen del mismo arreglo de filas; PDF abre una vista imprimible. Para un reporte muy extenso (más de ~5 000 filas) solo se ofrece CSV.
 
**Gráficos del dashboard:** todo reporte complejo (sección 4.11.2 de la especificación) se visualiza con `vue-echarts`, sin librería de gráficos adicional, según el tipo de dato: barras para comparativos (margen por marca, productividad por técnico, rentabilidad por sucursal), pastel/dona para distribuciones (clientes por nivel de fidelización, mermas por causa), líneas para tendencias en el tiempo (margen mensual, rotación de stock), y tarjetas KPI simples para los 5-6 indicadores del panel principal de Gerencia General (sección 4.11.3).
 
**Identidad visual — paleta de colores (definida):**
 
| Rol | Color | Hex | Uso |
|---|---|---|---|
| Primary | Azul marino oscuro | `#0F172A` | Barra de navegación horizontal, botones de acción primaria, encabezados de tabla/panel |
| Secondary | Dorado/bronce | `#B48E38` | Insignias de fidelización (Bronce/Plata/Oro), acentos de alto valor, estados activos de navegación |
| Tertiary | Verde esmeralda | `#059669` | Estados de éxito y confirmación (orden cerrada, venta confirmada, envío exitoso) — nunca decorativo |
| Neutral | Gris pizarra | `#64748B` | Texto secundario, bordes, fondos de tarjeta, estados deshabilitados |
| Danger *(sugerido, no venía en la paleta compartida)* | Rojo | `#DC2626` | Acciones destructivas (Eliminar, dar de baja por merma), errores de validación |
| Warning *(sugerido, no venía en la paleta compartida)* | Ámbar | `#D97706` | Alertas no críticas (stock bajo el umbral, cuenta por cobrar próxima a vencer) |
 
**Reglas de uso del color:**
- Cada color se usa siempre con su escala de tonos (900→50, igual que en la paleta compartida) para fondos, bordes y estados hover/active — nunca un hex suelto fuera de esas escalas.
- Todo texto sobre fondo Primary o Secondary usa el tono más claro de su propia escala (o blanco) para cumplir un contraste mínimo WCAG AA (4.5:1 en texto normal, 3:1 en texto grande).
- Secondary (dorado) se reserva para lo que realmente comunica valor o estatus — no se usa como color de fondo masivo ni se mezcla con Tertiary en un mismo componente.
- Tertiary (verde) es exclusivo de éxito/confirmación; Danger y Warning son exclusivos de sus propios casos — un mismo color no cubre dos significados distintos en la misma pantalla.

**Tratamiento visual — definido vía skill del Principio XII y aprobado por el usuario (2026-09-10):**
- **Mundo visual único: claro/marfil. Sin tema oscuro.** Toda la UI declara `color-scheme: light`; no se implementa `@media (prefers-color-scheme: dark)` ni variante `[data-theme="dark"]`. La única superficie oscura permitida es la barra de navegación superior (Primary `#0F172A`).
- **El oro (Secondary) se aplica como FILETE y como CIFRA, nunca como bloque/franja de fondo.** Escalones de la escala Secondary y su uso validado (todos ≥ WCAG AA):
  - oro texto/filete sobre marfil → `secondary-600 #8A6D2B` (4,9:1)
  - oro acento/texto sobre azul marino → `secondary-300 #D8B876` (9,4:1)
  - superficie Secondary (solo insignia de rango máximo, pequeña) → `secondary-900 #3B2E16` + `secondary-50 #FBF6EC` (12:1)
  - Escala Secondary de referencia: `300 #D8B876 · 400 #C6A052 · 500 #B48E38 (ancla) · 600 #8A6D2B · 700 #6B5320 · 800 #4E3D1C · 900 #3B2E16`.
  - Una sola cifra clave por pantalla puede ir en oro (`secondary-700`) para comunicar valor; el resto en tinta.
- **Superficies:** el lienzo va deliberadamente unos tonos por debajo del blanco de las tarjetas — lienzo marfil cálido (aprox. `#EFEBE0`), tarjetas `#FFFFFF` con borde hairline cálido de 1px + sombra cálida (tinte marrón, no gris). Escala de sombra de 2 niveles (tarjetas de KPI más tenue, tarjetas de contenido algo más profunda). Los KPIs son tarjetas individuales, no un bloque único. Nada de paneles ni franjas de color sólido.
- **Tipografía (ya definida — reemplaza la nota previa de "queda fuera"):** display y cifras destacadas en **Cormorant Garamond** (500/600); UI, tablas, ejes y datos en **Hanken Grotesk** (400/500/600) con `tabular-nums`. Sin monoespaciada. Fallbacks reales declarados. Se descartan Fira/Fraunces/Inter por genéricas.
- **Gráficos:** marcas finas, relleno ≤ 5–7 % de opacidad, grilla mínima (baseline + 1–2 referencias), remate del dato en oro; nada de gradientes o sombras que tapen el dato.
- Spacing generoso: escala 4/8 px; padding de tarjeta ~24 px; separación entre secciones 32–40 px.

**Navegación:** barra horizontal superior fija (no sidebar lateral), con categorías de primer nivel (ej. Dashboard, Ventas, Inventario, Servicio Técnico, Citas, Clientes/Fidelización, Proveedores, Técnicos, Sucursales, Finanzas, Sistema). El ítem activo se marca con un filete de oro (`secondary-300`) bajo la etiqueta. Una categoría con 4 o más sub-opciones se despliega en un mega-menú agrupado por columnas temáticas (ej. "Sistema" → Seguridad / Configuración / Auditoría). Una categoría con menos de 4 sub-opciones se lista directo sin agrupar en columnas.
 
### XII. Consistencia Visual mediante Skill de Diseño (NON-NEGOTIABLE)
Toda interfaz — pantalla, componente o feature — se construye usando la skill `ui-ux-pro-max`, ubicada en `C:\Users\Usuario\.claude\skills\ui-ux-pro-max`. Ninguna pantalla se diseña o codifica por fuera de ella. Esta skill es responsable de traducir la paleta y las reglas de uso del color (Principio XI) en componentes Vue reales (tokens, configuración de Tailwind, variantes de botón/tarjeta/modal) y de aplicarlos de forma idéntica en cada feature — ninguna feature define su propio estilo de componente ni reinterpreta la paleta por su cuenta. El resultado debe ser un diseño de interfaz profesional — a nivel de un producto comercial real, no una maqueta académica — con jerarquía visual clara, espaciado consistente y acabado cuidado en cada pantalla; ninguna feature se da por completa con una interfaz de aspecto improvisado o "por defecto".
 
## Stack y Restricciones Técnicas
 
- **Infraestructura fija:** Docker Desktop + Airflow (DAGs) como orquestador.
- **Backend:** FastAPI (Python) — REST/JSON, JWT sobre el RBAC de PostgreSQL.
- **Frontend:** Vue 3 + Vite + Tailwind + vue-echarts.
- **Motores de datos:** PostgreSQL 16 (operativo), MinIO (`reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios` y `documentos` provisionados en 000; `landing-zone` provisionado en 012), ClickHouse (warehouse, 012), pgAdmin (visualización, opcional).
- **Modelo operativo:** derivado de `especificacion_sistema_relojeria.md` (entidades de la sección 4) hacia un `01_operativo_postgres.sql` formal (Ojo seguir nada mas de guia, si hace falta algun campo o tablas agregar de se rnecesario, no hac efalta seguir este .sql a la fuerza).
- **Control de versiones:** Git + GitHub, sin estándar de commits obligatorio (ajustable).
- **Pagos:** catálogo `medio_pago` (Efectivo, Transferencia Bancaria, Cheque, Tarjeta vía datáfono existente) — **sin pasarela de pago en línea**, dado que la venta es presencial; se revisa este punto si el negocio abre venta remota a futuro.
- **Email transaccional:** SendGrid (o equivalente) para los envíos automatizados: actualizaciones de estado de la orden de trabajo/servicio técnico, cupones y beneficios del programa de fidelización, y recordatorios de citas ya confirmadas. Esto es un flujo distinto del canal de *entrada* para solicitar citas (sección 4.1: Gmail y presencial, gestionado manualmente por el personal) — uno es humano y de entrada, el otro automatizado y de salida.
- **Facturación:** PDF local vía `reportlab` (o `weasyprint`) para comprobantes internos y certificados de garantía/autenticidad — **sin integración real con el SRI** en esta fase (la facturación electrónica legal ante el SRI queda documentada como pendiente, sección 7 de la especificación).
- **Forecasting/ML:** fuera de alcance — el volumen del negocio (stock de ~12 unidades por modelo) no lo justifica hoy; se evalúa a futuro contra el Principio VIII si el negocio lo pide.
- **Imágenes de producto:** bucket MinIO `reloj-imagenes` — nunca en disco local.
- Detalle completo de reglas de negocio, entidades y reportes en `especificacion_sistema_relojeria.md`.
## Flujo de Trabajo (Spec Kit / Kiro)
 
Features en orden de dependencias (fijo — no se adelanta alcance de una feature posterior):

| # | Feature | Alcance de cabecera | Depende de |
|---|---|---|---|
| 000 | `000-bootstrap-infraestructura` | Infraestructura base (ver abajo) | — |
| 001 | `001-auth-rbac-configuracion` | `usuario` (con autoservicio: ver mis datos, editar email/foto, cambio y restablecimiento de contraseña), RBAC de dos niveles, JWT + guard por endpoint, `sucursal` (§9.3; inactivar exige motivo y notifica a su personal), catálogos (`medio_pago`, categorías de gasto, canales de cita) y parámetros configurables de §9 con auditoría, capacidad compartida de correo con plantillas | 000 |
| 002 | `002-proveedores` | §4.2: proveedores, órdenes de compra / reposición, calificación de confiabilidad, entrega real vs. pactada | 001 |
| 003 | `003-inventario-relojes-piezas` | §4.4 relojes (ficha por unidad física, N.º de serie), §4.5 piezas; fotos a bucket `reloj-imagenes`; alertas de stock (~12 / 1 unidad / mínimo de pieza) | 001, 002 |
| 004 | `004-multisucursal-traslados` | §4.9: transferencias de relojes/piezas entre sucursales, visibilidad de datos y reportes por sucursal vs. consolidados | 001, 003 |
| 005 | `005-tecnicos-productividad` | §4.3 técnicos (RRHH técnico), costo interno de mano de obra; §5 reglas y fórmula de bono por productividad (configurables) + motor de acumulación | 001, 004 |
| 006 | `006-clientes-fidelizacion-descuentos` | §4.8 CRM básico; §4.8.1 niveles de fidelización (configurables, recálculo automático, historial); §4.8.2 descuentos, cupones y **margen mínimo protegido** (§9.1) | 001 |
| 007 | `007-citas` | §4.1: registro manual de citas (Gmail / presencial), estados, vínculo a venta u orden de trabajo | 001, 006 |
| 008 | `008-servicio-tecnico-lubricacion` | §4.6 fichas de lubricación por calibre; §4.7 órdenes de trabajo (presupuesto con elección de piezas originales/no originales, fecha estimada solo tras diagnóstico, aviso al cliente con datos del técnico, cobro al retiro); §5 costeo y margen del servicio; introduce el registro de pagos multimedios compartido; informe de servicios/arreglos | 003, 005, 006 |
| 009 | `009-ventas-facturacion-comprobantes-garantias` | Orden de venta de reloj (Principio II), baja de stock, aplicación de descuentos/cupones (006); §7 garantías (fábrica vs. tienda); comprobante + certificado de garantía/autenticidad a bucket `comprobantes-venta`; genera la CxC | 003, 006, 008 |
| 010 | `010-contabilidad-gastos-cxc-cxp` | §4.10 libro diario/mayor, estado de resultados, caja/bancos, cheques; §4.10.1 gastos por sucursal y tipo; CxC (de 009), CxP (de 002); §7 retenciones-ready | 002, 009 |
| 011 | `011-mermas-perdidas` | §4.12: baja de relojes/piezas por daño, pérdida, robo o defecto; costeo a costo de adquisición; asiento automático en 010; umbral de autorización (§9.2) | 003, 008, 010 |
| 012 | `012-plataforma-datos-tactico-estrategico` | Servicios ClickHouse + Airflow + bucket `landing-zone`; DAGs ELT desde PostgreSQL; modelo de warehouse para §4.11.2 | 001–011 (como fuente de extracción) |
| 013 | `013-dashboards-reportes` | §4.11.1 reportes operativos simples; §4.11.3 panel principal de Gerencia; §4.11.2 reportes analíticos renderizados desde ClickHouse | 012 |
| 014 | `014-notificaciones-automatizadas-email` | SendGrid: estado de orden de trabajo (008), cupones/beneficios de fidelización (006), recordatorios de citas confirmadas (007) | 006, 007, 008 |

**Qué construye cada feature de infraestructura, desde cero, y nada más allá de eso:**
- `000-bootstrap-infraestructura`: el `docker-compose.yml` base con los servicios **PostgreSQL, backend (FastAPI esqueleto con salud/health-check), frontend (Vue esqueleto con Tailwind ya configurado con la paleta del Principio XI) y MinIO con los buckets de cara a la app `reloj-imagenes`, `comprobantes-venta`, `perfil-usuarios` y `documentos` ya creados**, migraciones iniciales (Alembic) y las tablas base de RBAC (rol, módulo, permiso) vacías de datos de negocio. Ninguna feature de negocio (001-014) empieza sin que esta exista — todas la dan por sentada.
- `012-plataforma-datos-tactico-estrategico`: agrega al mismo `docker-compose.yml` los servicios de **ClickHouse y Airflow** (webserver + scheduler, `LocalExecutor`) y el bucket **`landing-zone`** en el MinIO ya provisionado por 000, y construye ahí los DAGs de extracción/carga desde cero, con tareas separadas y nombradas por fase (Extract / Load raw / Load warehouse / Transform), corrida horaria por defecto, disparo manual y frecuencia configurable. Ninguna otra feature toca configuración de Airflow, DAGs, ni el esquema de ClickHouse.
- Ninguna feature fuera de estas dos modifica el `docker-compose.yml` ni añade servicios nuevos — si una feature de negocio cree necesitar infraestructura adicional, se documenta como propuesta y se decide antes de tocar el archivo (Principio VIII, Simplicidad Justificada).

**Entidades compartidas:** cada entidad transversal tiene una única feature dueña que la crea completa antes que cualquier consumidora (`sucursal`, `usuario` y el catálogo `medio_pago` → 001; `cliente` → 006; `reloj`/`pieza`/`calibre` → 003; `proveedor` → 002; `tecnico` → 005). Ninguna feature crea una versión "mínima" de una entidad de otra para adelantarse; si la necesita, es porque su feature dueña ya está antes en el orden. Las **capacidades compartidas** siguen la misma regla: envío de correo con plantillas → introducida en 001; generación de PDF (comprobantes, certificados, documentos de OT) → introducida en 008; registro de pagos multimedios contra un documento facturable → introducida en 008; todas viven en `backend/src/shared/` y las features posteriores las reutilizan sin duplicarlas.

**Parámetros configurables — recálculo en cascada:** cambiar un parámetro de §9 dispara el recálculo automático de todos los valores derivados que dependan de él y estén **abiertos**: bonos de periodos de liquidación no cerrados, márgenes de ventas y órdenes de trabajo no confirmadas/no entregadas, niveles de fidelización, y todos los reportes. Los **documentos legales ya emitidos** (comprobantes de venta, certificados de garantía/autenticidad, documento de una OT ya entregada) y los **periodos contables cerrados** conservan su valor histórico; el cambio del parámetro y su alcance quedan auditados y visibles. La lógica de recálculo se valida siempre en el backend (Principio V).

Para cada feature: /speckit-specify → (opcional /speckit-clarify) → /speckit-plan → /speckit-tasks → (opcional /speckit-analyze) → /speckit-implement. Ninguna feature avanza a plan sin spec aprobado, ni a implement sin tasks aprobado. La feature 013 depende de que 012 (ClickHouse + Airflow) esté construida; 012 puede desarrollarse en paralelo a las features operativas ya que no depende de ellas para su infraestructura, aunque sí las necesita como fuente de extracción. La feature 014 depende de 008 (servicio técnico), 006 (fidelización) y 007 (citas) como disparadores de los envíos. Todas dependen de que 000 esté implementada primero.

**Modo de trabajo de las specs (lote):** por decisión del usuario, los `spec.md` de las 15 features (000–014) se generan en un único lote para revisión conjunta. El resto de artefactos (`plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, `checklists/requirements.md`, `contracts/`) y toda la implementación quedan en pausa hasta la aprobación explícita del lote. Esto no deroga el Principio VIII: cada `spec.md` sigue requiriendo validación antes de pasar a su `plan.md`.
 
### Estructura de cada Feature
Toda feature en `specs/NNN-feature/` sigue esta misma estructura, sin excepción:
 
```
specs/NNN-feature/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
├── checklists/
│   └── requirements.md
└── contracts/
    └── ...
```

**Ubicación de specs**: La carpeta `specs/` vive en la raíz del proyecto (mismo nivel que `backend/`, `frontend/`, `docs/`), no dentro de `.kiro/` ni `.specify/`. Esto facilita la navegación y refleja que las specs son documentos del proyecto, no configuración de herramientas.
 
Los archivos base (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, `checklists/requirements.md`) son obligatorios en todas las features. El contenido de `contracts/` y cualquier checklist adicional se completan según lo que aplique a cada feature (p. ej. contratos OpenAPI para los endpoints nuevos, checklists extra de seguridad o de datos cuando el feature lo amerite).
 
## Governance
 
Esta constitución tiene prioridad sobre cualquier spec individual. Un cambio aquí obliga a revisar las specs ya creadas que dependan del principio modificado. Toda spec/plan/tasks debe verificar cumplimiento de estos principios antes de pasar a la siguiente fase.
 
**Version**: 1.7.0 | **Ratified**: 2026-09-09 | **Last Amended**: 2026-09-10

**Changelog**:
- **1.7.0** — Principio XI: tratamiento visual concretado vía skill del Principio XII y aprobado por el usuario. Mundo visual único claro/marfil (sin tema oscuro; única superficie oscura = barra de navegación). El oro (Secondary) se usa como filete y cifra, nunca como bloque de fondo, con escalones de escala validados a WCAG AA. Superficies: lienzo marfil por debajo del blanco de las tarjetas + sombra cálida de 2 niveles; KPIs como tarjetas individuales. Tipografía fijada: Cormorant Garamond (display/cifras) + Hanken Grotesk (UI, `tabular-nums`) — se elimina la nota previa de "tipografía queda fuera". Gráficos: marcas finas, relleno ≤7 %, grilla mínima, remate en oro. Feature 000 implementada y validada; inicia implementación de 001.
- **1.6.0** — Principio III: buckets `perfil-usuarios` y `documentos` añadidos a `000` (además de `reloj-imagenes` y `comprobantes-venta`). Principio XI: minimizar texto libre + búsqueda multi-criterio; plantillas de correo cuidadas con identidad visual. Capacidades compartidas (correo→001, PDF→008, pagos multimedios→008) y catálogo `medio_pago`→001. Regla de recálculo en cascada de parámetros configurables (recalcula lo abierto, respeta lo ya emitido y los periodos cerrados). Detalles de alcance en 001 (autoservicio de usuario, reset de contraseña, inactivación de sucursal con aviso), 008 (presupuesto/piezas originales, cobro al retiro) y 012 (DAGs con fases E/L/T, horario configurable).
- **1.5.0** — Principio X reforzado (modularidad NON-NEGOTIABLE, anti-espagueti, `shared/`/`core/` único). Flujo de Trabajo reordenado por dependencias (auth-rbac a 001; ventas absorbida en `009-ventas-facturacion-comprobantes-garantias`; `012-plataforma-datos` antes de `013-dashboards`). MinIO (`reloj-imagenes`, `comprobantes-venta`) movido a `000`; 012 solo agrega ClickHouse, Airflow y `landing-zone`. Regla de generación de specs en lote.
- **1.3.0** — (previo) paleta de color e identidad visual en Principio XI.