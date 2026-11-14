-- Dimensiones (data-model.md "Warehouse — Dimensiones"). Todas ReplacingMergeTree
-- por `updated_at` salvo `dim_fecha` (generada, no viene del origen).

CREATE TABLE IF NOT EXISTS wh.dim_fecha
(
    fecha       Date,
    anio        UInt16,
    mes         UInt8,
    semana      UInt8,
    dia_semana  UInt8   -- 1=lunes … 7=domingo (ISO, como toDayOfWeek de ClickHouse)
)
ENGINE = MergeTree
ORDER BY fecha;

CREATE TABLE IF NOT EXISTS wh.dim_sucursal
(
    sucursal_id UInt64,
    nombre      String,
    estado      String,
    updated_at  DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY sucursal_id;

CREATE TABLE IF NOT EXISTS wh.dim_marca
(
    marca      String,
    pais       Nullable(String),
    activo     UInt8,
    updated_at DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY marca;

CREATE TABLE IF NOT EXISTS wh.dim_modelo
(
    marca         String,
    referencia    String,
    calibre_codigo Nullable(String),
    updated_at    DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (marca, referencia);

CREATE TABLE IF NOT EXISTS wh.dim_tecnico
(
    tecnico_id      UInt64,
    nombre          String,
    especialidades  String,   -- CSV, ya resuelto en la extracción
    estado          String,
    updated_at      DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY tecnico_id;

CREATE TABLE IF NOT EXISTS wh.dim_cliente
(
    cliente_id           UInt64,
    numero_afiliado      String,
    tipo                 String,
    nombre               String,
    nivel_fidelizacion_id Nullable(UInt64),
    estado               String,
    updated_at           DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY cliente_id;

CREATE TABLE IF NOT EXISTS wh.dim_nivel
(
    nivel_id   UInt64,
    nombre     String,
    orden      UInt16,
    activo     UInt8,
    updated_at DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY nivel_id;

CREATE TABLE IF NOT EXISTS wh.dim_proveedor
(
    proveedor_id UInt64,
    razon_social String,
    tipos        String,  -- CSV de proveedor_tipo
    estado       String,
    updated_at   DateTime64(6)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY proveedor_id;
