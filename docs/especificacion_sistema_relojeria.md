# Especificación Funcional del Sistema de Gestión para Relojería de Alta Gama

**Versión:** 1.0
**Tipo de documento:** Especificación de requisitos funcionales y no funcionales (base para análisis y diseño)

---

## 1. Introducción

### 1.1 Propósito
Este documento formaliza los requerimientos funcionales, datos y reglas de negocio necesarios para el diseño e implementación de un sistema de gestión integral para una relojería de gama alta con taller técnico propio. Consolida la información provista por el negocio y la amplía con recomendaciones técnicas y funcionales justificadas por las mejores prácticas del sector (retail de lujo + servicio técnico especializado) y por el marco legal ecuatoriano.

### 1.2 Alcance
El sistema cubrirá: gestión de inventario de relojes y repuestos, servicio técnico con trazabilidad por número de serie, gestión de citas, proveedores, técnicos, clientes, operación multi-sucursal, contabilidad básica y reportería gerencial. Queda fuera de alcance —salvo que se decida ampliarlo a futuro— un portal de autoservicio para clientes.

---

## 2. Descripción General del Negocio

### 2.1 Naturaleza del negocio
Distribuidor / relojería de gama alta, de tamaño pequeño, que opera bajo dos líneas de negocio:

| Línea de negocio | Descripción |
|---|---|
| Venta de relojes nuevos | Stock propio y limitado (~12 unidades por modelo/marca) |
| Servicio técnico postventa | Exclusivo para relojes adquiridos en la propia tienda |

**Restricciones explícitas del modelo:**
- No es un centro de servicio técnico abierto al público general.
- No opera como *grey market* (reventa no autorizada fuera de canales oficiales).
- Es una operación de tienda física con stock propio y taller interno (no dropshipping ni intermediación pura).

### 2.2 Fuentes de margen / ganancia
1. Diferencia entre costo de adquisición y precio de venta del reloj.
2. Mano de obra + piezas del servicio técnico (con margen definido por el negocio sobre el costo interno).
3. Venta de piezas de repuesto (originales o de calidad equivalente no original).

### 2.3 Propuesta de ampliación del modelo de negocio
Estas líneas no fueron mencionadas explícitamente pero son habituales en relojerías de gama alta. Se descarta expresamente la compra-venta o consignación de relojes usados; quedan como **propuestas a evaluar**:

- **Garantía diferenciada:** garantía de fábrica (marca) vs. garantía de tienda (mano de obra/servicio), con periodos y coberturas distintas registradas por transacción.
- **Certificado digital de autenticidad y garantía:** documento generado automáticamente al vender o dar servicio, vinculado al número de serie.

---

## 3. Actores del Sistema (Roles de Usuario)

| Rol | Descripción funcional |
|---|---|
| Propietario / Gerencia General | Acceso total, reportes consolidados multi-sucursal, configuración de márgenes |
| Gerente de Sucursal | Gestión operativa de su sucursal, reportes locales |
| Vendedor / Encargado de mostrador | Registro de citas, ventas, atención al cliente |
| Técnico | Ejecución de órdenes de trabajo, registro de lubricación e insumos usados |
| Técnico Jefe / Maestro relojero | Supervisión técnica, asignación de órdenes, control de calidad |
| Contador / Administrativo | Módulo contable, cuentas por cobrar/pagar, gastos |
| Cliente | No tiene acceso al sistema (gestión 100% a cargo del personal) |

El sistema debe soportar **niveles de acceso configurables por rol y por sucursal**, de modo que un técnico, por ejemplo, solo vea las órdenes asignadas a él, y un gerente de sucursal no vea datos financieros consolidados de otras sucursales salvo permiso explícito del propietario.

### 3.1 Modelo de Permisos (por módulo y por operación)
El control de acceso se define en dos niveles, independientes entre sí:

1. **Acceso por módulo:** a qué módulos puede entrar un usuario (Citas, Proveedores, Técnicos, Inventario de relojes, Piezas, Lubricación, Órdenes de trabajo, Clientes/Fidelización, Multi-sucursal, Contable, Reportes, Mermas, Configuración).
2. **Permisos por operación dentro de cada módulo habilitado:** Crear, Consultar, Editar, Eliminar — asignables de forma independiente. Por ejemplo, un vendedor puede tener "Crear" y "Consultar" en Citas pero no "Eliminar"; un técnico puede tener solo "Consultar" en Inventario de piezas, pero "Editar" en las órdenes de trabajo que tiene asignadas.

