"""Feature 004 — transferencias entre sucursales: envío, recepción (completa /
parcial con discrepancia / idempotente), cancelación reversible."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def suc_a(db, factory):
    return factory.sucursal("Sucursal A 004")


@pytest.fixture
def suc_b(db, factory):
    return factory.sucursal("Sucursal B 004")


@pytest.fixture
def gerente(db, factory, suc_a, suc_b):
    return factory.usuario(roles=[factory.gerencia()], sucursales=[suc_a, suc_b])


def _reloj(client, h, suc_id, serie, **over):
    ficha = {"numero_serie": serie, "marca": "Omega", "referencia": "Seamaster",
             "estado_producto": "nuevo", "motivo_alta_manual": "carga de prueba", "precio_venta": 5000, "sucursal_actual_id": suc_id, **over}
    r = client.post("/relojes", data={"data": json.dumps(ficha)}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _pieza(client, h, codigo="P-004"):
    r = client.post("/piezas", json={"codigo": codigo, "descripcion": "Corona", "tipo": "original", "stock_minimo": 1}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _stock(client, h, pid):
    r = client.get("/piezas", params={"q": ""}, headers=h).json()
    return next(p["stock_total"] for p in r["items"] if p["id"] == pid)


def test_origen_igual_destino_rechazado(client, gerente, auth_header, suc_a):
    h = auth_header(gerente)
    r = client.post("/transferencias", json={
        "sucursal_origen_id": suc_a.id, "sucursal_destino_id": suc_a.id,
        "motivo": "prueba", "lineas": [{"item_tipo": "reloj", "reloj_id": 1}],
    }, headers=h)
    assert r.status_code == 422


def test_enviar_pone_reloj_en_transito_y_descuenta_pieza(client, gerente, auth_header, suc_a, suc_b):
    h = auth_header(gerente)
    rid = _reloj(client, h, suc_a.id, "SM-A-1")
    pid = _pieza(client, h)
    client.post(f"/piezas/{pid}/movimientos", json={"sucursal_id": suc_a.id, "tipo": "ingreso", "cantidad": 5}, headers=h)

    tr = client.post("/transferencias", json={
        "sucursal_origen_id": suc_a.id, "sucursal_destino_id": suc_b.id, "motivo": "balanceo de stock",
        "lineas": [{"item_tipo": "reloj", "reloj_id": rid}, {"item_tipo": "pieza", "pieza_id": pid, "cantidad_enviada": 3}],
    }, headers=h).json()
    assert tr["estado"] == "en_preparacion"

    env = client.post(f"/transferencias/{tr['id']}/enviar", json={}, headers=h)
    assert env.status_code == 200, env.text
    assert env.json()["estado"] == "en_transito"

    # reloj en tránsito: no aparece en disponibles de A
    disp = client.get("/relojes", params={"sucursal_id": suc_a.id, "disponibilidad": "disponible"}, headers=h).json()
    assert "SM-A-1" not in {x["numero_serie"] for x in disp["items"]}
    assert client.get("/relojes/SM-A-1", headers=h).json()["disponibilidad"] == "en_transito"
    # stock de la pieza descontado de A (salió, no cuenta para nadie)
    assert _stock(client, h, pid) == 2


def test_recibir_completa_mueve_inventario_en_ambas(client, gerente, auth_header, suc_a, suc_b):
    h = auth_header(gerente)
    rid = _reloj(client, h, suc_a.id, "SM-A-2")
    pid = _pieza(client, h, "P-004b")
    client.post(f"/piezas/{pid}/movimientos", json={"sucursal_id": suc_a.id, "tipo": "ingreso", "cantidad": 4}, headers=h)

    tr = client.post("/transferencias", json={
        "sucursal_origen_id": suc_a.id, "sucursal_destino_id": suc_b.id, "motivo": "reubicación",
        "lineas": [{"item_tipo": "reloj", "reloj_id": rid}, {"item_tipo": "pieza", "pieza_id": pid, "cantidad_enviada": 4}],
        "enviar_ahora": True,
    }, headers=h).json()
    assert tr["estado"] == "en_transito"

    rec = client.post(f"/transferencias/{tr['id']}/recibir", json={
        "lineas": [
            {"linea_transferencia_id": tr["lineas"][0]["id"], "cantidad_recibida": 1},
            {"linea_transferencia_id": tr["lineas"][1]["id"], "cantidad_recibida": 4},
        ],
    }, headers=h)
    assert rec.status_code == 200, rec.text
    assert rec.json()["estado"] == "recibida"

    r = client.get("/relojes/SM-A-2", headers=h).json()
    assert r["sucursal_actual_id"] == suc_b.id
    assert r["disponibilidad"] == "disponible"
    hist = client.get("/relojes/SM-A-2/historial", headers=h).json()
    assert any(e["tipo"] == "transferencia" for e in hist)

    det = client.get(f"/piezas/{pid}", headers=h).json()
    por_suc = {s["sucursal_id"]: s["stock_actual"] for s in det["stock_por_sucursal"]}
    assert por_suc.get(suc_a.id, 0) == 0
    assert por_suc.get(suc_b.id, 0) == 4


def test_recepcion_parcial_genera_discrepancia(client, gerente, auth_header, suc_a, suc_b):
    h = auth_header(gerente)
    pid = _pieza(client, h, "P-004c")
    client.post(f"/piezas/{pid}/movimientos", json={"sucursal_id": suc_a.id, "tipo": "ingreso", "cantidad": 5}, headers=h)
    tr = client.post("/transferencias", json={
        "sucursal_origen_id": suc_a.id, "sucursal_destino_id": suc_b.id, "motivo": "envío",
        "lineas": [{"item_tipo": "pieza", "pieza_id": pid, "cantidad_enviada": 3}], "enviar_ahora": True,
    }, headers=h).json()

    rec = client.post(f"/transferencias/{tr['id']}/recibir", json={
        "lineas": [{"linea_transferencia_id": tr["lineas"][0]["id"], "cantidad_recibida": 2}],
    }, headers=h).json()
    assert rec["estado"] == "parcial"
    assert rec["tiene_discrepancias"] is True

    disc = client.get(f"/transferencias/{tr['id']}/discrepancias", headers=h).json()
    assert disc[0]["cantidad_faltante"] == 1
    assert disc[0]["accion_merma"]["causa"] == "dano_transito"


def test_doble_recepcion_idempotente(client, gerente, auth_header, suc_a, suc_b):
    h = auth_header(gerente)
    rid = _reloj(client, h, suc_a.id, "SM-A-3")
    _r = client.post("/transferencias", json={
        "sucursal_origen_id": suc_a.id, "sucursal_destino_id": suc_b.id, "motivo": "ajuste operativo",
        "lineas": [{"item_tipo": "reloj", "reloj_id": rid}], "enviar_ahora": True,
    }, headers=h)
    assert _r.status_code == 201, _r.text
    tr = _r.json()
    body = {"lineas": [{"linea_transferencia_id": tr["lineas"][0]["id"], "cantidad_recibida": 1}]}
    assert client.post(f"/transferencias/{tr['id']}/recibir", json=body, headers=h).status_code == 200
    assert client.post(f"/transferencias/{tr['id']}/recibir", json=body, headers=h).status_code == 409


def test_cancelar_devuelve_items_a_origen(client, gerente, auth_header, suc_a, suc_b):
    h = auth_header(gerente)
    rid = _reloj(client, h, suc_a.id, "SM-A-4")
    pid = _pieza(client, h, "P-004d")
    client.post(f"/piezas/{pid}/movimientos", json={"sucursal_id": suc_a.id, "tipo": "ingreso", "cantidad": 6}, headers=h)
    tr = client.post("/transferencias", json={
        "sucursal_origen_id": suc_a.id, "sucursal_destino_id": suc_b.id, "motivo": "reubicación temporal",
        "lineas": [{"item_tipo": "reloj", "reloj_id": rid}, {"item_tipo": "pieza", "pieza_id": pid, "cantidad_enviada": 6}],
        "enviar_ahora": True,
    }, headers=h).json()

    can = client.post(f"/transferencias/{tr['id']}/cancelar", json={"motivo": "envío suspendido"}, headers=h)
    assert can.status_code == 200
    assert can.json()["estado"] == "cancelada"
    assert client.get("/relojes/SM-A-4", headers=h).json()["disponibilidad"] == "disponible"
    assert _stock(client, h, pid) == 6

    # ya cancelada -> 409
    assert client.post(f"/transferencias/{tr['id']}/cancelar", json={"motivo": "otra vez"}, headers=h).status_code == 409
