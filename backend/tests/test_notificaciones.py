"""Feature 014 — notificaciones automatizadas por email.

`EMAIL_BACKEND=console` está forzado por `conftest.py` (nunca SendGrid en
tests) — el worker sí llega a `shared.correo.enviar()` en estos tests, pero
solo loguea, nunca sale a internet."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from clientes import service as cli
from clientes.schemas import ClienteIn, ConsentimientoIn
from notificaciones import service as notif
from notificaciones import repository as notif_repo
from shared.guard import CurrentUser


def _plano(u):
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=[], rol_ids=[], sucursal_ids=[])


def _gerencia(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def _cliente(db, factory, **kw):
    actor = factory.usuario().id
    base = dict(
        tipo="natural", identificacion=f"17{uuid.uuid4().hex[:8]}", nombre="Cliente Demo",
        email="cliente-demo@example.com", consentimiento=ConsentimientoIn(aceptado=True, version_texto=1),
    )
    base.update(kw)
    return cli.crear(db, ClienteIn(**base), actor=actor)


# --------------------------------------------------------------------- encolar
def test_encolar_crea_envio_encolado(db, factory):
    c = _cliente(db, factory)
    e = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=1, hito="entregado",
        contexto={"cliente_nombre": c.nombre}, cliente_id=c.id,
    )
    db.commit()
    assert e.estado == "encolado"
    assert e.destinatario_email == c.email


def test_encolar_deduplica_por_clave_idempotencia(db, factory):
    c = _cliente(db, factory)
    e1 = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=2, hito="entregado",
        contexto={}, cliente_id=c.id,
    )
    e2 = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=2, hito="entregado",
        contexto={"algo": "distinto"}, cliente_id=c.id,
    )
    db.commit()
    assert e1.id == e2.id


def test_encolar_sin_email_marca_sin_destinatario(db, factory):
    c = _cliente(db, factory, email=None)
    e = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=3, hito="entregado",
        contexto={}, cliente_id=c.id,
    )
    db.commit()
    assert e.estado == "sin_destinatario"
    assert e.motivo_estado == "sin_destinatario"


def test_encolar_respeta_opt_out(db, factory):
    c = _cliente(db, factory)
    notif.set_preferencia(db, c.id, "cupon", opt_in=False)
    db.commit()
    e = notif.encolar(
        db, tipo="cupon", disparo_origen_tipo="cupon", disparo_origen_id=99, hito="CODE1",
        contexto={}, cliente_id=c.id,
    )
    db.commit()
    assert e.estado == "cancelado"
    assert e.motivo_estado == "opt_out"


def test_tipo_critico_ignora_opt_out(db, factory):
    with pytest.raises(Exception):
        notif.set_preferencia(db, 1, "password_temporal", opt_in=False)


def test_opt_out_no_bloquea_la_creacion_del_cupon(db, factory):
    """El cupón se crea igual aunque el aviso quede cancelado por opt-out —
    Spec US5 acceptance scenario 2."""
    from clientes.schemas import CuponIn

    c = _cliente(db, factory)
    notif.set_preferencia(db, c.id, "cupon", opt_in=False)
    db.commit()
    actor = factory.usuario().id
    cupon = cli.crear_cupon(db, CuponIn(
        codigo=f"TEST-{c.id}", cliente_id=c.id, tipo="monto", valor="10",
        alcance="tienda", limite_uso="una_vez", vigencia_fin=(datetime.now().date() + timedelta(days=30)),
    ), actor=actor)
    db.commit()
    assert cupon.codigo == f"TEST-{c.id}"
    envios, _ = notif_repo.listar_envios(db, tipo="cupon", estado=None, cliente_id=c.id, disparo_origen_id=None, offset=0, limit=10)
    assert envios and envios[0].estado == "cancelado"


# ------------------------------------------------------------------ worker
def test_procesar_cola_envia_y_marca_enviado(db, factory):
    c = _cliente(db, factory)
    e = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=4, hito="entregado",
        contexto={"cliente_nombre": c.nombre, "ot_numero": "OT-0001"}, cliente_id=c.id,
    )
    db.commit()
    procesados = notif.procesar_cola(db)
    assert procesados >= 1
    db.refresh(e)
    assert e.estado == "enviado"
    assert e.intentos == 1


def test_worker_no_pierde_envios_con_proveedor_caido(db, factory, monkeypatch):
    c = _cliente(db, factory)
    e = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=5, hito="entregado",
        contexto={}, cliente_id=c.id,
    )
    db.commit()

    def _falla(*a, **kw):
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr("shared.correo.enviar", _falla)
    notif.procesar_cola(db)
    db.refresh(e)
    assert e.estado == "encolado"  # reintentable, no perdido
    assert e.intentos == 1
    assert e.proxima_ejecucion > datetime.now(timezone.utc)


# --------------------------------------------------------------- reintentar
def test_reintentar_exige_estado_fallido_o_rebotado(db, factory):
    c = _cliente(db, factory)
    e = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=6, hito="entregado",
        contexto={}, cliente_id=c.id,
    )
    db.commit()
    with pytest.raises(Exception):
        notif.reintentar(db, e.id, user=_plano(factory.usuario()))


def test_reintentar_reencola_un_fallido(db, factory):
    c = _cliente(db, factory)
    e = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=7, hito="entregado",
        contexto={}, cliente_id=c.id,
    )
    e.estado = "fallido"
    db.flush()
    db.commit()
    reencolado = notif.reintentar(db, e.id, user=_plano(factory.usuario()))
    assert reencolado.estado == "encolado"


# --------------------------------------------------------------- cancelar_pendiente
def test_cancelar_pendiente_de_un_disparo(db, factory):
    c = _cliente(db, factory)
    notif.encolar(
        db, tipo="recordatorio_cita", disparo_origen_tipo="cita", disparo_origen_id=42, hito="2026-10-01T10:00",
        contexto={}, cliente_id=c.id, programar_para=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.commit()
    n = notif.cancelar_pendiente(db, disparo_origen_tipo="cita", disparo_origen_id=42, motivo="cita_cancelada")
    db.commit()
    assert n == 1


# ------------------------------------------------------------------ plantillas
def test_set_plantilla_solo_gerencia(client, factory, auth_header):
    u = factory.usuario(roles=[factory.rol("Vendedor")])
    r = client.put("/plantillas/recordatorio_cita", json={"asunto": "x", "cuerpo": "<p>x</p>"}, headers=auth_header(u))
    assert r.status_code == 403


def test_set_plantilla_gerencia_incrementa_version(db, factory):
    user = _gerencia(factory)
    v1 = notif.set_plantilla(db, "recordatorio_cita", asunto="Su cita", cuerpo="<p>{{cliente_nombre}}</p>", user=user)
    db.commit()
    assert v1["version"] == 1
    v2 = notif.set_plantilla(db, "recordatorio_cita", asunto="Su cita v2", cuerpo="<p>{{cliente_nombre}} v2</p>", user=user)
    db.commit()
    assert v2["version"] == 2
    detalle = notif.get_plantilla(db, "recordatorio_cita")
    assert detalle["actual"]["version"] == 2
    assert len(detalle["historial"]) == 2


def test_override_de_plantilla_se_usa_al_renderizar(db, factory, monkeypatch):
    """`render()` abre su propia `SessionLocal()` de solo lectura (para no
    exigirle un `db` a los ~15 sitios de llamada existentes) — en el test la
    apuntamos a la MISMA conexión/transacción del fixture `db` (que nunca
    commitea de verdad, solo un savepoint) para poder ver la fila recién
    escrita sin salir de la transacción aislada del test."""
    import contextlib

    from shared.correo.service import render

    user = _gerencia(factory)
    notif.set_plantilla(db, "recordatorio_cita", asunto="Asunto override", cuerpo="<p>Hola {{cliente_nombre}}</p>", user=user)
    db.flush()

    monkeypatch.setattr("shared.database.SessionLocal", lambda: contextlib.nullcontext(db))
    html, _texto = render("recordatorio_cita", {"cliente_nombre": "Ana"})
    assert "Hola Ana" in html


def test_plantilla_tipo_desconocido_404(client, factory, auth_header):
    u = _gerencia(factory)
    uu = factory.usuario(roles=[factory.gerencia()])
    r = client.get("/plantillas/no-existe", headers=auth_header(uu))
    assert r.status_code == 404


# -------------------------------------------------------------------- webhook
def test_webhook_actualiza_estado_entregado(db, factory):
    c = _cliente(db, factory)
    e = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=8, hito="entregado",
        contexto={}, cliente_id=c.id,
    )
    e.estado = "enviado"
    e.proveedor_message_id = "abc123.filterdrecv-xyz"
    db.flush()
    db.commit()
    notif.procesar_webhook(db, [{"sg_message_id": "abc123.filterdrecv-otherpart", "event": "delivered"}])
    db.refresh(e)
    assert e.estado == "entregado"


# -------------------------------------------------------------- desacople
def test_encolar_nunca_lanza_por_fallo_de_contexto(db, factory):
    """FR-017: un disparo no puede fallar la transacción de origen."""
    e = notif.encolar(
        db, tipo="ot_entregado", disparo_origen_tipo="orden_trabajo", disparo_origen_id=9999, hito="entregado",
        contexto={}, cliente_id=999999,  # cliente inexistente
    )
    db.commit()
    assert e.estado == "sin_destinatario"


# -------------------------------------------------------------------- RBAC
def test_envios_exige_permiso_notificaciones(client, factory, auth_header):
    u = factory.usuario(roles=[factory.rol("Vendedor")])
    r = client.get("/envios", headers=auth_header(u))
    assert r.status_code == 403


def test_envios_gerente_sucursal_tiene_acceso(client, factory, auth_header):
    u = factory.usuario(roles=[factory.rol("Gerente de Sucursal")])
    r = client.get("/envios", headers=auth_header(u))
    assert r.status_code == 200
