"""Catálogo de los 18 reportes analíticos de §4.11.2 + cliente ClickHouse de
solo lectura (feature 013). Único punto del backend que conoce los nombres de
las vistas de ClickHouse (`wh.*`, sembradas por 012) — `service.py` no arma
SQL a mano fuera de aquí (Ppio X).

Los filtros de cada reporte están fijados por las columnas que su vista de
ClickHouse REALMENTE expone (`data/warehouse/ddl/040_views_reportes.sql`, 012)
— no todos los reportes admiten periodo/sucursal/marca/técnico; algunos son
fotos del estado actual (`valor_total_inventario`, `aging_cxc_cxp`,
`clientes_por_nivel`) y no tienen columna de periodo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.clickhouse import get_client

__all__ = ["get_client", "CATALOGO", "ReporteDef"]


@dataclass(frozen=True)
class ReporteDef:
    slug: str
    titulo: str
    modelo_ch: str
    filtros_soportados: tuple[str, ...]  # subconjunto de {periodo, sucursal, marca, tecnico}
    tipo_grafico: str  # barras | pastel | lineas | kpi | tabla
    col_categoria: str | None = None
    cols_series: tuple[str, ...] = field(default_factory=tuple)


_REPORTES: list[ReporteDef] = [
    ReporteDef("mejores-clientes", "Mejores clientes", "mejores_clientes",
               ("periodo",), "tabla"),
    ReporteDef("margen-por-reloj-vendido", "Margen por reloj vendido", "margen_por_reloj_vendido",
               ("periodo", "sucursal", "marca"), "tabla"),
    ReporteDef("margen-por-servicio", "Margen por servicio / orden de trabajo", "margen_por_servicio",
               ("periodo", "sucursal", "tecnico"), "tabla"),
    ReporteDef("margen-por-marca-modelo", "Margen por marca y modelo", "margen_por_marca_modelo",
               ("periodo", "sucursal", "marca"), "barras",
               col_categoria="referencia", cols_series=("margen_total",)),
    ReporteDef("rotacion-stock", "Rotación de stock", "rotacion_stock",
               ("periodo", "sucursal", "marca"), "lineas",
               col_categoria="periodo", cols_series=("dias_promedio_rotacion",)),
    ReporteDef("piezas-mas-usadas", "Piezas más usadas y su costo", "piezas_mas_usadas",
               ("periodo", "sucursal"), "barras",
               col_categoria="descripcion", cols_series=("cantidad_usada",)),
    # Solo "ordenes_completadas" en el gráfico: "margen_generado" es otra unidad
    # (moneda vs. conteo) — nunca un eje doble (dataviz, "never dual-axis"); el
    # margen se ve en la tabla de detalle, que trae todas las columnas.
    ReporteDef("productividad-tecnico", "Productividad por técnico", "productividad_tecnico",
               ("periodo", "sucursal", "tecnico"), "barras",
               col_categoria="tecnico_nombre", cols_series=("ordenes_completadas",)),
    ReporteDef("valor-total-inventario", "Valor total del inventario", "valor_total_inventario",
               ("sucursal",), "tabla"),
    ReporteDef("comparativo-costo-precio", "Comparativo costo vs. precio de venta", "comparativo_costo_precio",
               ("periodo", "sucursal", "marca"), "barras",
               col_categoria="marca", cols_series=("costo_total", "precio_total")),
    ReporteDef("tiempo-medio-servicio", "Tiempo medio de servicio", "tiempo_medio_servicio",
               ("periodo", "sucursal"), "lineas",
               col_categoria="periodo", cols_series=("dias_promedio",)),
    ReporteDef("tasa-reposicion-piezas", "Tasa de reposición de piezas", "tasa_reposicion_piezas",
               ("periodo",), "lineas",
               col_categoria="periodo", cols_series=("compras",)),
    ReporteDef("rentabilidad-neta-sucursal", "Rentabilidad neta por sucursal", "rentabilidad_neta_sucursal",
               ("periodo", "sucursal"), "barras",
               col_categoria="sucursal_id", cols_series=("rentabilidad_neta",)),
    ReporteDef("conversion-citas", "Tasa de conversión de citas a venta/servicio", "conversion_citas",
               ("periodo", "sucursal"), "lineas",
               col_categoria="periodo", cols_series=("tasa_conversion",)),
    ReporteDef("desviacion-lubricacion", "Desviación de lubricación", "desviacion_lubricacion",
               ("periodo", "tecnico"), "tabla"),
    ReporteDef("aging-cxc-cxp", "Antigüedad de cuentas por cobrar/pagar", "aging_cxc_cxp",
               ("sucursal",), "tabla"),
    ReporteDef("efectividad-fidelizacion-descuentos", "Efectividad de fidelización y descuentos",
               "efectividad_fidelizacion_descuentos", ("periodo",), "barras",
               col_categoria="origen", cols_series=("costo_beneficio", "ventas_generadas")),
    ReporteDef("clientes-por-nivel", "Clientes por nivel de fidelización", "clientes_por_nivel",
               (), "pastel", col_categoria="nivel_nombre", cols_series=("clientes",)),
    ReporteDef("mermas-perdidas", "Mermas y pérdidas", "mermas_perdidas",
               ("periodo", "sucursal"), "pastel",
               col_categoria="causa", cols_series=("monto_total",)),
]

CATALOGO: dict[str, ReporteDef] = {r.slug: r for r in _REPORTES}

assert len(CATALOGO) == 18, "El catálogo debe cubrir los 18 reportes de §4.11.2"
