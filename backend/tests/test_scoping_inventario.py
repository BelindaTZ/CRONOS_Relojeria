"""Feature 004 — visibilidad por sucursal del inventario (FR-008): un gerente de
sucursal solo ve su sucursal; Gerencia General ve el consolidado."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def suc_a(db, factory):
    return factory.sucursal("Local A scope")


@pytest.fixture
def suc_b(db, factory):
    return factory.sucursal("Local B scope")


@pytest.fixture
def gerencia(db, factory):
    return factory.usuario(roles=[factory.gerencia()])


@pytest.fixture
def gerente_a(db, factory, suc_a):
    rol = factory.rol("Gerente Sucursal scope")
    factory.permitir(rol, "inventario_relojes", ["consultar", "crear", "editar"])
    factory.permitir(rol, "piezas", ["consultar", "crear", "editar"])
    return factory.usuario(roles=[rol], sucursales=[suc_a])


def _reloj(client, h, suc_id, serie):
    ficha = {"numero_serie": serie, "marca": "Tudor", "referencia": "BB58",
             "estado_producto": "nuevo", "motivo_alta_manual": "carga de prueba", "precio_venta": 4000, "sucursal_actual_id": suc_id}
    assert client.post("/relojes", data={"data": json.dumps(ficha)}, headers=h).status_code == 201


def test_gerente_de_sucursal_solo_ve_su_inventario(client, gerencia, gerente_a, auth_header, suc_a, suc_b):
    hg = auth_header(gerencia)
    _reloj(client, hg, suc_a.id, "SC-A-1")
    _reloj(client, hg, suc_b.id, "SC-B-1")

    # Gerencia General: consolidado (ambas) + puede filtrar
    todos = client.get("/relojes", headers=hg).json()
    assert {"SC-A-1", "SC-B-1"} <= {x["numero_serie"] for x in todos["items"]}
    filtrado = client.get("/relojes", params={"sucursal_id": suc_b.id}, headers=hg).json()
    assert {x["numero_serie"] for x in filtrado["items"]} == {"SC-B-1"}

    # Gerente de A: solo su sucursal, aunque pida la B
    ha = auth_header(gerente_a)
    solo_a = client.get("/relojes", headers=ha).json()
    assert {x["numero_serie"] for x in solo_a["items"]} == {"SC-A-1"}
    pide_b = client.get("/relojes", params={"sucursal_id": suc_b.id}, headers=ha).json()
    assert pide_b["items"] == []

    # valor-inventario también respeta el scope
    val_a = client.get("/valor-inventario", headers=ha).json()
    assert val_a["unidades"] == 1
    val_g = client.get("/valor-inventario", headers=hg).json()
    assert val_g["unidades"] == 2


def test_scoping_piezas_por_sucursal(client, gerencia, gerente_a, auth_header, suc_a, suc_b):
    hg = auth_header(gerencia)
    pid = client.post("/piezas", json={"codigo": "SC-P1", "descripcion": "x", "tipo": "original"}, headers=hg).json()["id"]
    client.post(f"/piezas/{pid}/movimientos", json={"sucursal_id": suc_a.id, "tipo": "ingreso", "cantidad": 3}, headers=hg)
    client.post(f"/piezas/{pid}/movimientos", json={"sucursal_id": suc_b.id, "tipo": "ingreso", "cantidad": 7}, headers=hg)

    total_g = next(p["stock_total"] for p in client.get("/piezas", headers=hg).json()["items"] if p["id"] == pid)
    assert total_g == 10
    ha = auth_header(gerente_a)
    total_a = next(p["stock_total"] for p in client.get("/piezas", headers=ha).json()["items"] if p["id"] == pid)
    assert total_a == 3
