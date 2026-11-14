"""T018 (US3): reejecutar una carga no duplica filas (`ReplacingMergeTree` +
`FINAL` — research D3). Se usa una tabla de prueba propia (no una `wh.fact_*`
real) para no depender de datos operativos concretos."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from lib import load as libload

_TABLA = "wh.test_elt_dedup"


@dataclass
class _DominioFalso:
    nombre: str
    tabla_destino: str
    modo: str = "incremental"


def _preparar_tabla(ch):
    ch.command(f"DROP TABLE IF EXISTS {_TABLA}")
    ch.command(
        f"""
        CREATE TABLE {_TABLA} (
            id UInt64, valor String, updated_at DateTime64(6)
        ) ENGINE = ReplacingMergeTree(updated_at) ORDER BY id
        """
    )


def _escribir_ndjson(ruta: Path, filas: list[dict]) -> None:
    with ruta.open("w", encoding="utf-8") as fh:
        for f in filas:
            fh.write(json.dumps(f))
            fh.write("\n")


def test_reejecutar_una_carga_no_duplica_filas(ch, tmp_path: Path):
    _preparar_tabla(ch)
    dominio = _DominioFalso(nombre="test_elt_dedup", tabla_destino=_TABLA)
    ahora = datetime.now(timezone.utc).isoformat()

    ruta = tmp_path / "raw.ndjson"
    _escribir_ndjson(ruta, [{"id": 1, "valor": "a", "updated_at": ahora}])

    libload.cargar_a_clickhouse(ch, dominio, ruta)
    libload.cargar_a_clickhouse(ch, dominio, ruta)  # mismo raw, reintento

    total = ch.query(f"SELECT count() FROM {_TABLA} FINAL").result_rows[0][0]
    assert total == 1

    ch.command(f"DROP TABLE IF EXISTS {_TABLA}")


def test_version_mas_nueva_gana(ch, tmp_path: Path):
    _preparar_tabla(ch)
    dominio = _DominioFalso(nombre="test_elt_dedup", tabla_destino=_TABLA)

    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    t2 = datetime(2026, 1, 2, tzinfo=timezone.utc).isoformat()

    r1 = tmp_path / "v1.ndjson"
    _escribir_ndjson(r1, [{"id": 1, "valor": "viejo", "updated_at": t1}])
    r2 = tmp_path / "v2.ndjson"
    _escribir_ndjson(r2, [{"id": 1, "valor": "nuevo", "updated_at": t2}])

    libload.cargar_a_clickhouse(ch, dominio, r1)
    libload.cargar_a_clickhouse(ch, dominio, r2)

    fila = ch.query(f"SELECT valor FROM {_TABLA} FINAL WHERE id = 1").result_rows
    assert fila[0][0] == "nuevo"

    ch.command(f"DROP TABLE IF EXISTS {_TABLA}")
