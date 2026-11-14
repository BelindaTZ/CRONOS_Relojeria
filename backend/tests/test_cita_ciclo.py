"""Feature 007 — registro y ciclo de estados de una cita (US1, US2, US4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from citas import service as citas
from citas.schemas import AtenderIn, CancelarIn, CitaIn, ConfirmarIn
from clientes import service as cli
from clientes.schemas import ClienteIn, ConsentimientoIn
from shared.exceptions import ConflictError, ValidationError
from sqlalchemy import select

from shared.guard import CurrentUser
from shared.models import CanalCita


def _user(factory, *, gerencia=False, sucursales=()):
    u = factory.usuario(roles=[factory.gerencia()] if gerencia else [], sucursales=list(sucursales))
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full",
                       roles=["Gerencia General"] if gerencia else [], rol_ids=[],
                       sucursal_ids=[s.id for s in sucursales])


def _canal(db, clave="presencial"):
    return db.scalars(select(CanalCita).where(CanalCita.clave == clave)).first().id


def _cliente(db, factory, ident="1712000001"):
    return cli.crear(db, ClienteIn(tipo="natural", identificacion=ident, nombre="Cliente Cita",
                                   consentimiento=ConsentimientoIn(aceptado=True, version_texto=1)),
                     actor=factory.usuario().id)


def _cita_in(cliente_id, sucursal_id, canal_id, **kw):
    base = dict(cliente_id=cliente_id, sucursal_id=sucursal_id, canal_cita_id=canal_id,
                motivo="servicio_tecnico", fecha_preferida=datetime(2030, 1, 15, 10, 0, tzinfo=timezone.utc))
    base.update(kw)
    return CitaIn(**base)


def test_crear_exige_cliente_existente_y_canal_valido(db, factory):
    gg = _user(factory, gerencia=True)
    suc = factory.sucursal("Boutique")
    canal = _canal(db)
    c = _cliente(db, factory)

    ok = citas.crear(db, _cita_in(c.id, suc.id, canal), actor=gg.id)
    assert ok.estado == "pendiente" and ok.cliente_nombre == "Cliente Cita"

    with pytest.raises(ValidationError):
        citas.crear(db, _cita_in(999999, suc.id, canal), actor=gg.id)
    with pytest.raises(ValidationError):
        citas.crear(db, _cita_in(c.id, suc.id, 999999), actor=gg.id)


def test_ciclo_pendiente_confirmada_atendida(db, factory):
    gg = _user(factory, gerencia=True)
    suc = factory.sucursal("Suc ciclo")
    canal = _canal(db)
    c = _cliente(db, factory, "1712000002")
    cita = citas.crear(db, _cita_in(c.id, suc.id, canal), actor=gg.id)

    conf = citas.confirmar(db, cita.id, fecha_confirmada=None, actor=gg.id)
    assert conf.cita.estado == "confirmada" and conf.cita.fecha_confirmada == cita.fecha_preferida
    assert conf.warning is None

    at = citas.atender(db, cita.id, venta_id=None, orden_trabajo_id=None, actor=gg.id)
    assert at.cita.estado == "atendida"
    # motivo servicio_tecnico sin OT → acción de creación con contexto
    assert at.accion is not None and at.accion.tipo == "crear_ot"
    assert at.accion.cliente_id == c.id and at.accion.cita_id == cita.id

    hist = citas.historial_estados(db, cita.id)
    assert [h["estado"] for h in hist] == ["pendiente", "confirmada", "atendida"]


def test_no_se_cancela_una_cita_atendida(db, factory):
    gg = _user(factory, gerencia=True)
    suc = factory.sucursal("Suc cancel")
    c = _cliente(db, factory, "1712000003")
    cita = citas.crear(db, _cita_in(c.id, suc.id, _canal(db)), actor=gg.id)
    citas.atender(db, cita.id, venta_id=None, orden_trabajo_id=None, actor=gg.id)
    with pytest.raises(ConflictError):
        citas.cancelar(db, cita.id, motivo="ya no aplica", actor=gg.id)


def test_cancelar_exige_motivo(db, factory):
    gg = _user(factory, gerencia=True)
    suc = factory.sucursal("Suc mot")
    c = _cliente(db, factory, "1712000004")
    cita = citas.crear(db, _cita_in(c.id, suc.id, _canal(db)), actor=gg.id)
    citas.confirmar(db, cita.id, fecha_confirmada=None, actor=gg.id)
    out = citas.cancelar(db, cita.id, motivo="el cliente reprograma", actor=gg.id)
    assert out.estado == "cancelada" and out.motivo_cancelacion == "el cliente reprograma"


def test_advertencia_de_solape_sin_bloqueo(db, factory):
    gg = _user(factory, gerencia=True)
    suc = factory.sucursal("Suc solape")
    canal = _canal(db)
    c1 = _cliente(db, factory, "1712000005")
    c2 = _cliente(db, factory, "1712000006")
    t = datetime(2030, 2, 1, 11, 0, tzinfo=timezone.utc)

    a = citas.crear(db, _cita_in(c1.id, suc.id, canal, fecha_preferida=t), actor=gg.id)
    b = citas.crear(db, _cita_in(c2.id, suc.id, canal, fecha_preferida=t + timedelta(minutes=15)), actor=gg.id)

    citas.confirmar(db, a.id, fecha_confirmada=None, actor=gg.id)
    conf_b = citas.confirmar(db, b.id, fecha_confirmada=None, actor=gg.id)
    assert conf_b.cita.estado == "confirmada"        # NO bloquea
    assert conf_b.warning is not None and "cita" in conf_b.warning.lower()


def test_atender_con_orden_trabajo_vincula_directo(db, factory):
    gg = _user(factory, gerencia=True)
    suc = factory.sucursal("Suc vinc")
    c = _cliente(db, factory, "1712000007")
    cita = citas.crear(db, _cita_in(c.id, suc.id, _canal(db), motivo="compra"), actor=gg.id)
    at = citas.atender(db, cita.id, venta_id=555, orden_trabajo_id=None, actor=gg.id)
    assert at.cita.venta_id == 555 and at.accion is None


def test_atender_motivo_consulta_no_genera_accion(db, factory):
    gg = _user(factory, gerencia=True)
    suc = factory.sucursal("Suc consulta")
    c = _cliente(db, factory, "1712000008")
    cita = citas.crear(db, _cita_in(c.id, suc.id, _canal(db), motivo="consulta"), actor=gg.id)
    at = citas.atender(db, cita.id, venta_id=None, orden_trabajo_id=None, actor=gg.id)
    assert at.cita.estado == "atendida" and at.accion is None
