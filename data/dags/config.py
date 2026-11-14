"""Registro de dominios del pipeline ELT (feature 012).

Cada dominio es UNA consulta SQL de solo lectura sobre PostgreSQL, ya
denormalizada al grano de su tabla de hechos/dimensión destino — sin una capa
de "staging" intermedia por tabla de origen: el propio SELECT hace el join que
en un modelo más grande viviría en una fase `transform` separada (Ppio VII,
"Simplicidad Justificada" — el volumen del negocio no lo exige).

Añadir un dominio nuevo (feature futura) = agregar una entrada aquí con su SQL,
su tabla ClickHouse destino y su modo. Nada más se toca (FR-018,
`CONVENCIONES.md` "cómo añadir un dominio nuevo").

Modos:
  - "incremental": la consulta lleva `%(watermark)s` y solo trae filas con
    `updated_at > watermark`. Requiere que el origen tenga una columna de
    actualización fiable (propia o heredada de la tabla padre).
  - "full": la tabla de origen no tiene una columna de actualización que sirva
    de watermark (p. ej. `stock_pieza`, `cuenta_por_cobrar` — su saldo cambia
    sin tocar `creado_en`) o es tan pequeña que no vale la pena la
    complejidad. Se reextrae completa cada corrida; el destino sigue siendo
    idempotente porque es `ReplacingMergeTree` y la nueva versión (`updated_at
    = now()` de la corrida) siempre gana.

Toda consulta proyecta una columna `updated_at` — es lo único que `extract.py`
necesita para (a) fijar el nuevo watermark y (b) versionar la fila en
ClickHouse. `tabla_destino` debe existir ya en `warehouse/ddl/`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dominio:
    nombre: str
    modo: str  # "incremental" | "full"
    tabla_destino: str  # "<db>.<tabla>" en ClickHouse
    sql: str
    pk_cols: tuple[str, ...]  # columnas que identifican la fila (para logs/tests)
    grupo: str = "hechos"  # "hechos" | "dimensiones" — solo para agrupar en la UI de Airflow


_WATERMARK_INICIAL = "1970-01-01T00:00:00+00:00"


def _sql(texto: str) -> str:
    return " ".join(line.strip() for line in texto.strip().splitlines())


DOMINIOS: dict[str, Dominio] = {
    d.nombre: d
    for d in [
        # ---------------------------------------------------------- dimensiones
        Dominio(
            "dim_sucursal", "incremental", "wh.dim_sucursal",
            _sql("""
                SELECT id AS sucursal_id, nombre, estado, actualizado_en AS updated_at
                FROM sucursal
                WHERE actualizado_en > %(watermark)s
                ORDER BY actualizado_en
            """),
            ("sucursal_id",), grupo="dimensiones",
        ),
        Dominio(
            "dim_marca", "full", "wh.dim_marca",
            _sql("""
                SELECT nombre AS marca, pais, (CASE WHEN activo THEN 1 ELSE 0 END) AS activo, now() AS updated_at
                FROM marca_reloj
            """),
            ("marca",), grupo="dimensiones",
        ),
        Dominio(
            "dim_modelo", "full", "wh.dim_modelo",
            _sql("""
                SELECT DISTINCT r.marca, r.referencia, c.codigo AS calibre_codigo, now() AS updated_at
                FROM reloj r
                LEFT JOIN calibre c ON c.id = r.calibre_id
            """),
            ("marca", "referencia"), grupo="dimensiones",
        ),
        Dominio(
            "dim_tecnico", "incremental", "wh.dim_tecnico",
            _sql("""
                SELECT t.id AS tecnico_id, t.nombre,
                       COALESCE(string_agg(e.nombre, ', '), '') AS especialidades,
                       t.estado, t.actualizado_en AS updated_at
                FROM tecnico t
                LEFT JOIN tecnico_especialidad te ON te.tecnico_id = t.id
                LEFT JOIN especialidad e ON e.id = te.especialidad_id
                WHERE t.actualizado_en > %(watermark)s
                GROUP BY t.id, t.nombre, t.estado, t.actualizado_en
                ORDER BY t.actualizado_en
            """),
            ("tecnico_id",), grupo="dimensiones",
        ),
        Dominio(
            "dim_cliente", "incremental", "wh.dim_cliente",
            _sql("""
                SELECT id AS cliente_id, numero_afiliado, tipo, nombre,
                       nivel_fidelizacion_id, estado, actualizado_en AS updated_at
                FROM cliente
                WHERE actualizado_en > %(watermark)s
                ORDER BY actualizado_en
            """),
            ("cliente_id",), grupo="dimensiones",
        ),
        Dominio(
            "dim_nivel", "full", "wh.dim_nivel",
            _sql("""
                SELECT id AS nivel_id, nombre, orden,
                       (CASE WHEN activo THEN 1 ELSE 0 END) AS activo, now() AS updated_at
                FROM nivel_fidelizacion
            """),
            ("nivel_id",), grupo="dimensiones",
        ),
        Dominio(
            "dim_proveedor", "incremental", "wh.dim_proveedor",
            _sql("""
                SELECT p.id AS proveedor_id, p.razon_social,
                       COALESCE(string_agg(pt.tipo, ', '), '') AS tipos,
                       p.estado, p.actualizado_en AS updated_at
                FROM proveedor p
                LEFT JOIN proveedor_tipo pt ON pt.proveedor_id = p.id
                WHERE p.actualizado_en > %(watermark)s
                GROUP BY p.id, p.razon_social, p.estado, p.actualizado_en
                ORDER BY p.actualizado_en
            """),
            ("proveedor_id",), grupo="dimensiones",
        ),
        # -------------------------------------------------------------- hechos
        Dominio(
            "ventas", "incremental", "wh.fact_venta",
            _sql("""
                SELECT lv.id AS linea_venta_id, ov.id AS orden_venta_id, ov.numero,
                       ov.fecha::date AS fecha, ov.sucursal_id, ov.cliente_id,
                       ov.vendedor_usuario_id, lv.item_tipo, lv.reloj_id, r.marca, r.referencia,
                       c.codigo AS calibre_codigo, lv.cantidad, lv.precio_lista,
                       lv.precio_final, lv.costo, lv.margen, ov.estado,
                       ov.actualizado_en AS updated_at
                FROM linea_venta lv
                JOIN orden_venta ov ON ov.id = lv.orden_venta_id
                LEFT JOIN reloj r ON r.id = lv.reloj_id
                LEFT JOIN calibre c ON c.id = r.calibre_id
                WHERE ov.actualizado_en > %(watermark)s
                ORDER BY ov.actualizado_en
            """),
            ("linea_venta_id",),
        ),
        Dominio(
            "ordenes_trabajo", "incremental", "wh.fact_orden_trabajo",
            _sql("""
                SELECT ot.id AS orden_trabajo_id, ot.numero, ot.fecha_ingreso::date AS fecha_ingreso,
                       ot.fecha_real_entrega::date AS fecha_real_entrega, ot.sucursal_id,
                       ot.tecnico_id, ot.cliente_id, ot.tipo_reparacion, ot.horas_trabajadas,
                       ot.costo_interno, ot.precio_cobrado, ot.margen_real, ot.estado,
                       ot.reproceso, ot.actualizado_en AS updated_at
                FROM orden_trabajo ot
                WHERE ot.actualizado_en > %(watermark)s
                ORDER BY ot.actualizado_en
            """),
            ("orden_trabajo_id",),
        ),
        Dominio(
            "piezas_uso", "incremental", "wh.fact_pieza_uso",
            _sql("""
                SELECT puo.id AS pieza_usada_ot_id, puo.orden_trabajo_id, puo.pieza_id,
                       p.codigo, p.descripcion, puo.tipo_elegido, puo.cantidad, puo.costo,
                       ot.sucursal_id, puo.creado_en::date AS fecha, puo.creado_en AS updated_at
                FROM pieza_usada_ot puo
                JOIN pieza p ON p.id = puo.pieza_id
                JOIN orden_trabajo ot ON ot.id = puo.orden_trabajo_id
                WHERE puo.creado_en > %(watermark)s
                ORDER BY puo.creado_en
            """),
            ("pieza_usada_ot_id",),
        ),
        Dominio(
            "lubricacion", "incremental", "wh.fact_lubricacion",
            _sql("""
                SELECT r.id AS registro_id, r.orden_trabajo_id, r.tecnico_id, r.punto_nombre,
                       r.producto_recomendado_id, r.producto_usado_id, r.desviacion,
                       r.fecha::date AS fecha, r.fecha AS updated_at
                FROM registro_lubricacion_ot r
                WHERE r.fecha > %(watermark)s
                ORDER BY r.fecha
            """),
            ("registro_id",),
        ),
        Dominio(
            "movimientos_inventario", "incremental", "wh.fact_movimiento_inventario",
            _sql("""
                SELECT * FROM (
                  SELECT es.id AS movimiento_id, 'reloj' AS tipo_bien, es.reloj_id AS bien_id,
                         r.sucursal_actual_id AS sucursal_id, es.tipo AS tipo_movimiento,
                         1 AS cantidad, es.creado_en::date AS fecha, es.creado_en AS updated_at
                  FROM evento_serie es
                  LEFT JOIN reloj r ON r.id = es.reloj_id
                  WHERE es.reloj_id IS NOT NULL AND es.creado_en > %(watermark)s
                  UNION ALL
                  SELECT ms.id AS movimiento_id, 'pieza' AS tipo_bien, ms.pieza_id AS bien_id,
                         ms.sucursal_id, ms.tipo AS tipo_movimiento, ms.cantidad,
                         ms.creado_en::date AS fecha, ms.creado_en AS updated_at
                  FROM movimiento_stock_pieza ms
                  WHERE ms.creado_en > %(watermark)s
                ) t
                ORDER BY updated_at
            """),
            ("tipo_bien", "movimiento_id"),
        ),
        Dominio(
            "citas", "incremental", "wh.fact_cita",
            _sql("""
                SELECT c.id AS cita_id, c.sucursal_id, c.cliente_id, c.canal_cita_id,
                       c.motivo, c.estado, c.fecha_preferida, c.fecha_confirmada,
                       c.venta_id, c.orden_trabajo_id, c.actualizado_en AS updated_at
                FROM cita c
                WHERE c.actualizado_en > %(watermark)s
                ORDER BY c.actualizado_en
            """),
            ("cita_id",),
        ),
        Dominio(
            "mermas", "incremental", "wh.fact_merma",
            _sql("""
                SELECT m.id AS merma_id, m.sucursal_id, m.bien_tipo, m.causa,
                       m.categoria_merma_id, m.costo_perdida, m.estado,
                       m.fecha_evento::date AS fecha_evento, m.tecnico_id,
                       m.orden_trabajo_id, m.actualizado_en AS updated_at
                FROM merma m
                WHERE m.actualizado_en > %(watermark)s
                ORDER BY m.actualizado_en
            """),
            ("merma_id",),
        ),
        Dominio(
            "contabilidad", "incremental", "wh.fact_asiento",
            _sql("""
                SELECT la.id AS linea_asiento_id, la.asiento_id, cc.codigo AS cuenta_codigo,
                       cc.nombre AS cuenta_nombre, cc.tipo AS cuenta_tipo, la.debe, la.haber,
                       a.fecha::date AS fecha, a.origen, a.creado_en AS updated_at
                FROM linea_asiento la
                JOIN asiento a ON a.id = la.asiento_id
                JOIN cuenta_contable cc ON cc.id = la.cuenta_contable_id
                WHERE a.creado_en > %(watermark)s
                ORDER BY a.creado_en
            """),
            ("linea_asiento_id",),
        ),
        Dominio(
            "gastos", "incremental", "wh.fact_gasto",
            _sql("""
                SELECT g.id AS gasto_id, g.sucursal_id, g.categoria_gasto_id,
                       cg.nombre AS categoria_nombre, g.monto, g.fecha::date AS fecha,
                       g.estado, g.creado_en AS updated_at
                FROM gasto g
                JOIN categoria_gasto cg ON cg.id = g.categoria_gasto_id
                WHERE g.creado_en > %(watermark)s
                ORDER BY g.creado_en
            """),
            ("gasto_id",),
        ),
        Dominio(
            "cxc_cxp", "full", "wh.fact_cxc_cxp",
            _sql("""
                SELECT cxc.id AS id, 'cxc' AS tipo, cxc.origen_tipo, ov.sucursal_id,
                       cxc.monto_original, cxc.saldo, cxc.estado,
                       cxc.creado_en::date AS fecha, now() AS updated_at
                FROM cuenta_por_cobrar cxc
                LEFT JOIN orden_venta ov ON cxc.origen_tipo = 'venta' AND ov.id = cxc.origen_id
                UNION ALL
                SELECT cxp.id AS id, 'cxp' AS tipo, cxp.origen_tipo,
                       COALESCE(oc.sucursal_destino_id, g.sucursal_id) AS sucursal_id,
                       cxp.monto_original, cxp.saldo, cxp.estado,
                       cxp.creado_en::date AS fecha, now() AS updated_at
                FROM cuenta_por_pagar cxp
                LEFT JOIN orden_compra oc ON cxp.origen_tipo = 'orden_compra' AND oc.id = cxp.orden_compra_id
                LEFT JOIN gasto g ON cxp.origen_tipo = 'gasto' AND g.id = cxp.gasto_id
            """),
            ("tipo", "id"),
        ),
        Dominio(
            "bonos", "incremental", "wh.fact_bono",
            _sql("""
                SELECT ba.id AS bono_acumulado_id, ba.tecnico_id, ba.periodo_liquidacion_id,
                       pl.fecha_inicio::date AS fecha_inicio, pl.fecha_fin::date AS fecha_fin,
                       ba.valor_total, ba.estado, ba.calculado_en AS updated_at
                FROM bono_acumulado ba
                JOIN periodo_liquidacion pl ON pl.id = ba.periodo_liquidacion_id
                WHERE ba.calculado_en > %(watermark)s
                ORDER BY ba.calculado_en
            """),
            ("bono_acumulado_id",),
        ),
        Dominio(
            "fidelizacion", "incremental", "wh.fact_fidelizacion",
            _sql("""
                SELECT ad.id AS aplicacion_descuento_id, ad.documento_tipo, ad.origen,
                       ad.precio_lista, ad.precio_final, ad.margen_resultante,
                       ad.creado_en::date AS fecha, ad.creado_en AS updated_at
                FROM aplicacion_descuento ad
                WHERE ad.creado_en > %(watermark)s
                ORDER BY ad.creado_en
            """),
            ("aplicacion_descuento_id",),
        ),
        Dominio(
            "inventario_actual", "full", "wh.fact_inventario_actual",
            _sql("""
                SELECT 'reloj' AS tipo_bien, r.id AS bien_id, r.marca, r.referencia,
                       NULL AS codigo, r.sucursal_actual_id AS sucursal_id,
                       r.costo_adquisicion AS costo, r.precio_venta, r.disponibilidad,
                       1 AS cantidad, r.fecha_ingreso, now() AS updated_at
                FROM reloj r
                WHERE r.sucursal_actual_id IS NOT NULL
                UNION ALL
                SELECT 'pieza' AS tipo_bien, sp.pieza_id AS bien_id, NULL AS marca,
                       NULL AS referencia, p.codigo, sp.sucursal_id,
                       p.costo_adquisicion AS costo, p.precio_venta_suelta AS precio_venta,
                       (CASE WHEN sp.stock_actual > 0 THEN 'disponible' ELSE 'agotado' END) AS disponibilidad,
                       sp.stock_actual AS cantidad, NULL AS fecha_ingreso, now() AS updated_at
                FROM stock_pieza sp
                JOIN pieza p ON p.id = sp.pieza_id
            """),
            ("tipo_bien", "bien_id", "sucursal_id"),
        ),
        Dominio(
            "proveedor_compra", "incremental", "wh.fact_proveedor_compra",
            _sql("""
                SELECT rl.id AS recepcion_linea_id, oc.proveedor_id, loc.pieza_id,
                       loc.item_tipo, rc.fecha_real::date AS fecha_real,
                       rl.cantidad_recibida, rc.creado_en AS updated_at
                FROM recepcion_linea rl
                JOIN recepcion_compra rc ON rc.id = rl.recepcion_compra_id
                JOIN linea_orden_compra loc ON loc.id = rl.linea_orden_compra_id
                JOIN orden_compra oc ON oc.id = rc.orden_compra_id
                WHERE rc.creado_en > %(watermark)s
                ORDER BY rc.creado_en
            """),
            ("recepcion_linea_id",),
        ),
    ]
}


def frecuencia_default() -> str:
    """`schedule_interval` del DAG — variable de Airflow `elt_frecuencia` si existe,
    si no la de entorno `ELT_FRECUENCIA`, si no `@hourly` (Spec §FR-017)."""
    try:
        from airflow.models import Variable

        return Variable.get("elt_frecuencia", default_var=os.environ.get("ELT_FRECUENCIA", "@hourly"))
    except Exception:  # entorno sin Airflow (tests unitarios de data/lib) -> fallback directo
        return os.environ.get("ELT_FRECUENCIA", "@hourly")


WATERMARK_INICIAL = _WATERMARK_INICIAL
