-- Hechos (data-model.md "Warehouse — Hechos", `ReplacingMergeTree` por clave +
-- `updated_at`). Las consultas de las vistas de reporte (040_views_reportes.sql)
-- leen siempre con `FINAL` para resolver la versión vigente de cada fila —
-- volumen pequeño (Ppio VII), el costo de FINAL es despreciable aquí.
--
-- Dos hechos (`fact_gasto`, `fact_proveedor_compra`) no estaban en la lista original
-- de `data-model.md` — se agregaron porque, al construir las vistas, `fact_asiento`
-- no alcanza (el mayor no tiene `sucursal_id`, por diseño — ver CONVENCIONES §21) y
-- `tasa_reposicion_piezas` necesita el historial de recepciones por proveedor. La
-- Constitución permite explícitamente ampliar el modelo cuando hace falta.

CREATE TABLE IF NOT EXISTS wh.fact_venta
(
    linea_venta_id  UInt64,
    orden_venta_id  UInt64,
    numero          String,
    fecha           Date,
    sucursal_id     UInt64,
    cliente_id      Nullable(UInt64),
    vendedor_usuario_id Nullable(UInt64),
    item_tipo       String,
    reloj_id        Nullable(UInt64),
    marca           Nullable(String),
    referencia      Nullable(String),
    calibre_codigo  Nullable(String),
    cantidad        UInt32,
    precio_lista    Decimal64(2),
    precio_final    Decimal64(2),
    costo           Decimal64(2),
    margen          Decimal64(2),
    estado          String,   -- borrador | confirmada | anulada
    updated_at      DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY linea_venta_id;

CREATE TABLE IF NOT EXISTS wh.fact_orden_trabajo
(
    orden_trabajo_id   UInt64,
    numero             String,
    fecha_ingreso       Date,
    fecha_real_entrega  Nullable(Date),
    sucursal_id         UInt64,
    tecnico_id          Nullable(UInt64),
    cliente_id          UInt64,
    tipo_reparacion      String,
    horas_trabajadas     Nullable(Decimal64(2)),
    costo_interno        Nullable(Decimal64(2)),
    precio_cobrado       Nullable(Decimal64(2)),
    margen_real          Nullable(Decimal64(2)),
    estado               String,
    reproceso             UInt8,
    updated_at            DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY orden_trabajo_id;

CREATE TABLE IF NOT EXISTS wh.fact_pieza_uso
(
    pieza_usada_ot_id UInt64,
    orden_trabajo_id  UInt64,
    pieza_id          UInt64,
    codigo            String,
    descripcion       String,
    tipo_elegido      String,
    cantidad          UInt32,
    costo             Decimal64(2),
    sucursal_id       UInt64,
    fecha             Date,
    updated_at        DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY pieza_usada_ot_id;

CREATE TABLE IF NOT EXISTS wh.fact_lubricacion
(
    registro_id       UInt64,
    orden_trabajo_id  UInt64,
    tecnico_id        Nullable(UInt64),
    punto_nombre      String,
    producto_recomendado_id Nullable(UInt64),
    producto_usado_id UInt64,
    desviacion        UInt8,
    fecha             Date,
    updated_at        DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY registro_id;

-- Grano: un movimiento (evento_serie de un reloj, o movimiento_stock_pieza de una
-- pieza) — ambos append-only en el origen, se unifican aquí por tipo_bien.
CREATE TABLE IF NOT EXISTS wh.fact_movimiento_inventario
(
    movimiento_id   UInt64,
    tipo_bien       String,  -- reloj | pieza
    bien_id         UInt64,  -- reloj_id o pieza_id
    sucursal_id     Nullable(UInt64),
    tipo_movimiento String,  -- venta | traslado | merma | recepcion | ...
    cantidad        Int32,
    fecha           Date,
    updated_at      DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (tipo_bien, movimiento_id);

CREATE TABLE IF NOT EXISTS wh.fact_cita
(
    cita_id           UInt64,
    sucursal_id       UInt64,
    cliente_id        UInt64,
    canal_cita_id     UInt64,
    motivo            String,
    estado            String,
    fecha_preferida   DateTime64(6),
    fecha_confirmada  Nullable(DateTime64(6)),
    venta_id          Nullable(UInt64),
    orden_trabajo_id  Nullable(UInt64),
    updated_at        DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY cita_id;

CREATE TABLE IF NOT EXISTS wh.fact_merma
(
    merma_id          UInt64,
    sucursal_id       UInt64,
    bien_tipo         String,
    causa             String,
    categoria_merma_id Nullable(UInt64),
    costo_perdida     Decimal64(2),
    estado            String,
    fecha_evento      Date,
    tecnico_id        Nullable(UInt64),
    orden_trabajo_id  Nullable(UInt64),
    updated_at        DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY merma_id;

-- Grano: línea de asiento. Deliberadamente SIN sucursal_id (el mayor no la tiene,
-- por diseño — ver CONVENCIONES §21 "el mayor no tiene sucursal_id"). Rentabilidad
-- por sucursal se resuelve con fact_venta + fact_orden_trabajo + fact_gasto.
CREATE TABLE IF NOT EXISTS wh.fact_asiento
(
    linea_asiento_id UInt64,
    asiento_id       UInt64,
    cuenta_codigo    String,
    cuenta_nombre    String,
    cuenta_tipo      String,
    debe             Decimal64(2),
    haber            Decimal64(2),
    fecha            Date,
    origen           String,
    updated_at       DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY linea_asiento_id;

CREATE TABLE IF NOT EXISTS wh.fact_gasto
(
    gasto_id           UInt64,
    sucursal_id        UInt64,
    categoria_gasto_id UInt64,
    categoria_nombre   String,
    monto              Decimal64(2),
    fecha              Date,
    estado             String,
    updated_at         DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY gasto_id;

-- Snapshot completo (dominio "full", sin watermark — ver research/CONVENCIONES:
-- cuenta_por_cobrar/cuenta_por_pagar no tienen columna de actualización en el
-- origen, su saldo cambia con cada cobro/pago sin tocar `creado_en`).
CREATE TABLE IF NOT EXISTS wh.fact_cxc_cxp
(
    id             UInt64,
    tipo           String,  -- cxc | cxp
    origen_tipo    String,
    sucursal_id    Nullable(UInt64),
    monto_original Decimal64(2),
    saldo          Decimal64(2),
    estado         String,
    fecha          Date,
    updated_at     DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (tipo, id);

CREATE TABLE IF NOT EXISTS wh.fact_bono
(
    bono_acumulado_id     UInt64,
    tecnico_id            UInt64,
    periodo_liquidacion_id UInt64,
    fecha_inicio          Date,
    fecha_fin             Date,
    valor_total           Decimal64(2),
    estado                String,
    updated_at            DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY bono_acumulado_id;

CREATE TABLE IF NOT EXISTS wh.fact_fidelizacion
(
    aplicacion_descuento_id UInt64,
    documento_tipo          String,
    origen                  String,  -- descuento | cupon | nivel
    precio_lista            Decimal64(2),
    precio_final            Decimal64(2),
    margen_resultante       Nullable(Decimal64(4)),
    fecha                   Date,
    updated_at              DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY aplicacion_descuento_id;

-- Snapshot completo (dominio "full" — refleja el stock/estado AHORA, no un
-- histórico incremental; `reloj`/`stock_pieza` no traen una columna de
-- actualización que sirva de watermark fiable para `stock_pieza`).
CREATE TABLE IF NOT EXISTS wh.fact_inventario_actual
(
    tipo_bien      String,  -- reloj | pieza
    bien_id        UInt64,
    marca          Nullable(String),
    referencia     Nullable(String),
    codigo         Nullable(String),
    sucursal_id    UInt64,
    costo          Nullable(Decimal64(2)),
    precio_venta   Nullable(Decimal64(2)),
    disponibilidad String,
    cantidad       UInt32,
    fecha_ingreso  Nullable(Date),
    updated_at     DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (tipo_bien, bien_id, sucursal_id);

CREATE TABLE IF NOT EXISTS wh.fact_proveedor_compra
(
    recepcion_linea_id UInt64,
    proveedor_id       UInt64,
    pieza_id           Nullable(UInt64),
    item_tipo          String,
    fecha_real         Date,
    cantidad_recibida  UInt32,
    updated_at         DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY recepcion_linea_id;
