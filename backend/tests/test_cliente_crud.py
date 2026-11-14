"""Feature 006 — CRM de clientes (US1)."""

from __future__ import annotations

import pytest

from clientes import service as cli
from clientes.schemas import ClienteIn, ClientePatch, ConsentimientoIn
from shared.exceptions import ValidationError
from shared.guard import CurrentUser


def _plano(u):
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=[], rol_ids=[], sucursal_ids=[])


def _elevado(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def _cliente_in(**kw):
    base = dict(tipo="natural", identificacion="1712345678", nombre="Ana Ríos", email="ana@x.com",
                consentimiento=ConsentimientoIn(aceptado=True, version_texto=1))
    base.update(kw)
    return ClienteIn(**base)


def test_alta_genera_afiliado_y_nivel_base(db, factory):
    actor = factory.usuario().id
    c = cli.crear(db, _cliente_in(), actor=actor)
    assert c.numero_afiliado.startswith("AF-") and c.numero_afiliado != "AF-000000"
    assert c.nivel_nombre == "Bronce"
    assert c.consentimiento_vigente.aceptado is True


def test_sin_consentimiento_falla(db, factory):
    actor = factory.usuario().id
    with pytest.raises(ValidationError):
        cli.crear(db, _cliente_in(consentimiento=ConsentimientoIn(aceptado=False, version_texto=1)), actor=actor)


def test_identificacion_duplicada(db, factory):
    actor = factory.usuario().id
    cli.crear(db, _cliente_in(identificacion="0102030405"), actor=actor)
    from shared.exceptions import ConflictError

    with pytest.raises(ConflictError):
        cli.crear(db, _cliente_in(identificacion="0102030405", nombre="Otro"), actor=actor)


def test_editar_identificacion_requiere_rol_elevado(db, factory):
    actor = factory.usuario().id
    c = cli.crear(db, _cliente_in(identificacion="1710000001"), actor=actor)

    with pytest.raises(cli.NoAutorizadoError):
        cli.actualizar(db, c.id, ClientePatch(identificacion="1710000009"), user=_plano(factory.usuario()))

    ok = cli.actualizar(db, c.id, ClientePatch(identificacion="1710000009"), user=_elevado(factory))
    assert ok.identificacion == "1710000009"

    # el resto de datos los edita el personal normal
    ok2 = cli.actualizar(db, c.id, ClientePatch(telefono="0999999999"), user=_plano(factory.usuario()))
    assert ok2.telefono == "0999999999"


def test_busqueda_multicriterio(client, factory, auth_header):
    gerente = factory.usuario(roles=[factory.gerencia()])
    r = client.post("/clientes", json={"tipo": "natural", "identificacion": "1799887766", "nombre": "Carla Núñez",
                                       "email": "carla@correo.com", "telefono": "0987001002",
                                       "consentimiento": {"aceptado": True, "version_texto": 1}},
                    headers=auth_header(gerente))
    assert r.status_code == 201, r.text
    afiliado = r.json()["numero_afiliado"]

    for q in ("Núñez", "1799887766", "carla@correo.com", "0987001002", afiliado):
        res = client.get(f"/clientes?q={q}", headers=auth_header(gerente))
        assert res.status_code == 200
        assert any(x["identificacion"] == "1799887766" for x in res.json()["items"]), q

    # el consumidor final nunca aparece en el listado normal
    todos = client.get("/clientes", headers=auth_header(gerente)).json()["items"]
    assert not any(x["es_consumidor_final"] for x in todos)
