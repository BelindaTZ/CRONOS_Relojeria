-- =====================================================================
-- 01_operativo_postgres.sql
-- Esquema operativo (OLTP) del sistema de gestión para relojería de
-- alta gama. Derivado de especificacion_sistema_relojeria.md.
-- Convenciones: snake_case, PK SERIAL, timestamps en toda tabla,
-- enums implementados como VARCHAR + CHECK (más simple de alterar
-- que un tipo ENUM nativo de Postgres). Normalizado a 3FN: todo
-- atributo multivaluado vive en su propia tabla (especialidades,
-- preferencias, full-set, documentos adjuntos).
-- Pendiente de una segunda pasada: vistas de reporting (libro_mayor,
-- estado_resultados, balance_comprobacion) construidas sobre
-- libro_diario -- no se materializan como tablas propias para no
-- duplicar datos (Principio VII, DRY).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. SUCURSALES (sección 4.9)
-- ---------------------------------------------------------------------
CREATE TABLE sucursales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    direccion VARCHAR(255),
    responsable VARCHAR(150),
    activa BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 2. RBAC DE DOS NIVELES: rol -> modulo, rol -> modulo -> operacion
--    (sección 3.1: Crear/Consultar/Editar/Eliminar)
-- ---------------------------------------------------------------------
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE modulos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
);

-- Nivel 1: acceso al módulo
CREATE TABLE permisos_rol_modulo (
    rol_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    modulo_id INTEGER NOT NULL REFERENCES modulos(id) ON DELETE CASCADE,
    PRIMARY KEY (rol_id, modulo_id)
);

-- Nivel 2: operación dentro del módulo. La FK compuesta obliga a que
-- el rol ya tenga acceso al módulo (Principio IV de la constitución)
-- antes de poder tener un permiso de operación sobre él.
CREATE TABLE permisos_rol_modulo_operacion (
    rol_id INTEGER NOT NULL,
    modulo_id INTEGER NOT NULL,
    operacion VARCHAR(20) NOT NULL CHECK (operacion IN ('crear','consultar','editar','eliminar')),
    PRIMARY KEY (rol_id, modulo_id, operacion),
    FOREIGN KEY (rol_id, modulo_id) REFERENCES permisos_rol_modulo(rol_id, modulo_id) ON DELETE CASCADE
);

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol_id INTEGER NOT NULL REFERENCES roles(id),
    sucursal_id INTEGER REFERENCES sucursales(id),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_usuarios_rol_id ON usuarios(rol_id);
CREATE INDEX idx_usuarios_sucursal_id ON usuarios(sucursal_id);

