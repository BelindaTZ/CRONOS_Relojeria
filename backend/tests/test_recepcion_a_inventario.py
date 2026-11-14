"""Feature 003 — el receptor de recepción de compra (002) sube stock de piezas
y deja las líneas de reloj como 'pendientes de fichar'."""

from __future__ import annotations

from datetime import date

import pytest

from inventario import service as inv_service
from piezas import repository as piezas_repo
from piezas import service as piezas_service
from proveedores import repository as prov_repo
from proveedores import service as prov_service
from proveedores.models import LineaOrdenCompra
from proveedores.schemas import LineaIn, OrdenCompraIn, ProveedorIn, RecepcionIn, RecepcionLineaIn
from shared.guard import CurrentUser


def _elevado(factory, db):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


@pytest.fixture(autouse=True)
def _wire():
    prov_service._RECEPTORES_INVENTARIO.clear()
    prov_service.registrar_receptor_inventario(piezas_service.recibir_de_compra)
    yield
    prov_service._RECEPTORES_INVENTARIO.clear()


def test_recepcion_sube_stock_de_piezas_y_deja_relojes_pendientes(db, factory):
    suc = factory.sucursal("Dep 003")
    actor = factory.usuario(roles=[factory.gerencia()])
    user = _elevado(factory, db)

    prov = prov_service.crear(db, ProveedorIn(razon_social="ETA Recambios", email="eta@x.com"), actor=actor.id)

    orden = prov_service.crear_orden(
        db,
        OrdenCompraIn(
            proveedor_id=prov.id, sucursal_destino_id=suc.id, fecha_pactada=date(2030, 1, 1),
            lineas=[
                LineaIn(item_tipo="pieza", item_ref="INS-777", descripcion="Junta", cantidad=15, costo_unitario=3),
                LineaIn(item_tipo="reloj", item_ref="Ref-X", cantidad=2, costo_unitario=1000),
            ],
        ),
        actor=actor.id,
    )
    o = prov_repo.obtener_orden(db, orden.id)
    prov_service.emitir_orden(db, o.id, actor=actor.id)
    prov_service.confirmar_orden(db, o.id, user=user)

    lineas = {l.item_tipo: l.id for l in db.query(LineaOrdenCompra).filter_by(orden_compra_id=o.id)}
    prov_service.registrar_recepcion(
        db, o.id,
        RecepcionIn(
            fecha_real=date(2030, 1, 2),
            lineas=[
                RecepcionLineaIn(linea_orden_compra_id=lineas["pieza"], cantidad_recibida=15),
                RecepcionLineaIn(linea_orden_compra_id=lineas["reloj"], cantidad_recibida=2),
            ],
        ),
        actor=actor.id,
    )

    pieza = piezas_repo.por_codigo(db, "INS-777")
    assert pieza is not None
    total = sum(s.stock_actual for s in piezas_repo.stock_por_sucursal(db, pieza.id))
    assert total == 15

    pendientes = inv_service.lineas_recepcion_pendientes(db)
    ref_x = [p for p in pendientes if p.item_ref == "Ref-X"]
    assert ref_x and ref_x[0].pendientes == 2
