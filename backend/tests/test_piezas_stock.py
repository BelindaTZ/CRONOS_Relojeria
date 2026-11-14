"""Feature 003 — piezas: stock nunca negativo, perecederos con lote/caducidad (FEFO)."""

from __future__ import annotations

import pytest


@pytest.fixture
def suc(db, factory):
    return factory.sucursal("Bodega 003")


@pytest.fixture
def gerente(db, factory, suc):
    return factory.usuario(roles=[factory.gerencia()], sucursales=[suc])


def _crear_pieza(client, h, **over):
    body = {"codigo": over.pop("codigo", "9010"), "descripcion": "Moebius 9010",
            "tipo": "original", "stock_minimo": over.pop("stock_minimo", 2), **over}
    r = client.post("/piezas", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _mov(client, h, pid, **body):
    return client.post(f"/piezas/{pid}/movimientos", json=body, headers=h)


def test_stock_nunca_negativo(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    p = _crear_pieza(client, h)
    assert _mov(client, h, p["id"], sucursal_id=suc.id, tipo="ingreso", cantidad=3).status_code == 201

    # consumir 1 y 1 más -> ok; el tercero deja 1; el cuarto (2) NO puede
    assert _mov(client, h, p["id"], sucursal_id=suc.id, tipo="consumo_ot", cantidad=1).status_code == 201
    r = _mov(client, h, p["id"], sucursal_id=suc.id, tipo="consumo_ot", cantidad=5)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "stock_insuficiente"

    det = client.get(f"/piezas/{p['id']}", headers=h).json()
    total = sum(s["stock_actual"] for s in det["stock_por_sucursal"])
    assert total == 2


def test_ultima_unidad_solo_un_consumo_gana(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    p = _crear_pieza(client, h, codigo="LAST-1")
    _mov(client, h, p["id"], sucursal_id=suc.id, tipo="ingreso", cantidad=1)

    exitos = sum(
        _mov(client, h, p["id"], sucursal_id=suc.id, tipo="consumo_ot", cantidad=1).status_code == 201
        for _ in range(10)
    )
    assert exitos == 1
    det = client.get(f"/piezas/{p['id']}", headers=h).json()
    assert all(s["stock_actual"] >= 0 for s in det["stock_por_sucursal"])


def test_perecedera_exige_lote_y_caducidad(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    p = _crear_pieza(client, h, codigo="PER-1", perecedera=True)

    sin_lote = _mov(client, h, p["id"], sucursal_id=suc.id, tipo="ingreso", cantidad=5)
    assert sin_lote.status_code == 422

    con_lote = _mov(client, h, p["id"], sucursal_id=suc.id, tipo="ingreso", cantidad=5,
                    lote="L-2411", fecha_caducidad="2035-01-01")
    assert con_lote.status_code == 201
    lotes = client.get(f"/piezas/{p['id']}/lotes", headers=h).json()
    assert len(lotes) == 1 and lotes[0]["cantidad"] == 5


def test_fefo_descuenta_del_lote_que_vence_antes(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    p = _crear_pieza(client, h, codigo="FEFO-1", perecedera=True)
    _mov(client, h, p["id"], sucursal_id=suc.id, tipo="ingreso", cantidad=4, lote="VIEJO", fecha_caducidad="2035-01-01")
    _mov(client, h, p["id"], sucursal_id=suc.id, tipo="ingreso", cantidad=4, lote="NUEVO", fecha_caducidad="2036-01-01")

    _mov(client, h, p["id"], sucursal_id=suc.id, tipo="consumo_ot", cantidad=5)

    lotes = {l["numero_lote"]: l["cantidad"] for l in client.get(f"/piezas/{p['id']}/lotes", headers=h).json()}
    assert lotes["VIEJO"] == 0
    assert lotes["NUEVO"] == 3


def test_alerta_caducidad_proxima(client, gerente, auth_header, suc):
    from datetime import date, timedelta

    h = auth_header(gerente)
    p = _crear_pieza(client, h, codigo="CAD-1", perecedera=True)
    pronto = (date.today() + timedelta(days=10)).isoformat()
    _mov(client, h, p["id"], sucursal_id=suc.id, tipo="ingreso", cantidad=3, lote="X", fecha_caducidad=pronto)

    alertas = client.get("/alertas-stock", params={"tipo": "caducidad_proxima"}, headers=h).json()
    assert any(str(p["id"]) == a["ref"] for a in alertas)