**Ejemplo ilustrativo (los valores son de referencia; todo es configurable, ver 9.3):**

| Módulo | Vendedor | Técnico | Gerente de Sucursal | Gerencia General |
|---|---|---|---|---|
| Citas | Crear, Consultar, Editar | Consultar | Crear, Consultar, Editar, Eliminar | Crear, Consultar, Editar, Eliminar |
| Inventario de relojes | Consultar | Consultar | Crear, Consultar, Editar | Crear, Consultar, Editar, Eliminar |
| Órdenes de trabajo | Crear, Consultar | Consultar, Editar (solo las propias) | Crear, Consultar, Editar, Eliminar | Crear, Consultar, Editar, Eliminar |
| Mermas | Consultar | Crear, Consultar (reportar un hecho) | Crear, Consultar, Editar | Crear, Consultar, Editar, Eliminar (autoriza bajas) |
| Módulo contable | Sin acceso | Sin acceso | Consultar | Crear, Consultar, Editar, Eliminar |
| Configuración (sección 9) | Sin acceso | Sin acceso | Sin acceso (salvo delegación) | Crear, Consultar, Editar, Eliminar |

La Gerencia General define esta matriz para cada rol —e incluso para un usuario puntual si hace falta una excepción— desde el módulo de configuración.

---

## 4. Módulos Funcionales

### 4.1 Módulo de Citas
Registro manual por parte del personal (no autoservicio). Canales de solicitud: correo electrónico (Gmail) y presencial.

**Datos por cita:**
- Cliente (vinculado a ficha de cliente, ver 4.8)
- Fecha y hora preferida / fecha y hora confirmada
- Motivo: compra, servicio técnico, consulta
- Estado: pendiente, confirmada, cancelada, atendida
- Sucursal asignada
- Canal de origen (Gmail o presencial) — *dato agregado para medir de dónde provienen más solicitudes*
- Observaciones / notas del vendedor

**Regla de negocio:** una cita en estado "atendida" debe poder vincularse automáticamente a una venta o a una orden de trabajo generada, para trazabilidad completa del embudo cita → transacción.

### 4.2 Módulo de Proveedores
**Datos obligatorios:**
- Nombre / Razón social
- Contacto, teléfono, email
- Tipo: relojes, piezas originales, piezas no originales, lubricantes, herramientas
- Condiciones de pago y plazos de entrega
- Historial de compras
- Calificación de confiabilidad (ej. escala 1-5, con criterios: cumplimiento de plazos, calidad, soporte postventa)
- Documentos legales: RUC/NIT, certificados de distribución autorizada si aplica

**Ampliación sugerida:** registrar **tiempo de entrega promedio real vs. pactado** por proveedor, para retroalimentar la calificación de confiabilidad de forma automática en lugar de manual.

### 4.3 Módulo de Técnicos (RRHH técnico)
**Datos:**
- Nombre completo
- Especialidades (Rolex, Omega, complicaciones, etc.)
- Certificaciones / formación
- Nivel de acceso al sistema
- Historial de órdenes de trabajo asignadas y tiempos de ejecución
- Productividad (para reportes: órdenes completadas, tiempo promedio, margen generado)
- **Costo interno de mano de obra** (sueldo fijo, y esquema de comisiones/bonos si aplica — ver sección 6)
- Sucursal(es) donde trabaja

### 4.4 Módulo de Inventario — Relojes
Ficha detallada por unidad física (no solo por modelo), dado que el número de serie es único:

| Campo | Detalle |
|---|---|
| Marca | — |
| Referencia / Modelo exacto | — |
| Número de serie | Único e irrepetible, clave de trazabilidad |
| Calibre / Movimiento | Vinculado a ficha de lubricación (ver 4.6) |
| Año de fabricación | Si se conoce |
| Material de caja y brazalete | — |
| Color de esfera | — |
| Tipo de cristal | Zafiro, mineral, acrílico, etc. |
| Resistencia al agua | — |
| Estado | Nuevo / usado |
| Costo de adquisición | — |
| Precio de venta | — |
| Fecha de ingreso a stock | — |
| Proveedor | Vínculo a ficha de proveedor |
| Full Set | Sí/No + detalle (caja, papeles, garantía, eslabones extra, etc.) |
| Sucursal actual | Para control multi-sucursal |
| Historial de servicios | Todas las órdenes de trabajo vinculadas al número de serie |
| Historial de transferencias entre sucursales | Fecha, origen, destino, motivo |

