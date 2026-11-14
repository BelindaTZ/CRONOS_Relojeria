"""Fase Extract del flujo ELT (feature 012): lectura incremental de PostgreSQL,
estrictamente de SOLO LECTURA (Spec §FR-006). No escribe nada sobre el origen.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from psycopg.rows import dict_row

from lib.db import pg_readonly_connection

logger = logging.getLogger("cronos.elt.extract")


@dataclass
class ResultadoExtraccion:
    ruta_local: Path
    filas: int
    max_updated_at: str | None  # ISO 8601, o None si no hubo filas


def _json_default(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    raise TypeError(f"Tipo no serializable en el raw de landing-zone: {type(valor)!r}")


def extraer(dominio, run_id: str, tmp_dir: Path, watermark_actual: str) -> ResultadoExtraccion:
    """Ejecuta el SQL del dominio (con `%(watermark)s` si es incremental) y
    escribe el resultado como NDJSON en `tmp_dir/<dominio>.ndjson`.

    `dominio` es una instancia de `dags.config.Dominio` (se evita el import
    directo para no acoplar `lib` a Airflow ni al paquete `dags`).
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    destino = tmp_dir / f"{dominio.nombre}.ndjson"

    params = {"watermark": watermark_actual} if dominio.modo == "incremental" else None

    filas = 0
    max_updated_at: datetime | None = None
    with pg_readonly_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(dominio.sql, params)
        with destino.open("w", encoding="utf-8") as fh:
            for fila in cur:
                fh.write(json.dumps(fila, default=_json_default, ensure_ascii=False))
                fh.write("\n")
                filas += 1
                ua = fila.get("updated_at")
                if isinstance(ua, str):
                    ua = datetime.fromisoformat(ua)
                if ua is not None:
                    if ua.tzinfo is None:
                        ua = ua.replace(tzinfo=timezone.utc)
                    if max_updated_at is None or ua > max_updated_at:
                        max_updated_at = ua

    logger.info("extract[%s] run_id=%s -> %d filas", dominio.nombre, run_id, filas)
    return ResultadoExtraccion(
        ruta_local=destino,
        filas=filas,
        max_updated_at=max_updated_at.isoformat() if max_updated_at else None,
    )
