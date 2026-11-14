"""Control del pipeline (feature 012): `ctl.pipeline_watermark`,
`ctl.pipeline_corrida`, `ctl.pipeline_frescura` — research D3/D6.
"""
from __future__ import annotations

from datetime import datetime, timezone


def registrar_corrida(
    ch_client, *, run_id: str, dominio: str, fase: str, inicio: datetime,
    fin: datetime | None, estado: str, filas: int = 0, detalle_error: str = "",
) -> None:
    """Una fila por (run_id, dominio, fase) — observable por separado en la UI
    de Airflow y consultable aparte (checklist DP008/DP009)."""
    ch_client.insert(
        "ctl.pipeline_corrida",
        [[run_id, dominio, fase, inicio, fin, estado, filas, detalle_error]],
        column_names=["run_id", "dominio", "fase", "inicio", "fin", "estado", "filas", "detalle_error"],
    )


def avanzar_watermark(ch_client, *, dominio: str, tabla: str, run_id: str, nuevo_valor: str) -> None:
    """Guarda el nuevo watermark tras un `load_wh` exitoso (research D3)."""
    ch_client.insert(
        "ctl.pipeline_watermark",
        [[dominio, tabla, datetime.fromisoformat(nuevo_valor), run_id, datetime.now(timezone.utc)]],
        column_names=["dominio", "tabla", "ultimo_valor", "ultimo_run_id", "actualizado_en"],
    )


def watermark_vigente(ch_client, *, dominio: str, tabla: str, valor_inicial: str) -> str:
    filas = ch_client.query(
        "SELECT ultimo_valor FROM ctl.pipeline_watermark FINAL WHERE dominio = {dominio:String} AND tabla = {tabla:String}",
        parameters={"dominio": dominio, "tabla": tabla},
    ).result_rows
    if not filas:
        return valor_inicial
    return filas[0][0].isoformat()


def actualizar_frescura(
    ch_client, *, dominio: str, ultima_carga_ts: datetime, max_updated_at_origen: str | None,
    run_id: str, estado: str,
) -> None:
    """Tras cada `load_wh_<dominio>` exitoso (research D6) — lo lee
    `GET /reportes/estado-frescura`."""
    max_ua = datetime.fromisoformat(max_updated_at_origen) if max_updated_at_origen else None
    ch_client.insert(
        "ctl.pipeline_frescura",
        [[dominio, ultima_carga_ts, max_ua, run_id, estado]],
        column_names=["dominio", "ultima_carga_ts", "max_updated_at_origen", "ultimo_run_id", "estado_ultima_corrida"],
    )