**Regla de negocio:** el stock máximo recomendado por modelo/marca es ~12 unidades; el sistema puede alertar automáticamente cuando se acerque a ese límite o cuando quede 1 unidad disponible (alerta de reposición). Un reloj dañado, perdido o robado se da de baja del stock activo a través del módulo de Mermas y Pérdidas (ver 4.12), sin perder su historial.

### 4.5 Módulo de Piezas y Repuestos
- Código de pieza, descripción, tipo (original / no original de calidad equivalente)
- Calibre(s)/modelo(s) compatibles
- Proveedor
- Costo de adquisición y precio de venta (si se vende suelta)
- Stock disponible y stock mínimo (para alertas de reposición)
- Historial de uso en órdenes de trabajo

### 4.6 Módulo de Lubricación Técnica (Fichas por Calibre)
Cada calibre tiene asociada una ficha técnica con los puntos de lubricación y el producto Moebius recomendado. El técnico debe poder **marcar qué producto usó realmente en cada punto**, lo cual permite auditar desviaciones respecto a la recomendación y calcular consumo real de insumos.

| Código Moebius | Uso recomendado |
|---|---|
| 9010 | Pivotes rápidos de baja carga (balanza, rueda de escape, tren rápido) |
| 9104 / HP-1300 | Pivotes de mayor presión (centro, tercera, barrilete, automáticos) |
| 9415 | Paletas del áncora (escapement) |
| 9501 / 9504 | Mecanismo de cuerda, puesta en hora, calendario |
| 8200 / 8217 | Resorte de barrilete y paredes del barrilete |
| 8513 / 8516 | Juntas de estanqueidad (gaskets) |

**Datos por ficha de calibre:** marca/calibre, lista de puntos de lubricación, producto recomendado por punto, notas técnicas (ej. cantidad aproximada, precauciones).

**Registro en la orden de trabajo:** punto de lubricación → producto recomendado → producto realmente usado → técnico que lo aplicó → fecha.

### 4.7 Módulo de Órdenes de Trabajo / Servicio Técnico
- Reloj (número de serie), cliente, técnico asignado
- Motivo del servicio, diagnóstico, trabajo realizado
- Piezas usadas (con costo)
- Productos de lubricación usados (ver 4.6)
- Costo interno de mano de obra
- Precio cobrado al cliente
- Margen calculado automáticamente = precio cobrado − (costo de piezas + costo de mano de obra + insumos)
- Estado: recibido, en diagnóstico, en reparación, listo, entregado
- Tiempos: fecha de ingreso, fecha estimada de entrega, fecha real de entrega (para "tiempo medio de servicio")
- Garantía del servicio (periodo y cobertura)

### 4.8 Módulo de Clientes (CRM básico) — *ampliación necesaria*
No estaba detallado en el planteamiento original, pero es indispensable para poder generar el reporte de "mejores clientes" y para vincular citas, ventas y servicios.

**Datos sugeridos:**
- Nombre completo / razón social (si es persona jurídica)
- Cédula/RUC, teléfono, email, dirección
- Historial de compras (relojes adquiridos)
- Historial de servicios técnicos
- Fecha de nacimiento (opcional, útil para campañas de fidelización)
- Preferencias (marcas de interés, tipo de complicaciones, etc.)
- Notas del vendedor
- Nivel de fidelización actual (ver 4.8.1) y cupones/beneficios activos

Clasificación automática de clientes según volumen de compra + servicios, usada tanto para reportes ("mejores clientes") como para asignar el nivel de fidelización correspondiente.

#### 4.8.1 Programa de Fidelización
Niveles calculados automáticamente según el histórico de compras y servicios del cliente (monto acumulado, frecuencia, o una combinación — criterio configurable, ver sección 9).

