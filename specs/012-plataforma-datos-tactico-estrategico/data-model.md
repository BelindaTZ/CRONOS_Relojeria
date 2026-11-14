# Data Model: Plataforma de Datos Táctico-Estratégica

**Feature**: `012-plataforma-datos-tactico-estrategico` | **Phase**: 1 | **Date**: 2026-09-10

Este data-model describe el **warehouse de ClickHouse** y los artefactos de control del pipeline. **No modifica el esquema operativo de PostgreSQL** (extracción read-only). Migración Alembic `0029_rol_elt_readonly` crea en PostgreSQL el rol de base de datos de solo lectura `cronos_elt_ro` (con `GRANT SELECT` sobre tablas del esquema `public` y `ALTER DEFAULT PRIVILEGES` para tablas futuras), asegurando la separación estricta de motores (Const. Ppio III).

## Zona de aterrizaje (`landing-zone`, MinIO)

- Objetos `landing-zone/<dominio>/<run_id>/<tabla>.parquet` (o `.ndjson`). Raw sin transformar. **Nunca fuente de negocio**. Retención configurable (por defecto 30 días o últimas N corridas).

## Control del pipeline

| Artefacto | Contenido |
|---|---|
| `pipeline_watermark` | (dominio, tabla) → `ultimo_updated_at`, `ultimo_run_id` |
| `pipeline_corrida` | `run_id`, `dominio`, `fase`, `inicio`, `fin`, `estado` (`ok`/`error`), `filas` |
| `pipeline_frescura` | (dominio) → `ultima_carga_ts`, `max_updated_at_origen`, `ultimo_run_id` |

(Se guardan en la DB de metadata de Airflow o en tablas de ClickHouse `system`-adjacentes; el endpoint `GET /reportes/estado-frescura` las lee.)

## Warehouse — Dimensiones (ClickHouse)

| Tabla | Claves / atributos |
|---|---|
| `dim_fecha` | fecha, anio, mes, semana, dia_semana |
| `dim_sucursal` | sucursal_id, nombre |
| `dim_marca` | marca |
| `dim_modelo` | marca, referencia, calibre |
| `dim_tecnico` | tecnico_id, nombre, especialidades |
| `dim_cliente` | cliente_id, numero_afiliado, tipo |
| `dim_nivel` | nivel_id, nombre, orden |
| `dim_proveedor` | proveedor_id, razon_social, tipos |

## Warehouse — Hechos (ClickHouse, `ReplacingMergeTree` por clave + `updated_at`)

| Tabla | Grano | Métricas |
|---|---|---|
| `fact_venta` | línea de venta | precio_lista, precio_final, costo, margen, estado |
| `fact_orden_trabajo` | OT | costo_mo, costo_piezas, costo_insumos, costo_interno, precio_cobrado, margen_real, horas, dias_servicio, estado |
| `fact_pieza_uso` | pieza usada en OT | cantidad, costo |
| `fact_lubricacion` | registro por punto | recomendado, usado, desviacion (0/1) |
| `fact_movimiento_inventario` | movimiento de reloj/pieza | tipo, cantidad, costo, dias_en_stock |
| `fact_cita` | cita | estado, atendida (0/1), con_transaccion (0/1) |
| `fact_merma` | merma | costo_perdida, causa, estado |
| `fact_asiento` | línea de asiento | cuenta, debe, haber, sucursal |
| `fact_cxc_cxp` | cuenta | tipo, monto_original, saldo, dias_antiguedad |
| `fact_bono` | bono por técnico/periodo | valor_total, por indicador |

## Warehouse — Modelos de reporte (§4.11.2)

Cada reporte de §4.11.2 se materializa (vista o `MATERIALIZED VIEW`) sobre los hechos con las claves de filtro periodo/sucursal/marca/técnico:

1. mejores_clientes · 2. margen_por_reloj_vendido · 3. margen_por_servicio · 4. margen_por_marca_modelo · 5. rotacion_stock · 6. piezas_mas_usadas · 7. productividad_tecnico · 8. valor_total_inventario · 9. comparativo_costo_precio · 10. tiempo_medio_servicio · 11. tasa_reposicion_piezas · 12. rentabilidad_neta_sucursal · 13. conversion_citas · 14. desviacion_lubricacion · 15. aging_cxc_cxp · 16. efectividad_fidelizacion_descuentos · 17. clientes_por_nivel · 18. mermas_perdidas

## Nota — endpoint de estado

- `backend/src/reportes_estado/` expone `GET /reportes/estado-frescura` (solo lectura) y `POST /reportes/actualizar-ahora` (dispara el DAG vía Airflow REST API). Es el único punto de contacto con el backend operativo.
