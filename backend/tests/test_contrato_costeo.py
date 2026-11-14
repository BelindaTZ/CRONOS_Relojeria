"""Feature 005 — contrato interno de costo de mano de obra para 008 (US4).

El costo de MO nunca se filtra a una respuesta pública ni a un documento del
cliente (spec §FR-009, §SC-006).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from shared.guard import CurrentUser
from tecnicos import service as tec
from tecnicos.schemas import CostoIn, TecnicoIn


def _jefe(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def test_contrato_costo_mo_ot_forma_y_valores(client, factory, auth_header, db):
    jefe_rol = factory.gerencia()
    jefe = factory.usuario(roles=[jefe_rol])
    r = client.post("/tecnicos", json={"nombre": "Costeo"}, headers=auth_header(jefe))
    tid = r.json()["id"]
    client.post(f"/tecnicos/{tid}/costo", json={"sueldo_mensual": 1600, "vigente_desde": "2026-09-01"},
                headers=auth_header(jefe))

    r = client.post("/_internal/costeo/costo-mo-ot",
                    json={"tecnico_id": tid, "horas": 3, "tipo_reparacion": "servicio_completo"},
                    headers=auth_header(jefe))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"costo_mo", "tarifa_hora", "horas", "base"}
    assert body["costo_mo"] == "30.00" and body["tarifa_hora"] == "10.00" and body["base"] == "horas_registradas"

    r = client.post("/_internal/costeo/costo-mo-ot", json={"tecnico_id": tid}, headers=auth_header(jefe))
    assert r.json()["base"] == "tiempo_estimado" and r.json()["costo_mo"] == "20.00"


def test_costo_no_aparece_en_la_ficha_publica(client, factory, auth_header):
    jefe = factory.usuario(roles=[factory.gerencia()])
    rol_ventas = factory.rol("Vendedor")
    factory.permitir(rol_ventas, "tecnicos", ["consultar"])
    vendedor = factory.usuario(roles=[rol_ventas])

    r = client.post("/tecnicos", json={"nombre": "Oculto"}, headers=auth_header(jefe))
    tid = r.json()["id"]
    client.post(f"/tecnicos/{tid}/costo", json={"sueldo_mensual": 2000, "vigente_desde": "2026-09-01"},
                headers=auth_header(jefe))

    ficha = client.get(f"/tecnicos/{tid}", headers=auth_header(vendedor)).json()
    assert ficha["costos_visibles"] is False
    assert ficha["costo_vigente"] is None
    assert "2000" not in r.text  # el número del sueldo no viaja en la ficha