| Nivel (ejemplo) | Criterio orientativo | Beneficios propuestos |
|---|---|---|
| Bronce (cliente nuevo) | Primera compra o servicio registrado | Bienvenida, alta en el sistema de fidelización |
| Plata (frecuente) | Monto acumulado o número de compras/servicios superado en el año | Descuento preferencial en servicio técnico, prioridad de agenda |
| Oro (VIP) | Monto acumulado alto o cliente recurrente de varios años | Descuento mayor, invitación a eventos/lanzamientos, condiciones especiales en mantenimiento preventivo |

**Notas de diseño:**
- Nombres, umbrales y beneficios de cada nivel deben ser **configurables por la Gerencia General** (ver sección 9), no valores fijos en el sistema.
- El nivel del cliente se recalcula automáticamente al registrarse una nueva compra o servicio; el sistema conserva el historial de cambios de nivel.
- Debe existir un reporte de clientes agrupados por nivel, para campañas dirigidas.

#### 4.8.2 Descuentos y Promociones
Se contemplan dos mecanismos, no excluyentes:

| Mecanismo | Descripción | Ejemplo de uso |
|---|---|---|
| Descuento general | Se aplica automáticamente a un segmento (nivel de fidelización, tipo de cliente) o a toda venta/servicio durante un periodo | "10% en mantenimiento por el aniversario de la tienda" |
| Cupón | Código o beneficio puntual asignado a un cliente específico, con vigencia y condiciones propias | Cupón de cumpleaños, cupón de reactivación para clientes inactivos |

**Datos a gestionar por descuento/cupón:**
- Tipo (general o cupón), porcentaje o monto fijo
- Alcance: producto/servicio específico, marca, o toda la tienda
- Segmento aplicable (todos, nivel de fidelización específico, cliente puntual)
- Vigencia (fecha inicio – fecha fin) o evento asociado (cumpleaños del cliente, aniversario de la tienda, fechas comerciales específicas)
- Límite de uso (una vez, varias veces, por cliente o global)
- Código del cupón (si aplica) y estado (activo, usado, vencido)

**Regla de negocio:** todo descuento o cupón aplicado debe quedar registrado en la venta u orden de trabajo correspondiente, de modo que el margen real (sección 5) se calcule sobre el precio final ya descontado, no sobre el precio de lista.

**Regla de negocio (margen mínimo protegido):** ningún descuento ni cupón puede reducir el precio final por debajo de un margen mínimo configurable (definido como % sobre el costo, o monto mínimo, por producto/marca o global — ver sección 9.1). Al aplicar un descuento, el sistema calcula el margen resultante y bloquea la operación —o exige autorización expresa de Gerencia General— si ese margen cae por debajo del mínimo definido.

### 4.9 Módulo Multi-Sucursal
Desde el diseño inicial, aunque se opere con una sola sucursal al inicio.

Cada sucursal gestiona de forma independiente:
- Stock de relojes y piezas
- Técnicos asignados
- Caja y movimientos de dinero
- Gastos operativos propios
- Reportes locales

**Funcionalidad transversal:**
- Transferencia de relojes o piezas entre sucursales, con registro de fecha, motivo, responsable de envío/recepción y actualización automática del inventario en ambas sucursales.
- Reportes consolidados (todas las sucursales) o filtrados por sucursal, visibles según el rol del usuario.

### 4.10 Módulo Contable y Financiero
Sin llegar a un ERP contable completo, pero con trazabilidad suficiente para cumplir con la ley y calcular márgenes reales:

- Libro diario (todas las operaciones)
- Libro mayor
- Estado de resultados (ingresos por ventas + servicios − costos − gastos)
- Balance de comprobación
- Control de caja y bancos
- Registro de cheques
- Cuentas por pagar a proveedores
- Cuentas por cobrar a clientes
- **Registro de gastos operativos** (ver detalle en 4.10.1)

#### 4.10.1 Categorías de gastos a registrar (por sucursal y por tipo)

| Categoría | Ejemplos |
|---|---|
| Local / operativos | Arriendo, luz, agua, internet/wifi, teléfono, seguridad/alarma, limpieza, seguros del local y mercancía, impuestos municipales |
| Personal | Sueldos de técnicos, sueldos de vendedores/administrativos, aportes de seguridad social, bonos o comisiones |
| Otros | Publicidad y marketing, materiales de oficina, mantenimiento de herramientas y equipos, capacitación de técnicos, transporte/envíos, comisiones bancarias y de tarjetas |
| Mermas y pérdidas | Relojes o piezas dañados, perdidos o robados, registrados a costo de adquisición (ver módulo 4.12) |

