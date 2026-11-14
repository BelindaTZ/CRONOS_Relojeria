"""Feature 007 — agenda del día/semana, scope por sucursal, conversión, recordatorios (US3, Polish)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from citas import service as citas
from citas.schemas import CitaIn
from clientes import service as cli
from clientes.schemas import ClienteIn, ConsentimientoIn
from shared.guard import CurrentUser
from shared.models import CanalCita


def _user(factory, *, gerencia=False, sucursales=()):
    u = factory.usuario(roles=[factory.gerencia()] if gerencia else [], sucursales=list(sucursales))
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full",
                       roles=["Gerencia General"] if gerencia else [], rol_ids=[],
                       sucursal_ids=[s.id for s in sucursales])


def _canal(db):
    return db.scalars(select(CanalCita).where(CanalCita.clave == "presencial")).first().id


def _cliente(db, factory, ident):
    return cli.crear(db, ClienteIn(tipo="natural", identificacion=ident, nombre=f"Cli {ident}",
                                   consentimiento=ConsentimientoIn(aceptado=True, version_texto=1)),
                     actor=factory.usuario().id)


def _cita(db, gg, cliente_id, suc_id, canal, when, motivo="consulta"):
    return citas.crear(db, CitaIn(cliente_id=cliente_id, sucursal_id=suc_id, canal_cita_id=canal,
                                  motivo=motivo, fecha_preferida=when), actor=gg.id)


def test_agenda_del_dia_ordenada_y_con_scope(db, factory):
    gg = _user(factory, gerencia=True)
    canal = _canal(db)
    suc_a = factory.sucursal("Suc A")
    suc_b = factory.sucursal("Suc B")
    ca = _cliente(db, factory, "1713000001")
    cb = _cliente(db, factory, "1713000002")

    dia = datetime(2030, 6, 10, tzinfo=timezone.utc)
    _cita(db, gg, ca.id, suc_a.id, canal, dia.replace(hour=15))
    _cita(db, gg, ca.id, suc_a.id, canal, dia.replace(hour=9))
    _cita(db, gg, cb.id, suc_b.id, canal, dia.replace(hour=11))

    # usuario de A solo ve las de A, ordenadas por hora
    user_a = _user(factory, sucursales=[suc_a])
    ag = citas.agenda(db, user=user_a, rango="dia", fecha=dia, sucursal_id=None)
    assert [x.sucursal_id for x in ag] == [suc_a.id, suc_a.id]
    assert ag[0].hora.hour == 9 and ag[1].hora.hour == 15

    # Gerencia puede pedir una sucursal concreta
    ag_b = citas.agenda(db, user=gg, rango="dia", fecha=dia, sucursal_id=suc_b.id)
    assert len(ag_b) == 1 and ag_b[0].cliente_id == cb.id

    # un usuario de A que pide la sucursal B NO ve nada (el alcance no se salta)
    fuga = citas.agenda(db, user=user_a, rango="dia", fecha=dia, sucursal_id=suc_b.id)
    assert fuga == []


def test_agenda_semana_incluye_toda_la_semana(db, factory):
    gg = _user(factory, gerencia=True)
    canal = _canal(db)
    suc = factory.sucursal("Suc semana")
    c = _cliente(db, factory, "1713000010")
    lunes = datetime(2030, 6, 3, tzinfo=timezone.utc)  # 2030-06-03 es lunes
    _cita(db, gg, c.id, suc.id, canal, lunes.replace(hour=10))
    _cita(db, gg, c.id, suc.id, canal, (lunes + timedelta(days=4)).replace(hour=16))

    ag = citas.agenda(db, user=gg, rango="semana", fecha=lunes + timedelta(days=2), sucursal_id=suc.id)
    assert len(ag) == 2


def test_conversion_operativa(db, factory):
    gg = _user(factory, gerencia=True)
    canal = _canal(db)
    suc = factory.sucursal("Suc conv")
    c = _cliente(db, factory, "1713000020")
    base = datetime(2030, 7, 1, 10, tzinfo=timezone.utc)

    a = _cita(db, gg, c.id, suc.id, canal, base, motivo="compra")
    b = _cita(db, gg, c.id, suc.id, canal, base + timedelta(days=1), motivo="compra")
    citas.atender(db, a.id, venta_id=1, orden_trabajo_id=None, actor=gg.id)
    citas.atender(db, b.id, venta_id=None, orden_trabajo_id=None, actor=gg.id)  # sin vincular

    conv = citas.conversion(db, desde=None, hasta=None)
    assert conv.atendidas == 2 and conv.con_transaccion == 1 and conv.tasa == 0.5


def test_citas_para_recordatorio_solo_confirmadas_en_ventana(db, factory):
    gg = _user(factory, gerencia=True)
    canal = _canal(db)
    suc = factory.sucursal("Suc record")
    c = _cliente(db, factory, "1713000030")
    ahora = datetime.now(timezone.utc)

    pronto = _cita(db, gg, c.id, suc.id, canal, ahora + timedelta(hours=6))
    lejos = _cita(db, gg, c.id, suc.id, canal, ahora + timedelta(days=5))
    citas.confirmar(db, pronto.id, fecha_confirmada=None, actor=gg.id)
    citas.confirmar(db, lejos.id, fecha_confirmada=None, actor=gg.id)

    r = citas.citas_para_recordatorio(db, antelacion="24h")
    ids = {x["cita_id"] for x in r}
    assert pronto.id in ids and lejos.id not in ids

    # una cancelada después ya no aparece
    citas.cancelar(db, pronto.id, motivo="cliente avisa", actor=gg.id)
    assert not any(x["cita_id"] == pronto.id for x in citas.citas_para_recordatorio(db, antelacion="24h"))
