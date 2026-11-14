"""Parámetros (US6 — regla crítica): historial insert-only; `set` dispara recálculo
del consumidor; los "documentos emitidos" (mock) quedan intactos; auditoría antes/después."""

from __future__ import annotations

import sqlalchemy as sa

from configuracion import service as cfg_service
from configuracion.schemas import ParametroIn
from shared.models import ParametroConfiguracion, RegistroAuditoria
from shared.parametros import get_parametro, registrar_consumidor
from shared.parametros import service as param_service


def test_historial_es_insert_only_y_vigente_es_el_ultimo(db, factory):
    u = factory.usuario()
    clave = "__test_param_historial__"  # clave neutra: no la siembra ninguna migración
    cfg_service.set_parametro_cmd(db, clave, ParametroIn(valor=0.4), actor=u.id)
    cfg_service.set_parametro_cmd(db, clave, ParametroIn(valor=0.5), actor=u.id)

    filas = db.scalars(
        sa.select(ParametroConfiguracion).where(ParametroConfiguracion.clave == clave)
    ).all()
    assert len(filas) == 2  # nada se sobrescribió
    assert get_parametro(db, clave) == 0.5


def test_set_dispara_recalculo_del_consumidor_y_respeta_lo_emitido(db, factory, monkeypatch):
    # documentos "emitidos" simulados: no deben tocarse
    emitidos = [{"id": 1, "valor": 100}, {"id": 2, "valor": 100}]
    abiertas = {"n": 0}

    def consumidor_mock(_db, _clave) -> int:
        abiertas["n"] += 3  # recalcula 3 entidades abiertas
        return 3

    monkeypatch.setattr(param_service, "_CONSUMIDORES", {}, raising=False)
    registrar_consumidor("umbral_merma", consumidor_mock, nombre="mermas.recalcular")

    u = factory.usuario()
    out = cfg_service.set_parametro_cmd(db, "umbral_merma", ParametroIn(valor=250, tipo="monto"), actor=u.id)

    assert "mermas.recalcular" in out.recalculo.consumidores
    assert out.recalculo.entidades_abiertas_afectadas == 3
    assert [d["valor"] for d in emitidos] == [100, 100]  # intactos


def test_cambio_de_parametro_queda_auditado_con_antes_y_despues(db, factory):
    u = factory.usuario()
    cfg_service.set_parametro_cmd(db, "nivel_oro_min", ParametroIn(valor=1000, tipo="monto"), actor=u.id)
    cfg_service.set_parametro_cmd(db, "nivel_oro_min", ParametroIn(valor=1500, tipo="monto"), actor=u.id)

    aud = db.scalars(
        sa.select(RegistroAuditoria)
        .where(RegistroAuditoria.entidad == "parametro_configuracion")
        .order_by(RegistroAuditoria.creado_en)
    ).all()
    assert aud[-1].antes["valor"] == 1000
    assert aud[-1].despues["valor"] == 1500
