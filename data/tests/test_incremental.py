"""T023 (US4): watermark inicial, avance y persistencia (research D3)."""
from __future__ import annotations

from datetime import datetime, timezone

from dags.config import WATERMARK_INICIAL
from lib import freshness as libfreshness


def test_watermark_sin_corridas_previas_es_el_inicial(ch):
    valor = libfreshness.watermark_vigente(
        ch, dominio="test_dominio_inexistente", tabla="wh.no_existe", valor_inicial=WATERMARK_INICIAL,
    )
    assert valor == WATERMARK_INICIAL


def test_avanzar_watermark_y_releerlo(ch):
    nuevo = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    libfreshness.avanzar_watermark(
        ch, dominio="test_dominio_watermark", tabla="wh.test_tabla", run_id="run-test", nuevo_valor=nuevo,
    )
    leido = libfreshness.watermark_vigente(
        ch, dominio="test_dominio_watermark", tabla="wh.test_tabla", valor_inicial=WATERMARK_INICIAL,
    )
    assert leido.startswith("2026-06-01")


def test_frescura_registra_estado(ch):
    libfreshness.actualizar_frescura(
        ch, dominio="test_dominio_frescura", ultima_carga_ts=datetime.now(timezone.utc),
        max_updated_at_origen=None, run_id="run-test", estado="ok",
    )
    fila = ch.query(
        "SELECT estado_ultima_corrida FROM ctl.pipeline_frescura FINAL WHERE dominio = {d:String}",
        parameters={"d": "test_dominio_frescura"},
    ).result_rows
    assert fila[0][0] == "ok"