La categorización por sucursal y por tipo es indispensable para que los reportes de margen reflejen la rentabilidad real después de todos los costos y gastos, no solo el margen bruto de venta/servicio.

### 4.11 Módulo de Reportes y Dashboards

Los reportes se organizan en dos niveles, siguiendo la separación habitual entre información operativa (consulta directa, del día a día) e información táctica/analítica (agregaciones y comparaciones, orientada a decisiones de gestión).

#### 4.11.1 Reportes simples (operativos)
Consulta directa, sin cálculos agregados complejos, para el trabajo diario del personal:

| Reporte | Uso |
|---|---|
| Agenda de citas del día/semana | Operación diaria de mostrador |
| Estado de inventario actual (relojes y piezas) | Consulta rápida de disponibilidad |
| Órdenes de trabajo en curso y su estado | Seguimiento diario del taller |
| Cuentas por cobrar pendientes | Seguimiento de cobros |
| Historial de un cliente puntual | Atención personalizada en mostrador |
| Historial de servicios de un reloj (por número de serie) | Consulta técnica al recibir un reloj |

#### 4.11.2 Reportes complejos (analíticos / tácticos)
Requieren agregación, comparación entre periodos o cruces entre varias entidades; orientados a gerencia y administración:

| Reporte | Propósito |
|---|---|
| Mejores clientes | Por volumen de compra + servicios |
| Margen por reloj vendido | Costo vs. precio de venta |
| Margen por servicio / orden de trabajo | Precio cobrado − costo real (mano de obra + piezas + insumos) |
| Margen por marca y por modelo | Rentabilidad comparada |
| Rotación de stock | Días promedio en inventario antes de venderse |
| Piezas más usadas y su costo | Consumo de repuestos |
| Productividad por técnico | Órdenes completadas, tiempos, margen generado, bonos alcanzados |
| Valor total del inventario | Relojes + piezas, a costo y a precio de venta |
| Comparativo costo vs. precio de venta | Global y segmentado |
| Tiempo medio de servicio | Desde ingreso hasta entrega |
| Tasa de reposición de piezas | Frecuencia de recompra a proveedores |
| Rentabilidad neta por sucursal | Descontando gastos operativos, no solo margen bruto |
| Tasa de conversión de citas a venta/servicio | Efectividad comercial del embudo de atención |
| Desviación de lubricación | Producto recomendado vs. producto realmente usado |
| Antigüedad de cuentas por cobrar/pagar (aging) | Gestión de liquidez |
| Efectividad de fidelización y descuentos | Ventas/servicios generados por nivel o cupón vs. costo del beneficio otorgado |
| Clientes por nivel de fidelización | Distribución y evolución de la base de clientes |
| Mermas y pérdidas | Monto, causa y frecuencia de bajas por daño, pérdida o robo |

#### 4.11.3 Alcance recomendado
Para un negocio de este tamaño no conviene construir decenas de reportes desde el inicio. Se recomienda:

- **Panel principal (Gerencia General):** 5-6 indicadores críticos — margen del periodo, rentabilidad neta por sucursal, cuentas por cobrar vencidas, rotación de stock, productividad de técnicos y clientes por nivel de fidelización. Un panel con más de 8-10 indicadores tiende a saturar y dificultar la lectura.
- **Reportes simples:** disponibles en cada módulo, de consulta libre para el personal según su rol.
- **Reportes complejos:** con filtros por periodo, sucursal, marca o técnico, accesibles principalmente para gerencia/administración.

El número exacto de reportes puede ajustarse en el diseño detallado, pero la separación simple/complejo debe reflejarse en el modelo de datos y en los permisos de acceso.

### 4.12 Módulo de Mermas y Pérdidas
Registra cualquier reloj o pieza que sale de stock por daño, pérdida, robo o defecto, sin haber generado una venta.

**Datos por registro de merma:**
- Bien afectado: reloj (número de serie) o pieza de repuesto (código)
- Causa: daño en tienda, daño en tránsito/transporte, robo o pérdida, defecto de fábrica, daño ocurrido durante un servicio técnico (vinculado a la orden de trabajo correspondiente)
- Fecha del evento y sucursal
- Responsable que reporta el hecho
- Costo de la pérdida (a costo de adquisición, no a precio de venta)
- Estado: en evaluación, dado de baja definitivamente, en reclamo a proveedor, en reclamo a seguro, reparado y reingresado a stock
- Documento de soporte (acta interna, fotografías, denuncia policial si corresponde)
- Usuario que autoriza la baja

