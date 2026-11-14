-- Bases de datos del warehouse (feature 012).
-- `wh`  = dimensiones, hechos y vistas de reporte (§4.11.2).
-- `ctl` = control del pipeline (watermark, corridas, frescura) — leído por
--         GET /reportes/estado-frescura y por el propio DAG.
CREATE DATABASE IF NOT EXISTS wh;
CREATE DATABASE IF NOT EXISTS ctl;
