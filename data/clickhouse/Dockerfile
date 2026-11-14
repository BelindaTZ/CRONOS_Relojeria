# ClickHouse con el DDL del warehouse (feature 012) ya copiado dentro de
# /docker-entrypoint-initdb.d/ — la imagen oficial ejecuta ahí, en orden
# alfabético, cualquier .sql al arrancar por primera vez (sobre un volumen de
# datos vacío). Los nombres 000_/010_/020_/030_/040_ fijan ese orden
# (bases -> control -> dimensiones -> hechos -> vistas de reporte).
FROM clickhouse/clickhouse-server:24.8

COPY warehouse/ddl/*.sql /docker-entrypoint-initdb.d/
COPY clickhouse/config.d/backups.xml /etc/clickhouse-server/config.d/backups.xml
