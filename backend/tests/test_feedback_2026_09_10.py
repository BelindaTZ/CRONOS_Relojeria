"""Ajustes del feedback del usuario (2026-09-10):
- alta de reloj exige recepción o motivo de alta manual;
- marca/materiales/color se resuelven contra catálogo (busca-o-crea);
- auditoría devuelve nombre + identificación del actor y la IP de origen;
- URL de objeto pública usa el endpoint del navegador, no el interno."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def suc(db, factory):
    return factory.sucursal("Matriz feedback")


@pytest.fixture
def gerente(db, factory, suc):
    return factory.usuario(roles=[factory.gerencia()], sucursales=[suc])


def _ficha(suc_id, **over):
    base = {
        "numero_serie": over.pop("numero_serie", "FB-1"),
        "marca": "Longines",
        "referencia": "L2.828",
        "estado_producto": "nuevo",
        "precio_venta": 2200,
        "sucursal_actual_id": suc_id,
    }
    base.update(over)
    return base


def test_alta_sin_orden_exige_motivo(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    r = client.post("/relojes", data={"data": json.dumps(_ficha(suc.id))}, headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["field"] == "motivo_alta_manual"

    ok = client.post(
        "/relojes",
        data={"data": json.dumps(_ficha(suc.id, motivo_alta_manual="inventario inicial"))},
        headers=h,
    )
    assert ok.status_code == 201, ok.text


def test_marca_material_color_se_resuelven_a_catalogo(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    r = client.post(
        "/relojes",
        data={"data": json.dumps(_ficha(
            suc.id, numero_serie="FB-2", motivo_alta_manual="carga inicial",
            marca="Grand Seiko", material_caja="Titanio", color_esfera="Azul hielo",
        ))},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["marca"] == "Grand Seiko"
    assert body["marca_id"] is not None
    assert body["material_caja"] == "Titanio" and body["material_caja_id"] is not None
    assert body["color_esfera"] == "Azul hielo" and body["color_esfera_id"] is not None

    # el catálogo quedó poblado y es reutilizable
    marcas = {m["nombre"] for m in client.get("/catalogos/marca-reloj", headers=h).json()}
    assert "Grand Seiko" in marcas

    # una segunda unidad con la misma marca reutiliza el mismo id
    r2 = client.post(
        "/relojes",
        data={"data": json.dumps(_ficha(suc.id, numero_serie="FB-3", motivo_alta_manual="x", marca="Grand Seiko"))},
        headers=h,
    )
    assert r2.json()["marca_id"] == body["marca_id"]


def test_auditoria_trae_nombre_identificacion_e_ip(client, gerente, auth_header, suc):
    h = auth_header(gerente)
    client.post(
        "/relojes",
        data={"data": json.dumps(_ficha(suc.id, numero_serie="FB-4", motivo_alta_manual="x"))},
        headers=h,
    )
    aud = client.get("/auditoria", params={"entidad": "reloj"}, headers=h).json()
    assert aud["items"], aud
    item = aud["items"][0]
    assert item["actor_nombre"] == gerente.nombre
    assert item["actor_identificacion"] == gerente.identificacion
    # el TestClient viaja como testclient / 127.0.0.1
    assert item["ip_origen"] is not None


def test_url_publica_usa_endpoint_del_navegador():
    from shared.storage import get_object_url

    url = get_object_url("reloj-imagenes", "reloj/ABC/1.jpg")
    assert "minio:9000" not in url
    assert url.startswith("http")
