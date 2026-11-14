"""Feature 006 — cupones (US5): uso único, vencimiento, límites de uso."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from clientes import service as cli
from clientes.schemas import ClienteIn, ConsentimientoIn, CuponIn
from shared.exceptions import ConflictError
from shared.guard import CurrentUser


def _gg(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def _cliente(db, factory, ident="1710009000"):
    return cli.crear(db, ClienteIn(tipo="natural", identificacion=ident, nombre="Titular Cupón",
                                   consentimiento=ConsentimientoIn(aceptado=True, version_texto=1)),
                     actor=factory.usuario().id)


def test_cupon_uso_unico_no_se_consume_dos_veces(db, factory):
    gg = _gg(factory)
    c = _cliente(db, factory)
    cli.crear_cupon(db, CuponIn(codigo="CUMPLE-001", cliente_id=c.id, tipo="porcentaje", valor=Decimal("0.1"),
                                alcance="tienda", limite_uso="una_vez",
                                vigencia_fin=date.today() + timedelta(days=30)), actor=gg.id)

    consumido = cli.consumir_cupon(db, codigo="CUMPLE-001", documento_tipo="venta", documento_id=1, actor=gg.id)
    assert consumido.estado == "usado" and consumido.usos == 1

    with pytest.raises(ConflictError):
        cli.consumir_cupon(db, codigo="CUMPLE-001", documento_tipo="venta", documento_id=2, actor=gg.id)


def test_cupon_vencido_se_rechaza(db, factory):
    gg = _gg(factory)
    c = _cliente(db, factory, ident="1710009001")
    cli.crear_cupon(db, CuponIn(codigo="VIEJO-1", cliente_id=c.id, tipo="monto", valor=Decimal("20"),
                                alcance="tienda", limite_uso="una_vez",
                                vigencia_fin=date.today() - timedelta(days=1)), actor=gg.id)
    with pytest.raises(ConflictError):
        cli.consumir_cupon(db, codigo="VIEJO-1", documento_tipo="venta", documento_id=5, actor=gg.id)


def test_cupon_n_veces_respeta_el_maximo(db, factory):
    gg = _gg(factory)
    c = _cliente(db, factory, ident="1710009002")
    cli.crear_cupon(db, CuponIn(codigo="MULTI-3", cliente_id=c.id, tipo="porcentaje", valor=Decimal("0.05"),
                                alcance="marca", alcance_ref="Rolex", limite_uso="n_veces", max_usos=3,
                                vigencia_fin=date.today() + timedelta(days=90)), actor=gg.id)
    for i in range(3):
        cli.consumir_cupon(db, codigo="MULTI-3", documento_tipo="orden_trabajo", documento_id=10 + i, actor=gg.id)
    with pytest.raises(ConflictError):
        cli.consumir_cupon(db, codigo="MULTI-3", documento_tipo="orden_trabajo", documento_id=99, actor=gg.id)


def test_consumo_concurrente_solo_uno_pasa(client, factory, auth_header, db):
    gg = factory.usuario(roles=[factory.gerencia()])
    c = _cliente(db, factory, ident="1710009003")
    client.post("/cupones", json={"codigo": "RACE-1", "cliente_id": c.id, "tipo": "porcentaje", "valor": 0.1,
                                  "alcance": "tienda", "limite_uso": "una_vez",
                                  "vigencia_fin": str(date.today() + timedelta(days=30))},
                headers=auth_header(gg))

    r1 = client.post("/_internal/cupones/consumir", json={"codigo": "RACE-1", "documento_tipo": "venta", "documento_id": 1}, headers=auth_header(gg))
    r2 = client.post("/_internal/cupones/consumir", json={"codigo": "RACE-1", "documento_tipo": "venta", "documento_id": 2}, headers=auth_header(gg))
    assert {r1.status_code, r2.status_code} == {200, 409}
