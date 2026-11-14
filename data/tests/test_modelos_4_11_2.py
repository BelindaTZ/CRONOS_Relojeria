"""T027 (US6): cada uno de los 18 modelos de reporte de §4.11.2 existe y es
consultable (no valida cifras — eso depende de qué datos operativos tenga el
entorno en el momento del test, solo que la vista no rompe)."""
from __future__ import annotations

import pytest

_MODELOS = [
    "mejores_clientes",
    "margen_por_reloj_vendido",
    "margen_por_servicio",
    "margen_por_marca_modelo",
    "rotacion_stock",
    "piezas_mas_usadas",
    "productividad_tecnico",
    "valor_total_inventario",
    "comparativo_costo_precio",
    "tiempo_medio_servicio",
    "tasa_reposicion_piezas",
    "rentabilidad_neta_sucursal",
    "conversion_citas",
    "desviacion_lubricacion",
    "aging_cxc_cxp",
    "efectividad_fidelizacion_descuentos",
    "clientes_por_nivel",
    "mermas_perdidas",
]


@pytest.mark.parametrize("modelo", _MODELOS)
def test_modelo_existe_y_es_consultable(ch, modelo):
    resultado = ch.query(f"SELECT count() FROM wh.{modelo}")
    assert resultado.result_rows[0][0] >= 0


def test_son_exactamente_18_modelos():
    assert len(_MODELOS) == 18
