"""Feedback 2026-09-10 (2ª ronda): la OC de un reloj lleva marca/calibre/año,
el costo es opcional (lo informa el proveedor al recibir), y el distribuidor
autorizado se ata a marcas concretas."""

from __future__ import annotations

import pytest

from proveedores import repository as prov_repo
from proveedores import service as prov_service
from proveedores.models import LineaOrdenCompra
from proveedores.schemas import (
    LineaIn,
    OrdenCompraIn,
    ProveedorIn,
    ProveedorPatch,
    RecepcionIn,
    RecepcionLineaIn,
)
from shared.guard import CurrentUser
from shared.models import MarcaReloj


def _elevado(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def test_oc_reloj_con_marca_calibre_anio_y_costo_opcional(db, factory):
    suc = factory.sucursal("Dep OC")
    actor = factory.usuario(roles=[factory.gerencia()])

    prov = prov_service.crear(db, ProveedorIn(razon_social="Distribuidora X"), actor=actor.id)
    orden = prov_service.crear_orden(
        db,
        OrdenCompraIn(
            proveedor_id=prov.id, sucursal_destino_id=suc.id,
            lineas=[LineaIn(item_tipo="reloj", item_ref="126334", marca="Rolex",
                            calibre_codigo="3235", anio=2024, descripcion="esfera azul, para cliente Pérez",
                            cantidad=2)],  # sin costo_unitario
        ),
        actor=actor.id,
    )
    linea = orden.lineas[0]
    assert linea.marca == "Rolex" and linea.calibre_codigo == "3235" and linea.anio == 2024
    assert linea.costo_unitario is None
    assert orden.importe_a_pagar == 0  # estimado, sin costo aún

    o = prov_repo.obtener_orden(db, orden.id)
    prov_service.emitir_orden(db, o.id, actor=actor.id)
    prov_service.confirmar_orden(db, o.id, user=_elevado(factory))
    lid = db.query(LineaOrdenCompra).filter_by(orden_compra_id=o.id).first().id

    recibida = prov_service.registrar_recepcion(
        db, o.id,
        RecepcionIn(fecha_real=__import__("datetime").date(2030, 1, 2),
                    lineas=[RecepcionLineaIn(linea_orden_compra_id=lid, cantidad_recibida=2, costo_unitario=8100)]),
        actor=actor.id,
    )
    assert recibida.importe_a_pagar == 8100 * 2  # recomputado con el costo real
    assert recibida.lineas[0].costo_unitario_real == 8100


def test_distribuidor_autorizado_por_marca(db, factory):
    actor = factory.usuario(roles=[factory.gerencia()])
    m1 = MarcaReloj(nombre="Omega")
    m2 = MarcaReloj(nombre="Longines")
    db.add_all([m1, m2])
    db.flush()

    prov = prov_service.crear(
        db,
        ProveedorIn(razon_social="Swatch Group EC", certificacion_autorizada=True,
                    marcas_autorizadas=[m1.id, m2.id]),
        actor=actor.id,
    )
    assert set(prov.marcas_autorizadas) == {m1.id, m2.id}
    assert set(prov.marcas_autorizadas_nombres) == {"Omega", "Longines"}

    # al desmarcar la certificación se limpian las marcas
    prov2 = prov_service.actualizar(
        db, prov.id, ProveedorPatch(certificacion_autorizada=False), user=_elevado(factory)
    )
    assert prov2.marcas_autorizadas == []
