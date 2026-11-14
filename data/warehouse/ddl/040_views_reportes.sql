-- Los 18 modelos de reporte de §4.11.2 (data-model.md "Warehouse — Modelos de
-- reporte"), como VISTAS planas sobre los hechos/dimensiones ya cargados —no
-- MATERIALIZED VIEW: a este volumen de negocio (Ppio VII, "decenas de miles de
-- filas") una vista calculada al vuelo ya cumple el objetivo de rendimiento
-- del plan (<3 s por consulta) y es bastante más simple de mantener. Es una
-- simplificación deliberada dentro de lo que `data-model.md` ya dejaba abierto
-- ("vista o MATERIALIZED VIEW").
--
-- Todas leen los hechos con FINAL para resolver la versión vigente de cada
-- fila (ReplacingMergeTree) y filtran los estados anulados/cancelados donde
-- aplica (FR-013). 013 filtra por periodo/sucursal/marca/técnico agregando un
-- WHERE sobre las columnas ya expuestas (FR-009) — estas vistas no imponen
-- rango de fechas por sí solas.

-- 1. Mejores clientes (por volumen de compra + servicios)
CREATE VIEW IF NOT EXISTS wh.mejores_clientes AS
SELECT
    cliente_id,
    toStartOfMonth(fecha) AS periodo,
    sum(linea_monto_ventas) AS monto_ventas,
    sum(linea_monto_servicios) AS monto_servicios,
    sum(linea_monto_ventas) + sum(linea_monto_servicios) AS monto_total
FROM (
    SELECT cliente_id, fecha, precio_final AS linea_monto_ventas, toDecimal64(0, 2) AS linea_monto_servicios
    FROM wh.fact_venta FINAL
    WHERE estado = 'confirmada' AND cliente_id IS NOT NULL
    UNION ALL
    SELECT cliente_id, fecha_ingreso AS fecha, toDecimal64(0, 2) AS linea_monto_ventas, coalesce(precio_cobrado, toDecimal64(0, 2)) AS linea_monto_servicios
    FROM wh.fact_orden_trabajo FINAL
    WHERE estado = 'entregado'
)
GROUP BY cliente_id, periodo;

-- 2. Margen por reloj vendido (costo vs. precio de venta)
CREATE VIEW IF NOT EXISTS wh.margen_por_reloj_vendido AS
SELECT
    linea_venta_id, orden_venta_id, numero, fecha, sucursal_id, cliente_id,
    reloj_id, marca, referencia, calibre_codigo,
    precio_lista, precio_final, costo, margen,
    (margen / nullIf(precio_final, 0)) AS margen_pct
FROM wh.fact_venta FINAL
WHERE item_tipo = 'reloj' AND estado = 'confirmada';

-- 3. Margen por servicio / orden de trabajo
CREATE VIEW IF NOT EXISTS wh.margen_por_servicio AS
SELECT
    orden_trabajo_id, numero, fecha_ingreso, fecha_real_entrega, sucursal_id,
    tecnico_id, cliente_id, tipo_reparacion, costo_interno, precio_cobrado, margen_real,
    (margen_real / nullIf(precio_cobrado, 0)) AS margen_pct
FROM wh.fact_orden_trabajo FINAL
WHERE estado = 'entregado';

-- 4. Margen por marca y por modelo
CREATE VIEW IF NOT EXISTS wh.margen_por_marca_modelo AS
SELECT
    marca, referencia, calibre_codigo, sucursal_id,
    toStartOfMonth(fecha) AS periodo,
    count() AS unidades_vendidas,
    sum(precio_final) AS ingresos,
    sum(costo) AS costo_total,
    sum(margen) AS margen_total,
    (sum(margen) / nullIf(sum(precio_final), 0)) AS margen_pct
FROM wh.fact_venta FINAL
WHERE item_tipo = 'reloj' AND estado = 'confirmada'
GROUP BY marca, referencia, calibre_codigo, sucursal_id, periodo;

-- 5. Rotación de stock (días promedio en inventario antes de venderse)
CREATE VIEW IF NOT EXISTS wh.rotacion_stock AS
SELECT
    fv.marca AS marca, fv.referencia AS referencia, fv.sucursal_id AS sucursal_id,
    toStartOfMonth(fv.fecha) AS periodo,
    avg(dateDiff('day', fi.fecha_ingreso, fv.fecha)) AS dias_promedio_rotacion,
    count() AS unidades
FROM wh.fact_venta fv FINAL
LEFT JOIN (
    SELECT bien_id, fecha_ingreso FROM wh.fact_inventario_actual FINAL WHERE tipo_bien = 'reloj'
) fi ON fi.bien_id = fv.reloj_id
WHERE fv.item_tipo = 'reloj' AND fv.estado = 'confirmada' AND fi.fecha_ingreso IS NOT NULL
GROUP BY fv.marca, fv.referencia, fv.sucursal_id, periodo;

-- 6. Piezas más usadas y su costo
CREATE VIEW IF NOT EXISTS wh.piezas_mas_usadas AS
SELECT
    pieza_id, codigo, descripcion, sucursal_id,
    toStartOfMonth(fecha) AS periodo,
    sum(cantidad) AS cantidad_usada,
    sum(costo) AS costo_total
FROM wh.fact_pieza_uso FINAL
GROUP BY pieza_id, codigo, descripcion, sucursal_id, periodo;

-- 7. Productividad por técnico (órdenes, tiempos, margen, bonos)
CREATE VIEW IF NOT EXISTS wh.productividad_tecnico AS
SELECT
    ot.tecnico_id AS tecnico_id,
    any(dt.nombre) AS tecnico_nombre,
    ot.sucursal_id AS sucursal_id,
    toStartOfMonth(ot.fecha_ingreso) AS periodo,
    count() AS ordenes_completadas,
    avg(dateDiff('day', ot.fecha_ingreso, ot.fecha_real_entrega)) AS dias_promedio_servicio,
    sum(ot.margen_real) AS margen_generado,
    any(b.bonos_totales) AS bonos_totales_historico
FROM wh.fact_orden_trabajo ot FINAL
LEFT JOIN wh.dim_tecnico dt FINAL ON dt.tecnico_id = ot.tecnico_id
LEFT JOIN (
    SELECT tecnico_id, sum(valor_total) AS bonos_totales
    FROM wh.fact_bono FINAL
    WHERE estado != 'preliminar'
    GROUP BY tecnico_id
) b ON b.tecnico_id = ot.tecnico_id
WHERE ot.estado = 'entregado' AND ot.tecnico_id IS NOT NULL
GROUP BY ot.tecnico_id, ot.sucursal_id, periodo;

-- 8. Valor total del inventario (relojes + piezas, a costo y a precio de venta)
CREATE VIEW IF NOT EXISTS wh.valor_total_inventario AS
SELECT
    sucursal_id, tipo_bien,
    sum(cantidad) AS unidades,
    sum(cantidad * coalesce(costo, 0)) AS valor_a_costo,
    sum(cantidad * coalesce(precio_venta, 0)) AS valor_a_precio_venta
FROM wh.fact_inventario_actual FINAL
WHERE disponibilidad IN ('disponible', 'reservado')
GROUP BY sucursal_id, tipo_bien;

-- 9. Comparativo costo vs. precio de venta (global y segmentado)
CREATE VIEW IF NOT EXISTS wh.comparativo_costo_precio AS
SELECT
    marca, referencia, sucursal_id, toStartOfMonth(fecha) AS periodo,
    sum(costo) AS costo_total, sum(precio_final) AS precio_total,
    (sum(precio_final) - sum(costo)) AS diferencia,
    ((sum(precio_final) - sum(costo)) / nullIf(sum(costo), 0)) AS diferencia_pct
FROM wh.fact_venta FINAL
WHERE estado = 'confirmada'
GROUP BY marca, referencia, sucursal_id, periodo;

-- 10. Tiempo medio de servicio (desde ingreso hasta entrega)
CREATE VIEW IF NOT EXISTS wh.tiempo_medio_servicio AS
SELECT
    sucursal_id, tipo_reparacion, toStartOfMonth(fecha_ingreso) AS periodo,
    avg(dateDiff('day', fecha_ingreso, fecha_real_entrega)) AS dias_promedio,
    count() AS ordenes
FROM wh.fact_orden_trabajo FINAL
WHERE estado = 'entregado' AND fecha_real_entrega IS NOT NULL
GROUP BY sucursal_id, tipo_reparacion, periodo;

-- 11. Tasa de reposición de piezas (frecuencia de recompra a proveedores)
CREATE VIEW IF NOT EXISTS wh.tasa_reposicion_piezas AS
SELECT
    pieza_id, proveedor_id, toStartOfMonth(fecha_real) AS periodo,
    count() AS compras, sum(cantidad_recibida) AS unidades_recibidas
FROM wh.fact_proveedor_compra FINAL
WHERE item_tipo = 'pieza' AND pieza_id IS NOT NULL
GROUP BY pieza_id, proveedor_id, periodo;

-- 12. Rentabilidad neta por sucursal (margen ventas + servicio − gastos operativos)
CREATE VIEW IF NOT EXISTS wh.rentabilidad_neta_sucursal AS
SELECT
    sucursal_id, periodo,
    sum(linea_margen_ventas) AS margen_ventas,
    sum(linea_margen_servicios) AS margen_servicios,
    sum(linea_gastos) AS gastos,
    (sum(linea_margen_ventas) + sum(linea_margen_servicios) - sum(linea_gastos)) AS rentabilidad_neta
FROM (
    SELECT sucursal_id, toStartOfMonth(fecha) AS periodo, sum(margen) AS linea_margen_ventas,
           toDecimal64(0, 2) AS linea_margen_servicios, toDecimal64(0, 2) AS linea_gastos
    FROM wh.fact_venta FINAL WHERE estado = 'confirmada' GROUP BY sucursal_id, periodo
    UNION ALL
    SELECT sucursal_id, toStartOfMonth(fecha_ingreso) AS periodo, toDecimal64(0, 2),
           sum(margen_real), toDecimal64(0, 2)
    FROM wh.fact_orden_trabajo FINAL WHERE estado = 'entregado' GROUP BY sucursal_id, periodo
    UNION ALL
    SELECT sucursal_id, toStartOfMonth(fecha) AS periodo, toDecimal64(0, 2), toDecimal64(0, 2), sum(monto)
    FROM wh.fact_gasto FINAL WHERE estado != 'anulado' GROUP BY sucursal_id, periodo
)
GROUP BY sucursal_id, periodo;

-- 13. Tasa de conversión de citas a venta/servicio
CREATE VIEW IF NOT EXISTS wh.conversion_citas AS
SELECT
    sucursal_id, motivo, toStartOfMonth(fecha_preferida) AS periodo,
    count() AS total_citas,
    countIf(estado = 'atendida') AS atendidas,
    countIf(venta_id IS NOT NULL OR orden_trabajo_id IS NOT NULL) AS con_transaccion,
    (countIf(venta_id IS NOT NULL OR orden_trabajo_id IS NOT NULL) / nullIf(count(), 0)) AS tasa_conversion
FROM wh.fact_cita FINAL
GROUP BY sucursal_id, motivo, periodo;

-- 14. Desviación de lubricación (recomendado vs. usado)
CREATE VIEW IF NOT EXISTS wh.desviacion_lubricacion AS
SELECT
    tecnico_id, punto_nombre, toStartOfMonth(fecha) AS periodo,
    count() AS registros,
    countIf(desviacion = 1) AS con_desviacion,
    (countIf(desviacion = 1) / nullIf(count(), 0)) AS tasa_desviacion
FROM wh.fact_lubricacion FINAL
GROUP BY tecnico_id, punto_nombre, periodo;

-- 15. Antigüedad de cuentas por cobrar/pagar (aging)
CREATE VIEW IF NOT EXISTS wh.aging_cxc_cxp AS
SELECT
    tipo, sucursal_id, id, origen_tipo, monto_original, saldo, estado, fecha,
    dateDiff('day', fecha, today()) AS dias_antiguedad,
    multiIf(
        dateDiff('day', fecha, today()) <= 30, '0-30',
        dateDiff('day', fecha, today()) <= 60, '31-60',
        dateDiff('day', fecha, today()) <= 90, '61-90',
        '+90'
    ) AS tramo
FROM wh.fact_cxc_cxp FINAL
WHERE estado != 'pagada' AND saldo > 0;

-- 16. Efectividad de fidelización y descuentos
CREATE VIEW IF NOT EXISTS wh.efectividad_fidelizacion_descuentos AS
SELECT
    origen, toStartOfMonth(fecha) AS periodo,
    count() AS aplicaciones,
    sum(precio_lista - precio_final) AS costo_beneficio,
    sum(precio_final) AS ventas_generadas
FROM wh.fact_fidelizacion FINAL
GROUP BY origen, periodo;

-- 17. Clientes por nivel de fidelización
CREATE VIEW IF NOT EXISTS wh.clientes_por_nivel AS
SELECT
    dn.nivel_id AS nivel_id, dn.nombre AS nivel_nombre, dn.orden AS orden,
    count() AS clientes
FROM wh.dim_cliente AS dc FINAL
LEFT JOIN wh.dim_nivel AS dn FINAL ON dn.nivel_id = dc.nivel_fidelizacion_id
WHERE dc.estado = 'activo'
GROUP BY dn.nivel_id, dn.nombre, dn.orden;

-- 18. Mermas y pérdidas (monto, causa y frecuencia)
CREATE VIEW IF NOT EXISTS wh.mermas_perdidas AS
SELECT
    sucursal_id, causa, estado, toStartOfMonth(fecha_evento) AS periodo,
    count() AS eventos, sum(costo_perdida) AS monto_total
FROM wh.fact_merma FINAL
GROUP BY sucursal_id, causa, estado, periodo;
