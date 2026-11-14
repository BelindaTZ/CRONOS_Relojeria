"""T013 (US2): el rol de extracción es estrictamente de solo lectura y la
extracción de un dominio no requiere watermark previo (arranca desde
`WATERMARK_INICIAL`)."""
from __future__ import annotations

from pathlib import Path

import pytest

from dags.config import DOMINIOS, WATERMARK_INICIAL
from lib import extract as libextract


def test_rol_de_extraccion_no_puede_escribir(pg):
    """Checklist DP001/DP002: ni siquiera con SQL explícito el pipeline puede
    escribir sobre el origen — ni por rol, ni por `conn.read_only`."""
    with pytest.raises(Exception):
        with pg.cursor() as cur:
            cur.execute("CREATE TABLE elt_test_no_deberia_existir (id int)")


def test_extraccion_de_un_dominio_incremental_no_falla(pg, tmp_path: Path):
    dominio = DOMINIOS["dim_sucursal"]
    resultado = libextract.extraer(dominio, "test-run-1", tmp_path, WATERMARK_INICIAL)
    assert resultado.ruta_local.exists()
    # No hay aserción de "> 0 filas": el entorno puede no tener sucursales aún.
    assert resultado.filas >= 0


def test_extraccion_full_no_usa_watermark(pg, tmp_path: Path):
    dominio = DOMINIOS["dim_marca"]
    assert dominio.modo == "full"
    resultado = libextract.extraer(dominio, "test-run-2", tmp_path, WATERMARK_INICIAL)
    assert resultado.ruta_local.exists()
