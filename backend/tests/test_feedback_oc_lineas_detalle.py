"""Feedback 2026-09-10 (3ª ronda): detalle completo de las líneas de la OC.

- Pieza: elegir del catálogo (hereda datos) o crear "pieza nueva" con tipo /
  unidad de medida / marca compatible; la recepción la da de alta y sube stock.
- `observaciones` libres, independientes de la descripción.
- Recepción registra N.º de factura del proveedor y el costo real.
- `ultimo_precio` devuelve el último costo conocido (real o estimado).
"""

from __future__ import annotations

from datetime import date

import pytest

from piezas import repository as piezas_repo
from piezas import service as piezas_service
from proveedores import repository as prov_repo
from proveedores import service as prov_service
from proveedores.models import LineaOrdenCompra
from proveedores.schemas import (
    LineaIn,
    OrdenCompraIn,
    ProveedorIn,
    RecepcionIn,
    RecepcionLineaIn,
)
from shared.guard import CurrentUser


def _elevado(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"],
                       rol_ids=[], sucursal_ids=[])


@pytest.fixture(autouse=True)
def _wire():
    prov_service._RECEPTORES_INVENTARIO.clear()
    prov_service.registrar_receptor_inventario(piezas_service.recibir_de_compra)
    yield
    prov_service._RECEPTORES_INVENTARIO.clear()


def _linea_ids(db, oid):
    return {l.item_ref: l.id for l in db.query(LineaOrdenCompra).filter_by(orden_compra_id=oid)}


def test_pieza_nueva_en_la_oc_se_da_de_alta_al_recibir(db, factory):
    suc = factory.sucursal("Dep piezas nuevas")
    actor = factory.usuario(roles=[factory.gerencia()])
    prov = prov_service.crear(db, ProveedorIn(razon_social="Recambios NN"), actor=actor.id)

    orden = prov_service.crear_orden(
        db,
        OrdenCompraIn(
            proveedor_id=prov.id, sucursal_destino_id=suc.id,
            lineas=[LineaIn(
                item_tipo="pieza", item_ref="COR-ROLEX-29",
                descripcion="Corona Rolex 29 mm", pieza_tipo="no_original_equivalente",
                unidad_medida="unidad", marca_compatible="Rolex, Tudor",
                observaciones="urgente para OT", cantidad=6, costo_unitario=12,
            )],
        ),
        actor=actor.id,
    )
    linea = orden.lineas[0]
    assert linea.observaciones == "urgente para OT"
    assert linea.unidad_medida == "unidad" and linea.marca_compatible == "Rolex, Tudor"

    o = prov_repo.obtener_orden(db, orden.id)
    prov_service.emitir_orden(db, o.id, actor=actor.id)
    prov_service.confirmar_orden(db, o.id, user=_elevado(factory))
    lid = _linea_ids(db, o.id)["COR-ROLEX-29"]

    prov_service.registrar_recepcion(
        db, o.id,
        RecepcionIn(
            fecha_real=date(2030, 3, 1), numero_factura="001-002-000045",
            lineas=[RecepcionLineaIn(linea_orden_compra_id=lid, cantidad_recibida=6, costo_unitario=13)],
        ),
        actor=actor.id,
    )

    p = piezas_repo.por_codigo(db, "COR-ROLEX-29")
    assert p is not None
    assert p.tipo == "no_original_equivalente"
    assert p.marca_compatible == "Rolex, Tudor"
    assert p.descripcion == "Corona Rolex 29 mm"
    total = sum(s.stock_actual for s in piezas_repo.stock_por_sucursal(db, p.id))
    assert total == 6

    # la factura quedó en la orden
    recargada = prov_service._orden_out(db, prov_repo.obtener_orden(db, o.id))
    assert recargada.numero_factura == "001-002-000045"


def test_pieza_del_catalogo_hereda_datos_y_ultimo_precio(db, factory):
    suc = factory.sucursal("Dep catálogo")
    actor = factory.usuario(roles=[factory.gerencia()])
    prov = prov_service.crear(db, ProveedorIn(razon_social="Catalogo SA"), actor=actor.id)

    p = piezas_repo.crear(
        db, codigo="ACEITE-9010", descripcion="Aceite 9010", tipo="original",
        unidad_medida="ml", marca_compatible="universal", perecedera=False,
    )
    db.flush()

    orden = prov_service.crear_orden(
        db,
        OrdenCompraIn(
            proveedor_id=prov.id, sucursal_destino_id=suc.id,
            lineas=[LineaIn(item_tipo="pieza", item_ref="ACEITE-9010", pieza_id=p.id,
                            cantidad=3, costo_unitario=40)],
        ),
        actor=actor.id,
    )
    linea = orden.lineas[0]
    assert linea.item_ref == "ACEITE-9010"
    assert linea.unidad_medida == "ml"

    # último precio conocido: el estimado de esta orden
    up = prov_service.ultimo_precio(db, item_tipo="pieza", marca=None, referencia=None, pieza_id=p.id)
    assert up.costo == 40 and up.fuente == "orden"

    o = prov_repo.obtener_orden(db, orden.id)
    prov_service.emitir_orden(db, o.id, actor=actor.id)
    prov_service.confirmar_orden(db, o.id, user=_elevado(factory))
    lid = _linea_ids(db, o.id)["ACEITE-9010"]
    prov_service.registrar_recepcion(
        db, o.id,
        RecepcionIn(fecha_real=date(2030, 3, 2),
                    lineas=[RecepcionLineaIn(linea_orden_compra_id=lid, cantidad_recibida=3, costo_unitario=44)]),
        actor=actor.id,
    )

    # ahora el último precio es el real de la recepción
    up2 = prov_service.ultimo_precio(db, item_tipo="pieza", marca=None, referencia=None, pieza_id=p.id)
    assert up2.costo == 44 and up2.fuente == "recepcion"