-- Auditoría genérica (Principio II / trazabilidad: quién cambió qué y cuándo)
CREATE TABLE auditoria_cambios (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    tabla_afectada VARCHAR(100) NOT NULL,
    registro_id INTEGER NOT NULL,
    accion VARCHAR(20) NOT NULL CHECK (accion IN ('crear','editar','eliminar')),
    valores_anteriores JSONB,
    valores_nuevos JSONB,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_auditoria_tabla_registro ON auditoria_cambios(tabla_afectada, registro_id);

-- Documentos adjuntos genéricos (fotos de merma, certificados de
-- proveedor, actas, etc.) — un mismo hecho puede tener varios archivos,
-- así que vive en su propia tabla en vez de una columna de URL única.
CREATE TABLE documentos_adjuntos (
    id SERIAL PRIMARY KEY,
    entidad_tipo VARCHAR(30) NOT NULL CHECK (entidad_tipo IN ('merma','proveedor','orden_trabajo','venta','cliente')),
    entidad_id INTEGER NOT NULL,
    tipo_documento VARCHAR(50),
    url_minio VARCHAR(500) NOT NULL,
    subido_por_usuario_id INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_documentos_entidad ON documentos_adjuntos(entidad_tipo, entidad_id);

-- ---------------------------------------------------------------------
-- 3. PROVEEDORES (sección 4.2)
-- ---------------------------------------------------------------------
CREATE TABLE proveedores (
    id SERIAL PRIMARY KEY,
    razon_social VARCHAR(200) NOT NULL,
    contacto VARCHAR(150),
    telefono VARCHAR(30),
    email VARCHAR(255),
    tipo VARCHAR(30) NOT NULL CHECK (tipo IN ('relojes','piezas_originales','piezas_no_originales','lubricantes','herramientas')),
    condiciones_pago VARCHAR(200),
    plazo_entrega_dias INTEGER CHECK (plazo_entrega_dias >= 0),
    ruc_nit VARCHAR(50),
    calificacion_confiabilidad NUMERIC(2,1) CHECK (calificacion_confiabilidad BETWEEN 1 AND 5),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_proveedores_tipo ON proveedores(tipo);

-- Órdenes de compra a proveedor: el documento real detrás de "historial
-- de compras" (4.2) y de "tasa de reposición de piezas" (4.11.2) — sin
-- esto solo se veía el stock resultante, no la transacción en sí.
CREATE TABLE ordenes_compra (
    id SERIAL PRIMARY KEY,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    fecha_orden DATE NOT NULL,
    fecha_recepcion DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','recibida','cancelada')),
    creado_por_usuario_id INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ordenes_compra_proveedor ON ordenes_compra(proveedor_id);

CREATE TABLE ordenes_compra_detalle (
    id SERIAL PRIMARY KEY,
    orden_compra_id INTEGER NOT NULL REFERENCES ordenes_compra(id) ON DELETE CASCADE,
    reloj_id INTEGER,
    pieza_id INTEGER,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    costo_unitario NUMERIC(12,2) NOT NULL CHECK (costo_unitario >= 0),
    CHECK (reloj_id IS NOT NULL OR pieza_id IS NOT NULL)
);
CREATE INDEX idx_ocd_orden_compra ON ordenes_compra_detalle(orden_compra_id);

-- ---------------------------------------------------------------------
-- 4. TÉCNICOS (sección 4.3) + especialidades + bono de productividad (sección 5)
-- ---------------------------------------------------------------------
CREATE TABLE tecnicos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER UNIQUE REFERENCES usuarios(id),
    nombre_completo VARCHAR(150) NOT NULL,
    certificaciones TEXT,
    sucursal_id INTEGER REFERENCES sucursales(id),
    costo_mano_obra_mensual NUMERIC(10,2) CHECK (costo_mano_obra_mensual >= 0),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_tecnicos_sucursal_id ON tecnicos(sucursal_id);

-- Normalizado: un técnico puede tener varias especialidades (Rolex,
-- Omega, complicaciones...) — antes vivía como texto libre.
CREATE TABLE tecnicos_especialidades (
    tecnico_id INTEGER NOT NULL REFERENCES tecnicos(id) ON DELETE CASCADE,
    especialidad VARCHAR(100) NOT NULL,
    PRIMARY KEY (tecnico_id, especialidad)
);

CREATE TABLE bonos_productividad (
    id SERIAL PRIMARY KEY,
    tecnico_id INTEGER NOT NULL REFERENCES tecnicos(id),
    periodo VARCHAR(20) NOT NULL,
    monto_calculado NUMERIC(10,2) NOT NULL CHECK (monto_calculado >= 0),
    criterios_aplicados JSONB,
    fecha_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tecnico_id, periodo)
);
CREATE INDEX idx_bonos_tecnico_id ON bonos_productividad(tecnico_id);

-- ---------------------------------------------------------------------
-- 5. CALIBRES Y FICHAS DE LUBRICACIÓN (sección 4.6)
-- ---------------------------------------------------------------------
CREATE TABLE calibres (
    id SERIAL PRIMARY KEY,
    marca VARCHAR(100) NOT NULL,
    nombre_calibre VARCHAR(100) NOT NULL,
    UNIQUE (marca, nombre_calibre)
);

CREATE TABLE fichas_lubricacion (
    id SERIAL PRIMARY KEY,
    calibre_id INTEGER NOT NULL REFERENCES calibres(id) ON DELETE CASCADE,
    punto_lubricacion VARCHAR(150) NOT NULL,
    producto_recomendado VARCHAR(50) NOT NULL,
    notas TEXT
);
CREATE INDEX idx_fichas_lubricacion_calibre_id ON fichas_lubricacion(calibre_id);

-- ---------------------------------------------------------------------
-- 6. RELOJES / INVENTARIO (sección 4.4)
-- ---------------------------------------------------------------------
CREATE TABLE relojes (
    id SERIAL PRIMARY KEY,
    marca VARCHAR(100) NOT NULL,
    referencia_modelo VARCHAR(100) NOT NULL,
    numero_serie VARCHAR(100) UNIQUE NOT NULL,
    calibre_id INTEGER REFERENCES calibres(id),
    anio_fabricacion INTEGER,
    material_caja VARCHAR(100),
    material_brazalete VARCHAR(100),
    color_esfera VARCHAR(50),
    tipo_cristal VARCHAR(50),
    resistencia_agua VARCHAR(50),
    estado_condicion VARCHAR(10) NOT NULL DEFAULT 'nuevo' CHECK (estado_condicion IN ('nuevo','usado')),
    costo_adquisicion NUMERIC(12,2) NOT NULL CHECK (costo_adquisicion >= 0),
    precio_venta NUMERIC(12,2) NOT NULL CHECK (precio_venta >= 0),
    fecha_ingreso_stock DATE NOT NULL,
    proveedor_id INTEGER REFERENCES proveedores(id),
    full_set BOOLEAN NOT NULL DEFAULT false,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    estado_stock VARCHAR(20) NOT NULL DEFAULT 'disponible' CHECK (estado_stock IN ('disponible','reservado','vendido','de_baja')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_relojes_marca_modelo ON relojes(marca, referencia_modelo);
CREATE INDEX idx_relojes_sucursal_id ON relojes(sucursal_id);
CREATE INDEX idx_relojes_estado_stock ON relojes(estado_stock);

-- Normalizado: qué incluye el full set (caja, papeles, garantía,
-- eslabones extra...) — antes era una sola columna de texto libre.
CREATE TABLE relojes_full_set_items (
    reloj_id INTEGER NOT NULL REFERENCES relojes(id) ON DELETE CASCADE,
    item VARCHAR(50) NOT NULL CHECK (item IN ('caja','papeles','garantia_tarjeta','eslabones_extra','manual','otro')),
    PRIMARY KEY (reloj_id, item)
);

-- ---------------------------------------------------------------------
-- 7. PIEZAS DE REPUESTO (sección 4.5)
-- ---------------------------------------------------------------------
CREATE TABLE piezas_repuesto (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    descripcion VARCHAR(200) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('original','no_original')),
    proveedor_id INTEGER REFERENCES proveedores(id),
    costo_adquisicion NUMERIC(10,2) NOT NULL CHECK (costo_adquisicion >= 0),
    precio_venta NUMERIC(10,2) CHECK (precio_venta >= 0),
    stock_disponible INTEGER NOT NULL DEFAULT 0 CHECK (stock_disponible >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_piezas_sucursal_id ON piezas_repuesto(sucursal_id);

CREATE TABLE piezas_calibres_compatibles (
    pieza_id INTEGER NOT NULL REFERENCES piezas_repuesto(id) ON DELETE CASCADE,
    calibre_id INTEGER NOT NULL REFERENCES calibres(id) ON DELETE CASCADE,
    PRIMARY KEY (pieza_id, calibre_id)
);

ALTER TABLE ordenes_compra_detalle
    ADD CONSTRAINT fk_ocd_reloj FOREIGN KEY (reloj_id) REFERENCES relojes(id),
    ADD CONSTRAINT fk_ocd_pieza FOREIGN KEY (pieza_id) REFERENCES piezas_repuesto(id);

-- ---------------------------------------------------------------------
-- 8. FIDELIZACIÓN Y CLIENTES (sección 4.8, 4.8.1)
-- ---------------------------------------------------------------------
CREATE TABLE niveles_fidelizacion (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    orden_jerarquico INTEGER NOT NULL UNIQUE,
    umbral_monto_acumulado NUMERIC(12,2),
    umbral_compras_servicios INTEGER,
    beneficios TEXT
);

CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nombre_razon_social VARCHAR(200) NOT NULL,
    cedula_ruc VARCHAR(20),
    telefono VARCHAR(30),
    email VARCHAR(255),
    direccion VARCHAR(255),
    fecha_nacimiento DATE,
    notas TEXT,
    nivel_fidelizacion_id INTEGER REFERENCES niveles_fidelizacion(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_clientes_nivel_fidelizacion_id ON clientes(nivel_fidelizacion_id);
CREATE INDEX idx_clientes_email ON clientes(email);

-- Normalizado: preferencias del cliente (marcas de interés, tipo de
-- complicaciones...) — antes era una sola columna de texto libre.
CREATE TABLE clientes_preferencias (
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    tipo_preferencia VARCHAR(30) NOT NULL CHECK (tipo_preferencia IN ('marca','complicacion')),
    valor VARCHAR(100) NOT NULL,
    PRIMARY KEY (cliente_id, tipo_preferencia, valor)
);

CREATE TABLE historial_nivel_fidelizacion (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nivel_fidelizacion_id INTEGER NOT NULL REFERENCES niveles_fidelizacion(id),
    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_historial_nivel_cliente_id ON historial_nivel_fidelizacion(cliente_id);

-- ---------------------------------------------------------------------
-- 9. CITAS (sección 4.1)
-- ---------------------------------------------------------------------
CREATE TABLE citas (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes(id),
    fecha_hora_preferida TIMESTAMP,
    fecha_hora_confirmada TIMESTAMP,
    motivo VARCHAR(20) NOT NULL CHECK (motivo IN ('compra','servicio','consulta')),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','confirmada','cancelada','atendida')),
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    canal_origen VARCHAR(20) NOT NULL CHECK (canal_origen IN ('gmail','presencial')),
    observaciones TEXT,
    registrado_por_usuario_id INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_citas_cliente_id ON citas(cliente_id);
CREATE INDEX idx_citas_sucursal_estado ON citas(sucursal_id, estado);

-- ---------------------------------------------------------------------
-- 10. DESCUENTOS Y CUPONES (sección 4.8.2, con margen mínimo protegido)
--     Se define antes de ventas/ordenes_trabajo porque ambas lo referencian.
-- ---------------------------------------------------------------------
CREATE TABLE descuentos_cupones (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('general','cupon')),
    valor_porcentaje NUMERIC(5,2) CHECK (valor_porcentaje BETWEEN 0 AND 100),
    valor_monto_fijo NUMERIC(10,2) CHECK (valor_monto_fijo >= 0),
    alcance VARCHAR(20) NOT NULL CHECK (alcance IN ('producto','marca','tienda')),
    nivel_fidelizacion_id INTEGER REFERENCES niveles_fidelizacion(id),
    cliente_id INTEGER REFERENCES clientes(id),
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    evento_asociado VARCHAR(100),
    limite_uso INTEGER,
    codigo_cupon VARCHAR(50) UNIQUE,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','usado','vencido')),
    margen_minimo_protegido NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (fecha_fin >= fecha_inicio),
    CHECK ((tipo = 'cupon' AND cliente_id IS NOT NULL) OR (tipo = 'general')),
    CHECK (
        (valor_porcentaje IS NOT NULL AND valor_monto_fijo IS NULL) OR
        (valor_porcentaje IS NULL AND valor_monto_fijo IS NOT NULL)
    )
);
CREATE INDEX idx_descuentos_estado ON descuentos_cupones(estado);
CREATE INDEX idx_descuentos_cliente_id ON descuentos_cupones(cliente_id);

-- ---------------------------------------------------------------------
-- 11. ÓRDENES DE TRABAJO / SERVICIO TÉCNICO (sección 4.7)
-- ---------------------------------------------------------------------
CREATE TABLE ordenes_trabajo (
    id SERIAL PRIMARY KEY,
    reloj_id INTEGER NOT NULL REFERENCES relojes(id),
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    tecnico_id INTEGER REFERENCES tecnicos(id),
    cita_id INTEGER REFERENCES citas(id),
    descuento_cupon_id INTEGER REFERENCES descuentos_cupones(id),
    motivo TEXT NOT NULL,
    diagnostico TEXT,
    trabajo_realizado TEXT,
    costo_mano_obra NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (costo_mano_obra >= 0),
    precio_cobrado NUMERIC(10,2) CHECK (precio_cobrado >= 0),
    margen_calculado NUMERIC(10,2),
    estado VARCHAR(20) NOT NULL DEFAULT 'recibido' CHECK (estado IN ('recibido','en_diagnostico','en_reparacion','listo','entregado')),
    fecha_ingreso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_estimada_entrega DATE,
    fecha_real_entrega TIMESTAMP,
    garantia_periodo_meses INTEGER,
    garantia_cobertura TEXT,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ordenes_trabajo_reloj_id ON ordenes_trabajo(reloj_id);
CREATE INDEX idx_ordenes_trabajo_tecnico_id ON ordenes_trabajo(tecnico_id);
CREATE INDEX idx_ordenes_trabajo_estado ON ordenes_trabajo(estado);

CREATE TABLE ordenes_trabajo_piezas (
    orden_trabajo_id INTEGER NOT NULL REFERENCES ordenes_trabajo(id) ON DELETE CASCADE,
    pieza_id INTEGER NOT NULL REFERENCES piezas_repuesto(id),
    cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    costo_unitario NUMERIC(10,2) NOT NULL CHECK (costo_unitario >= 0),
    PRIMARY KEY (orden_trabajo_id, pieza_id)
);

CREATE TABLE ordenes_trabajo_lubricacion (
    id SERIAL PRIMARY KEY,
    orden_trabajo_id INTEGER NOT NULL REFERENCES ordenes_trabajo(id) ON DELETE CASCADE,
    ficha_lubricacion_id INTEGER NOT NULL REFERENCES fichas_lubricacion(id),
    producto_usado VARCHAR(50) NOT NULL,
    tecnico_id INTEGER REFERENCES tecnicos(id),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ot_lubricacion_orden_id ON ordenes_trabajo_lubricacion(orden_trabajo_id);

-- ---------------------------------------------------------------------
-- 12. VENTAS
-- ---------------------------------------------------------------------
CREATE TABLE ventas (
    id SERIAL PRIMARY KEY,
    reloj_id INTEGER NOT NULL UNIQUE REFERENCES relojes(id),
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    vendedor_usuario_id INTEGER REFERENCES usuarios(id),
    precio_lista NUMERIC(12,2) NOT NULL CHECK (precio_lista >= 0),
    descuento_cupon_id INTEGER REFERENCES descuentos_cupones(id),
    precio_final NUMERIC(12,2) NOT NULL CHECK (precio_final >= 0),
    margen_calculado NUMERIC(12,2),
    medio_pago VARCHAR(20) NOT NULL CHECK (medio_pago IN ('efectivo','transferencia','cheque','tarjeta')),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ventas_cliente_id ON ventas(cliente_id);
CREATE INDEX idx_ventas_sucursal_id ON ventas(sucursal_id);
CREATE INDEX idx_ventas_fecha ON ventas(fecha);

-- ---------------------------------------------------------------------
-- 13. MERMAS Y PÉRDIDAS (sección 4.12)
-- ---------------------------------------------------------------------
CREATE TABLE mermas (
    id SERIAL PRIMARY KEY,
    reloj_id INTEGER REFERENCES relojes(id),
    pieza_id INTEGER REFERENCES piezas_repuesto(id),
    causa VARCHAR(30) NOT NULL CHECK (causa IN ('dano_tienda','dano_transito','robo_perdida','defecto_fabrica','dano_servicio')),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    responsable_usuario_id INTEGER REFERENCES usuarios(id),
    costo_perdida NUMERIC(12,2) NOT NULL CHECK (costo_perdida >= 0),
    estado VARCHAR(30) NOT NULL DEFAULT 'en_evaluacion' CHECK (estado IN ('en_evaluacion','dado_de_baja','reclamo_proveedor','reclamo_seguro','reparado_reingresado')),
    orden_trabajo_id INTEGER REFERENCES ordenes_trabajo(id),
    autorizado_por_usuario_id INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (reloj_id IS NOT NULL OR pieza_id IS NOT NULL)
);
CREATE INDEX idx_mermas_sucursal_id ON mermas(sucursal_id);
CREATE INDEX idx_mermas_estado ON mermas(estado);

-- ---------------------------------------------------------------------
-- 14. TRANSFERENCIAS ENTRE SUCURSALES (sección 4.9)
-- ---------------------------------------------------------------------
CREATE TABLE transferencias_sucursal (
    id SERIAL PRIMARY KEY,
    reloj_id INTEGER REFERENCES relojes(id),
    pieza_id INTEGER REFERENCES piezas_repuesto(id),
    sucursal_origen_id INTEGER NOT NULL REFERENCES sucursales(id),
    sucursal_destino_id INTEGER NOT NULL REFERENCES sucursales(id),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    motivo TEXT,
    responsable_usuario_id INTEGER REFERENCES usuarios(id),
    CHECK (reloj_id IS NOT NULL OR pieza_id IS NOT NULL),
    CHECK (sucursal_origen_id <> sucursal_destino_id)
);
CREATE INDEX idx_transferencias_origen ON transferencias_sucursal(sucursal_origen_id);
CREATE INDEX idx_transferencias_destino ON transferencias_sucursal(sucursal_destino_id);

-- ---------------------------------------------------------------------
-- 15. GASTOS OPERATIVOS (sección 4.10.1)
-- ---------------------------------------------------------------------
CREATE TABLE gastos (
    id SERIAL PRIMARY KEY,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    categoria VARCHAR(30) NOT NULL CHECK (categoria IN ('local_operativo','personal','otros','mermas_perdidas')),
    subcategoria VARCHAR(100),
    monto NUMERIC(12,2) NOT NULL CHECK (monto >= 0),
    fecha DATE NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_gastos_sucursal_categoria ON gastos(sucursal_id, categoria);
CREATE INDEX idx_gastos_fecha ON gastos(fecha);

-- ---------------------------------------------------------------------
-- 16. CUENTAS POR COBRAR / PAGAR (sección 4.10)
-- ---------------------------------------------------------------------
CREATE TABLE cuentas_por_cobrar (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    venta_id INTEGER REFERENCES ventas(id),
    orden_trabajo_id INTEGER REFERENCES ordenes_trabajo(id),
    monto NUMERIC(12,2) NOT NULL CHECK (monto >= 0),
    medio_pago VARCHAR(20) CHECK (medio_pago IN ('efectivo','transferencia','cheque','tarjeta')),
    fecha_vencimiento DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','pagado','vencido')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (venta_id IS NOT NULL OR orden_trabajo_id IS NOT NULL)
);
CREATE INDEX idx_cxc_cliente_id ON cuentas_por_cobrar(cliente_id);
CREATE INDEX idx_cxc_estado ON cuentas_por_cobrar(estado);

CREATE TABLE cuentas_por_pagar (
    id SERIAL PRIMARY KEY,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    orden_compra_id INTEGER REFERENCES ordenes_compra(id),
    monto NUMERIC(12,2) NOT NULL CHECK (monto >= 0),
    fecha_vencimiento DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','pagado','vencido')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_cxp_proveedor_id ON cuentas_por_pagar(proveedor_id);
CREATE INDEX idx_cxp_estado ON cuentas_por_pagar(estado);

-- ---------------------------------------------------------------------
-- 17. CONTROL DE CAJA Y BANCOS + REGISTRO DE CHEQUES (sección 6 del
--     planteamiento original) — faltaban por completo en la primera
--     versión; solo estaban insinuados como "medio_pago = cheque".
-- ---------------------------------------------------------------------
CREATE TABLE cuentas_bancarias (
    id SERIAL PRIMARY KEY,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    banco VARCHAR(100) NOT NULL,
    numero_cuenta VARCHAR(50) NOT NULL,
    tipo_cuenta VARCHAR(20) CHECK (tipo_cuenta IN ('corriente','ahorros')),
    activa BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_cuentas_bancarias_sucursal ON cuentas_bancarias(sucursal_id);

-- Apertura/cierre de caja por sucursal y por turno.
CREATE TABLE cajas_apertura_cierre (
    id SERIAL PRIMARY KEY,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    usuario_apertura_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha_apertura TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    monto_apertura NUMERIC(10,2) NOT NULL CHECK (monto_apertura >= 0),
    usuario_cierre_id INTEGER REFERENCES usuarios(id),
    fecha_cierre TIMESTAMP,
    monto_cierre_declarado NUMERIC(10,2),
    monto_cierre_sistema NUMERIC(10,2),
    diferencia NUMERIC(10,2),
    estado VARCHAR(20) NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta','cerrada')),
    CHECK (fecha_cierre IS NULL OR fecha_cierre >= fecha_apertura)
);
CREATE INDEX idx_cajas_sucursal_id ON cajas_apertura_cierre(sucursal_id);

-- Cada ingreso/egreso de efectivo dentro de un turno de caja, con
-- referencia genérica a la venta/orden de trabajo/gasto que lo originó.
CREATE TABLE movimientos_caja (
    id SERIAL PRIMARY KEY,
    caja_apertura_id INTEGER NOT NULL REFERENCES cajas_apertura_cierre(id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('ingreso','egreso')),
    monto NUMERIC(10,2) NOT NULL CHECK (monto > 0),
    concepto VARCHAR(200) NOT NULL,
    referencia_tipo VARCHAR(30),
    referencia_id INTEGER,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_movimientos_caja_apertura ON movimientos_caja(caja_apertura_id);

-- Cheques recibidos (ligados a una cuenta por cobrar) o emitidos
-- (ligados a una cuenta por pagar) — con su propio ciclo de vida,
-- que un simple enum de medio_pago no puede representar.
CREATE TABLE cheques (
    id SERIAL PRIMARY KEY,
    numero_cheque VARCHAR(30) NOT NULL,
    banco_emisor VARCHAR(100) NOT NULL,
    monto NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    fecha_emision DATE NOT NULL,
    fecha_cobro_estimada DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','cobrado','rechazado','anulado')),
    cuenta_por_cobrar_id INTEGER REFERENCES cuentas_por_cobrar(id),
    cuenta_por_pagar_id INTEGER REFERENCES cuentas_por_pagar(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (cuenta_por_cobrar_id IS NOT NULL OR cuenta_por_pagar_id IS NOT NULL)
);
CREATE INDEX idx_cheques_estado ON cheques(estado);

-- ---------------------------------------------------------------------
-- 18. LIBRO DIARIO simplificado (sección 4.10) — libro mayor, estado
--     de resultados y balance de comprobación se derivan de aquí
--     mediante vistas, no como tablas adicionales.
-- ---------------------------------------------------------------------
CREATE TABLE libro_diario (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    descripcion TEXT NOT NULL,
    cuenta_debe VARCHAR(100) NOT NULL,
    cuenta_haber VARCHAR(100) NOT NULL,
    monto NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    referencia_tipo VARCHAR(30),
    referencia_id INTEGER,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_libro_diario_fecha ON libro_diario(fecha);
CREATE INDEX idx_libro_diario_referencia ON libro_diario(referencia_tipo, referencia_id);

-- ---------------------------------------------------------------------
-- 19. PARÁMETROS CONFIGURABLES por Gerencia General (sección 9)
-- ---------------------------------------------------------------------
CREATE TABLE configuracion_parametros (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor VARCHAR(255) NOT NULL,
    descripcion TEXT,
    modificado_por_usuario_id INTEGER REFERENCES usuarios(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 20. NOTIFICACIONES AUTOMATIZADAS (feature 014: SendGrid)
-- ---------------------------------------------------------------------
CREATE TABLE notificaciones_enviadas (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    tipo VARCHAR(30) NOT NULL CHECK (tipo IN ('actualizacion_servicio','cupon_fidelizacion','recordatorio_cita')),
    referencia_tipo VARCHAR(30),
    referencia_id INTEGER,
    estado_envio VARCHAR(20) NOT NULL DEFAULT 'enviado' CHECK (estado_envio IN ('enviado','fallido')),
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notificaciones_cliente_id ON notificaciones_enviadas(cliente_id);