**Reglas de negocio:**
- Al confirmarse la baja, el sistema retira el bien del inventario activo (4.4/4.5) pero conserva su historial completo para trazabilidad.
- El costo de la pérdida se registra automáticamente en el libro de cuentas (4.10.1) como gasto/pérdida extraordinaria, separado de los gastos operativos regulares.
- Si el daño ocurrió durante un servicio técnico, la merma queda vinculada a la orden de trabajo y al técnico responsable, para trazabilidad interna (sin que esto implique sanción automática).
- Las mermas por encima de un monto configurable requieren aprobación de la Gerencia General antes de darse de baja definitivamente (ver 9.2).

---

## 5. Personal Técnico: Costeo y Margen del Servicio

Los técnicos son personal de planta (relación de dependencia), por lo que su costo de mano de obra forma parte del costo interno del servicio y debe distinguirse claramente del precio cobrado al cliente.

**Lógica de cálculo:**

```
Costo interno del servicio = Costo de mano de obra del técnico (prorrateado por orden)
                              + Costo de piezas usadas
                              + Costo de insumos (lubricantes, etc.)

Precio de venta del servicio = Costo interno + Margen definido por el negocio (ej. 40-60%, configurable)

Margen real de la orden = Precio de venta del servicio − Costo interno
```

**Requisitos del sistema:**
- Registrar el costo interno de mano de obra por técnico (sueldo fijo + esquema de comisiones/bonos por productividad, si existe).
- Definir el precio de venta del servicio, con el margen ya incorporado.
- Calcular automáticamente el margen real por orden de trabajo, sin exponer el costo interno de mano de obra al cliente.
- Permitir que el margen objetivo sea configurable (por tipo de servicio, por sucursal o global), no un valor fijo en el sistema.

**Esquema de bono por productividad (configurable):**
El sistema debe permitir definir reglas de bono para técnicos, evaluadas sobre indicadores objetivos, por ejemplo:
- Número de órdenes de trabajo completadas en el periodo.
- Cumplimiento de los tiempos estimados de entrega.
- Margen generado por las órdenes atendidas.
- Calidad (baja tasa de reprocesos o reclamos sobre el mismo reloj).

El bono puede definirse como monto fijo por meta alcanzada, porcentaje sobre el margen generado, o una combinación de ambos. La fórmula y los umbrales deben ser **configurables por la Gerencia General** (ver sección 9), no valores fijos en el sistema. El sistema debe calcular automáticamente el bono acumulado por técnico y por periodo, y reflejarlo como parte del costo de mano de obra en los reportes de margen.

---

## 6. Requisitos No Funcionales

- **Trazabilidad:** cada número de serie debe mantener un historial inalterable de eventos (ingreso, venta, servicios, transferencias entre sucursales).
- **Auditoría:** registro de quién hizo qué cambio y cuándo (especialmente en precios, márgenes, y estados de órdenes de trabajo).
- **Control de acceso basado en roles**, con posibilidad de restringir información financiera sensible (costos, márgenes) a roles administrativos.
- **Escalabilidad multi-sucursal** desde el modelo de datos, aunque el volumen inicial sea bajo.
- **Respaldo de datos (backup)** periódico, dado que se maneja información legal/contable.
- **Usabilidad**, considerando que parte del personal (vendedores) no necesariamente tiene perfil técnico.

---

## 7. Cumplimiento Legal y Fiscal (Ecuador) — *ampliación relevante*

Dado que el negocio opera en Ecuador, se recomienda contemplar desde el diseño:

- **Facturación electrónica ante el SRI**: los comprobantes de venta (facturas, notas de crédito) deben poder generarse en formato electrónico autorizado, no solo como registro interno.
- **Retenciones en la fuente** a proveedores, cuando aplique.
- **Libros contables alineados a NIIF para PYMES**, ya que la normativa ecuatoriana exige este marco para pequeñas empresas.
- **Garantías legales** conforme a la Ley Orgánica de Defensa del Consumidor, en particular para diferenciar garantía de fábrica vs. garantía del servicio técnico propio.

