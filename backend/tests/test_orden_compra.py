"""Órdenes de compra (US2): parcial→recibida; perecedero sin lote → 422; historial."""

from __future__ import annotations

from datetime import date

import pytest

from proveedores import service
from proveedores.schemas import LineaIn, OrdenCompraIn, ProveedorIn, RecepcionIn, RecepcionLineaIn
from shared.exceptions import ConflictError, ValidationError


def _prov_y_suc(db, factory):
    actor = factory.usuario()
    suc = factory.sucursal()
    prov = service.crear(db, ProveedorIn(razon_social="Moebius"), actor=actor.id)
    return actor.id, suc.id, prov.id


def _emitir_confirmar(db, factory, oid):
    actor = factory.usuario()
    service.emitir_orden(db, oid, actor=actor.id)
    service.confirmar_orden(db, oid, user=factory.current_user(gerencia=True))


def test_recepcion_parcial_luego_total(db, factory):
    actor, sid, pid = _prov_y_suc(db, factory)
    o = service.crear_orden(
        db,
        OrdenCompraIn(
            proveedor_id=pid, sucursal_destino_id=sid, fecha_pactada=date(2026, 9, 25),
            lineas=[LineaIn(item_tipo="pieza", item_ref="9010", cantidad=5, costo_unitario=45)],
        ),
        actor=actor,
    )
    _emitir_confirmar(db, factory, o.id)
    linea_id = o.lineas[0].id

    o1 = service.registrar_recepcion(
        db, o.id, RecepcionIn(fecha_real=date(2026, 9, 27),
                              lineas=[RecepcionLineaIn(linea_orden_compra_id=linea_id, cantidad_recibida=3)]),
        actor=actor,
    )
    assert o1.estado == "parcial"
    assert o1.lineas[0].cantidad_recibida == 3

    o2 = service.registrar_recepcion(
        db, o.id, RecepcionIn(fecha_real=date(2026, 9, 28),
                              lineas=[RecepcionLineaIn(linea_orden_compra_id=linea_id, cantidad_recibida=2)]),
        actor=actor,
    )
    assert o2.estado == "recibida"


def test_recepcion_perecedero_sin_lote_es_422(db, factory):
    actor, sid, pid = _prov_y_suc(db, factory)
    o = service.crear_orden(
        db,
        OrdenCompraIn(
            proveedor_id=pid, sucursal_destino_id=sid, fecha_pactada=date(2026, 9, 25),
            lineas=[LineaIn(item_tipo="pieza", item_ref="LUB-1", cantidad=2, costo_unitario=10, es_perecedero=True)],
        ),
        actor=actor,
    )
    _emitir_confirmar(db, factory, o.id)
    with pytest.raises(ValidationError):
        service.registrar_recepcion(
            db, o.id,
            RecepcionIn(fecha_real=date(2026, 9, 26),
                        lineas=[RecepcionLineaIn(linea_orden_compra_id=o.lineas[0].id, cantidad_recibida=2)]),
            actor=actor,
        )
    # con lote + caducidad → ok
    ok = service.registrar_recepcion(
        db, o.id,
        RecepcionIn(fecha_real=date(2026, 9, 26), lineas=[RecepcionLineaIn(
            linea_orden_compra_id=o.lineas[0].id, cantidad_recibida=2, lote="L-1", fecha_caducidad=date(2027, 1, 1))]),
        actor=actor,
    )
    assert ok.estado == "recibida"


def test_no_se_recibe_orden_en_borrador(db, factory):
    actor, sid, pid = _prov_y_suc(db, factory)
    o = service.crear_orden(
        db, OrdenCompraIn(proveedor_id=pid, sucursal_destino_id=sid,
                          lineas=[LineaIn(item_tipo="pieza", item_ref="x", cantidad=1, costo_unitario=1)]),
        actor=actor,
    )
    with pytest.raises(ConflictError):
        service.registrar_recepcion(
            db, o.id, RecepcionIn(fecha_real=date.today(),
                                  lineas=[RecepcionLineaIn(linea_orden_compra_id=o.lineas[0].id, cantidad_recibida=1)]),
            actor=actor,
        )


def test_historial_de_compras_del_proveedor(db, factory):
    actor, sid, pid = _prov_y_suc(db, factory)
    for _ in range(2):
        service.crear_orden(
            db, OrdenCompraIn(proveedor_id=pid, sucursal_destino_id=sid,
                              lineas=[LineaIn(item_tipo="pieza", item_ref="9010", cantidad=1, costo_unitario=5)]),
            actor=actor,
        )
    detalle = service.obtener_detalle(db, pid)
    assert len(detalle.historial_compras) == 2
