-- Control del pipeline ELT (data-model.md "Control del pipeline").

-- (dominio, tabla) -> último valor de updated_at extraído con éxito. La extracción
-- del próximo run pide `updated_at > ultimo_valor`. Dominios "full" (sin updated_at
-- utilizable) no usan watermark — extract.py los reprocesa enteros cada corrida.
CREATE TABLE IF NOT EXISTS ctl.pipeline_watermark
(
    dominio      String,
    tabla        String,
    ultimo_valor DateTime64(6),
    ultimo_run_id String,
    actualizado_en DateTime64(6) DEFAULT now64(6)
)
ENGINE = ReplacingMergeTree(actualizado_en)
ORDER BY (dominio, tabla);

-- Un registro por (run_id, dominio, fase): Extract / Load raw / Load warehouse /
-- Transform observables por separado (FR-005, checklist DP008/DP009).
CREATE TABLE IF NOT EXISTS ctl.pipeline_corrida
(
    run_id  String,
    dominio String,
    fase    Enum8('extract' = 1, 'load_raw' = 2, 'load_wh' = 3, 'transform' = 4),
    inicio  DateTime64(6),
    fin     Nullable(DateTime64(6)),
    estado  Enum8('ok' = 1, 'error' = 2, 'en_curso' = 3),
    filas   UInt64 DEFAULT 0,
    detalle_error String DEFAULT ''
)
ENGINE = ReplacingMergeTree(inicio)
ORDER BY (dominio, fase, run_id);

-- Estado de frescura por dominio — lo que expone GET /reportes/estado-frescura.
-- distingue "cargado ok" / "error" / "sin_datos" (checklist DP010).
CREATE TABLE IF NOT EXISTS ctl.pipeline_frescura
(
    dominio               String,
    ultima_carga_ts       DateTime64(6),
    max_updated_at_origen Nullable(DateTime64(6)),
    ultimo_run_id         String,
    estado_ultima_corrida Enum8('ok' = 1, 'error' = 2, 'sin_datos' = 3)
)
ENGINE = ReplacingMergeTree(ultima_carga_ts)
ORDER BY dominio;
