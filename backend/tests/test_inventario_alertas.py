"""Feature 003 — alertas de stock de relojes y acción de reposición (abre 002)."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def suc(db, factory):
    return factory.sucursal("Local 003")


@pytest.fixture
def gerente(db, factory, suc):
    return factory.usuario(roles=[factory.gerencia()], sucursales=[suc])


def _alta(client, h, suc_id, serie, **over):
    ficha = {"numero_serie": serie, "marca": "Tudor", "referencia": "M79030",
             "estado_producto": "nuevo", "motivo_alta_manual": "carga de prueba", "precio_venta": 3800, "sucursal_actual_id": suc_id, **over}
    r = client.post("/relojes", data={"data": json.dumps(ficha)}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_ultima_unidad_genera_alerta_con_accion_reponer(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    _alta(client, h, suc.id, "TU-1")

    alertas = client.get("/alertas-stock", headers=h).json()
    modelo = [a for a in alertas if a["ambito"] == "modelo" and a["tipo"] == "ultima_unidad"]
    assert modelo, alertas
    accion = modelo[0]["accion_reponer"]
    assert accion is not None
    assert accion["item_tipo"] == "reloj"
    assert accion["item_ref"] == "M79030"
    assert accion["cantidad_sugerida"] >= 1


def test_superar_maximo_alerta_sin_bloquear(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    # máximo por defecto 12: creamos 13 sin que ninguna alta falle
    for i in range(13):
        _alta(client, h, suc.id, f"MX-{i}")

    alertas = client.get("/alertas-stock", params={"tipo": "cerca_maximo"}, headers=h).json()
    assert any(a["ambito"] == "modelo" for a in alertas)
