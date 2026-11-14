"""Fases Load warehouse y Transform del flujo ELT (feature 012).

Carga el raw de `landing-zone` a la tabla de hechos/dimensión de ClickHouse
(`ReplacingMergeTree` por clave + `updated_at`) — un reintento no duplica
filas, solo agrega una nueva versión que gana al leer con `FINAL` (research D3).

No hay una capa de "staging" separada: cada dominio (`dags/config.py`) ya
extrae denormalizado al grano de su tabla destino, así que "load_wh" inserta
directo en `wh.fact_*`/`wh.dim_*` — es la simplificación documentada en
`warehouse/ddl/030_fact_tables.sql`.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger("cronos.elt.load")


def _tipo_base(tipo_ch: str) -> tuple[str, bool]:
    """`"Nullable(Decimal(18, 2))"` -> `("Decimal(18, 2)", True)`."""
    m = re.match(r"^Nullable\((.+)\)$", tipo_ch)
    if m:
        return m.group(1), True
    return tipo_ch, False


def _convertidor(tipo_ch: str):
    """Convierte el valor JSON-string de un campo NDJSON al tipo Python que
    `clickhouse-connect` espera para esa columna. Genérico por tipo, no por
    dominio — así un dominio nuevo no necesita tocar esta función."""
    base, nullable = _tipo_base(tipo_ch)

    if base.startswith("Decimal"):
        conv = lambda v: Decimal(str(v))
    elif base.startswith("DateTime"):
        conv = lambda v: datetime.fromisoformat(v)
    elif base == "Date":
        conv = lambda v: date.fromisoformat(v)
    elif base.startswith(("UInt", "Int")):
        conv = lambda v: int(v)
    elif base.startswith("Float"):
        conv = lambda v: float(v)
    else:  # String, Enum8/16, etc.
        conv = lambda v: str(v)

    if nullable:
        return lambda v: None if v is None else conv(v)
    return lambda v: conv(v)


def _columnas_y_convertidores(ch_client, tabla_destino: str) -> tuple[list[str], list]:
    filas = ch_client.query(f"DESCRIBE TABLE {tabla_destino}").result_rows
    columnas = [f[0] for f in filas]
    convertidores = [_convertidor(f[1]) for f in filas]
    return columnas, convertidores


def cargar_a_clickhouse(ch_client, dominio, ruta_ndjson: Path) -> int:
    """Lee el NDJSON descargado de `landing-zone` e inserta cada fila en
    `dominio.tabla_destino`. Devuelve el número de filas cargadas."""
    columnas, convertidores = _columnas_y_convertidores(ch_client, dominio.tabla_destino)

    lote: list[list] = []
    total = 0
    with ruta_ndjson.open("r", encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            cruda = json.loads(linea)
            fila = [conv(cruda.get(col)) for col, conv in zip(columnas, convertidores)]
            lote.append(fila)
            total += 1

    if lote:
        ch_client.insert(dominio.tabla_destino, lote, column_names=columnas)

    logger.info("load_wh[%s] -> %d fila(s) insertadas en %s", dominio.nombre, total, dominio.tabla_destino)
    return total


def asegurar_dim_fecha(ch_client, desde: str = "2020-01-01", hasta: str = "2035-12-31") -> None:
    """Siembra `wh.dim_fecha` una vez (idempotente): no viene de PostgreSQL, se
    genera. `toDayOfWeek` de ClickHouse: 1=lunes … 7=domingo."""
    ya = ch_client.query("SELECT count() FROM wh.dim_fecha").result_rows[0][0]
    if ya > 0:
        return
    ch_client.command(
        f"""
        INSERT INTO wh.dim_fecha
        SELECT
            d AS fecha,
            toYear(d) AS anio,
            toMonth(d) AS mes,
            toISOWeek(d) AS semana,
            toDayOfWeek(d) AS dia_semana
        FROM (
            SELECT arrayJoin(
                arrayMap(x -> toDate('{desde}') + x, range(toUInt32(dateDiff('day', toDate('{desde}'), toDate('{hasta}')) + 1)))
            ) AS d
        )
        """
    )
    logger.info("dim_fecha sembrada: %s .. %s", desde, hasta)
