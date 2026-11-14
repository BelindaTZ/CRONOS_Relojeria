"""Feature 003 — alta de unidades, estado de inventario, restricción de costo,
corrección con rol elevado e historial inalterable por número de serie."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def suc(db, factory):
    return factory.sucursal("Matriz 003")


@pytest.fixture
def gerente(db, factory, suc):
    rol = factory.gerencia()
    return factory.usuario(roles=[rol], sucursales=[suc])


@pytest.fixture
def vendedor(db, factory, suc):
    rol = factory.rol("Vendedor 003")
    factory.permitir(rol, "inventario_relojes", ["consultar", "crear", "editar"])
    factory.permitir(rol, "piezas", ["consultar", "crear", "editar"])
    return factory.usuario(roles=[rol], sucursales=[suc])


def _alta(client, headers, suc_id, **over):
    ficha = {
        "numero_serie": over.pop("numero_serie", "OMG-001"),
        "marca": "Omega",
        "referencia": "310.30.42.50.01.001",
        "estado_producto": "nuevo", "motivo_alta_manual": "carga de prueba",
        "precio_venta": 8500,
        "sucursal_actual_id": suc_id,
        **over,
    }
    return client.post("/relojes", data={"data": json.dumps(ficha)}, headers=headers)


def test_alta_y_serie_duplicada(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    r = _alta(client, h, suc.id)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["numero_serie"] == "OMG-001"
    assert body["disponibilidad"] == "disponible"

    # historial: un evento 'ingreso'
    hist = client.get("/relojes/OMG-001/historial", headers=h).json()
    assert [e["tipo"] for e in hist] == ["ingreso"]

    # serie duplicada -> 409
    dup = _alta(client, h, suc.id)
    assert dup.status_code == 409


def test_estado_inventario_filtra_por_sucursal_y_disponibilidad(client, gerente, auth_header, factory):
    h = auth_header(gerente)
    s1 = factory.sucursal("Suc A 003")
    s2 = factory.sucursal("Suc B 003")
    _alta(client, h, s1.id, numero_serie="A-1", marca="Rolex", referencia="126610")
    _alta(client, h, s2.id, numero_serie="B-1", marca="Rolex", referencia="126610")

    r = client.get("/relojes", params={"sucursal_id": s1.id}, headers=h).json()
    series = {x["numero_serie"] for x in r["items"]}
    assert "A-1" in series and "B-1" not in series

    # búsqueda multicriterio por marca
    r2 = client.get("/relojes", params={"q": "Rolex"}, headers=h).json()
    assert r2["total"] >= 2


def test_restriccion_de_costo_por_rol(client, gerente, vendedor, auth_header, suc):
    _alta(client, auth_header(gerente), suc.id, numero_serie="COST-1", costo_adquisicion=6000)

    con = client.get("/relojes/COST-1", headers=auth_header(gerente)).json()
    assert con["costo_adquisicion"] is not None
    assert con["margen"] is not None

    sin = client.get("/relojes/COST-1", headers=auth_header(vendedor)).json()
    assert sin["costo_adquisicion"] is None
    assert sin["margen"] is None


def test_correccion_requiere_rol_elevado_y_preserva_historial(client, gerente, vendedor, auth_header, suc):
    _alta(client, auth_header(gerente), suc.id, numero_serie="FIX-1")

    rid = client.get("/relojes/FIX-1", headers=auth_header(gerente)).json()["id"]

    # rol normal -> 403
    bad = client.patch(f"/relojes/{rid}", json={"numero_serie": "FIX-2", "motivo": "tipeo en recepción"},
                       headers=auth_header(vendedor))
    assert bad.status_code == 403

    # rol elevado -> 200, evento 'correccion', historial preservado bajo la nueva serie
    ok = client.patch(f"/relojes/{rid}", json={"numero_serie": "FIX-2", "motivo": "tipeo en recepción"},
                      headers=auth_header(gerente))
    assert ok.status_code == 200, ok.text
    hist = client.get("/relojes/FIX-2/historial", headers=auth_header(gerente)).json()
    tipos = [e["tipo"] for e in hist]
    assert tipos == ["ingreso", "correccion"]
    assert client.get("/relojes/FIX-1", headers=auth_header(gerente)).status_code == 404


def test_historial_no_tiene_endpoint_de_edicion(client):
    from main import create_app

    rutas = {(m, r.path) for r in create_app().routes for m in getattr(r, "methods", set())}
    assert not any(
        path.endswith("/historial") and metodo in ("PUT", "PATCH", "DELETE")
        for metodo, path in rutas
    )
