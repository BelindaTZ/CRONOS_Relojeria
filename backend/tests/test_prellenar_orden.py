"""Prellenado de orden (US7): devuelve borrador con proveedor/ítem/cantidad;
ítem sin proveedor habitual → pide elegir."""

from __future__ import annotations

from proveedores import service
from proveedores.schemas import LineaIn, OrdenCompraIn, PrellenarIn, ProveedorIn


def test_prellenar_con_proveedor_explicito(db, factory):
    actor = factory.usuario().id
    pid = service.crear(db, ProveedorIn(razon_social="Hab"), actor=actor).id
    out = service.prellenar_orden(
        db, PrellenarIn(proveedor_id=pid, item_tipo="pieza", item_ref="9010", cantidad_sugerida=10)
    )
    assert out.proveedor_id == pid
    assert out.requiere_elegir_proveedor is False
    assert out.lineas[0].item_ref == "9010"
    assert out.lineas[0].cantidad == 10


def test_prellenar_resuelve_proveedor_habitual_por_historial(db, factory):
    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(db, ProveedorIn(razon_social="Hab2"), actor=actor).id
    service.crear_orden(
        db, OrdenCompraIn(proveedor_id=pid, sucursal_destino_id=sid,
                          lineas=[LineaIn(item_tipo="pieza", item_ref="7777", cantidad=1, costo_unitario=5)]),
        actor=actor,
    )
    out = service.prellenar_orden(db, PrellenarIn(item_tipo="pieza", item_ref="7777", cantidad_sugerida=3))
    assert out.proveedor_id == pid
    assert out.requiere_elegir_proveedor is False


def test_prellenar_item_sin_proveedor_pide_elegir(db, factory):
    out = service.prellenar_orden(
        db, PrellenarIn(item_tipo="pieza", item_ref="SIN-HISTORIAL-XYZ", cantidad_sugerida=1)
    )
    assert out.proveedor_id is None
    assert out.requiere_elegir_proveedor is True