Esto no implica construir un módulo contable completo, pero sí que el modelo de datos del libro de cuentas sea compatible con estos requisitos desde el inicio, para evitar rediseños posteriores.

---

## 8. Propuestas de Ampliación (pendientes de decisión)

Ya se incorporaron como decisiones del negocio: programa de fidelización con niveles y beneficios (4.8.1), descuentos y cupones con margen mínimo protegido (4.8.2), bono de productividad para técnicos (sección 5), permisos por módulo y por operación CRUD (3.1), control de mermas y pérdidas (4.12), y parametrización general a cargo de Gerencia General (sección 9). Se descartó la compra-venta o consignación de relojes usados. Quedan como propuestas abiertas, aún no confirmadas:

| Propuesta | Justificación |
|---|---|
| Garantía diferenciada (fábrica vs. tienda) | Claridad legal y comercial ante reclamos |
| Certificado digital de autenticidad/garantía | Valor percibido por el cliente, trazabilidad documental |
| Facturación electrónica (SRI) | Obligación legal en Ecuador (ver sección 7) |
| Alertas automáticas de reposición de stock | Evita quiebres o excesos de inventario por modelo |
| Recordatorios de mantenimiento preventivo | Fideliza al cliente y genera recurrencia de servicio |
| Trazabilidad de desviación en lubricación | Control de calidad técnica y de consumo de insumos |
| Comisiones también para vendedores (no solo técnicos) | Consistencia en el esquema de incentivos |
| Reporte de conversión de citas a venta/servicio | Mide efectividad comercial del embudo de atención |

---

## 9. Parámetros Configurables del Sistema

Principio de diseño transversal: **todo valor que dependa de una decisión de negocio —y no de una regla fija del dominio relojero— debe ser configurable desde el sistema por la Gerencia General**, sin requerir cambios de código.

### 9.1 Configuración comercial y financiera
- Margen objetivo de venta de relojes (global, por marca o por modelo).
- Margen objetivo de servicio técnico (global, por tipo de servicio o por sucursal).
- Precios de referencia y listas de precios.
- Reglas de descuentos y cupones: porcentajes, vigencias, segmentos aplicables (ver 4.8.2).
- Niveles de fidelización, sus umbrales y sus beneficios (ver 4.8.1).
- Fórmula y umbrales del bono de productividad por técnico (ver sección 5).
- Comisiones de vendedores, si se implementan.
- Margen mínimo permitido tras aplicar descuentos o cupones (global, por marca o por producto — ver 4.8.2).

### 9.2 Configuración de inventario y operación
- Stock máximo recomendado por modelo/marca (por defecto ~12 unidades).
- Umbral de alerta de reposición de stock (relojes y piezas).
- Periodo de garantía de fábrica y de garantía de tienda por tipo de producto/servicio.
- Tiempos estimados de servicio por tipo de reparación (para medir cumplimiento).
- Monto de merma a partir del cual se requiere aprobación de Gerencia General para la baja definitiva (ver 4.12).

### 9.3 Configuración organizativa
- Roles y permisos de acceso por módulo, con permisos independientes de Crear/Consultar/Editar/Eliminar por módulo y por rol o usuario (ver 3.1).
- Sucursales activas y sus datos (nombre, dirección, responsable).
- Categorías de gastos operativos.
- Canales de solicitud de citas habilitados (actualmente: correo electrónico y presencial).

### 9.4 Alcance de la configuración
Estas pantallas de configuración deben ser accesibles solo para el rol de Gerencia General (o a quien este delegue explícitamente), quedando fuera del alcance de vendedores y técnicos. Todo cambio de configuración debe quedar registrado en el módulo de auditoría (sección 6), dado que afecta directamente el cálculo de márgenes y bonos ya generados o futuros.

---

## 10. Notas para la Etapa de Diseño

Este documento es la base funcional; los siguientes pasos naturales serían:
1. Modelo entidad-relación (diagrama ER) a partir de las entidades descritas en la sección 4.
2. Definición de la matriz de permisos por rol.
3. Priorización de módulos para un MVP (probablemente: inventario de relojes, órdenes de trabajo, citas y reportes básicos primero; contabilidad completa y multi-sucursal después, si el negocio inicia con una sola sucursal).
