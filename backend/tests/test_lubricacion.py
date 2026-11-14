"""Feature 008 — Lubricación: catálogo Moebius sembrado, ficha por calibre,
registro recomendado vs. usado en la OT con marca de desviación y consumo de
insumo, y reporte operativo de desviación.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from shared.exceptions import ValidationError
from shared.guard import CurrentUser


@pytest.fixture
def jefe(db, factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def test_catalogo_moebius_sembrado(db, jefe):
    from lubricacion import service as lub

    codigos = {p.codigo for p in lub.listar_productos(db)}
    assert {"9010", "9104", "HP-1300", "9415", "9501", "9504", "8200", "8217", "8513", "8516"} <= codigos


def test_ficha_por_calibre_y_recomendado(db, jefe):
    from inventario.models import Calibre
    from lubricacion import service as lub
    from lubricacion.schemas import FichaIn, PuntoIn

    cal = Calibre(codigo="ETA 2824-2")
    db.add(cal)
    db.flush()

    with pytest.raises(Exception):
        lub.get_ficha(db, cal.id)  # NotFound

    ficha = lub.set_ficha(db, cal.id, FichaIn(
        notas_generales="Servicio estándar",
        puntos=[
            PuntoIn(nombre="Rubí de escape", producto_moebius_codigo="9415"),
            PuntoIn(nombre="Barrilete", producto_moebius_codigo="8200"),
            PuntoIn(nombre="Puente libre", producto_moebius_codigo=None),
        ],
    ), user=jefe)
    assert [p.producto_recomendado for p in ficha.puntos] == ["9415", "8200", None]

    # producto inexistente → 422
    with pytest.raises(ValidationError):
        lub.set_ficha(db, cal.id, FichaIn(puntos=[PuntoIn(nombre="x", producto_moebius_codigo="NOPE")]), user=jefe)


def test_registro_en_ot_marca_desviacion_y_consume_insumo(db, factory, jefe):
    from inventario.models import Calibre, EventoSerie, Reloj
    from lubricacion import service as lub
    from lubricacion.schemas import FichaIn, PuntoIn
    from piezas import service as piezas_svc
    from piezas.schemas import MovimientoIn, PiezaIn
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import (
        AprobarPresupuestoIn,
        DiagnosticoIn,
        LubricacionIn,
        OrdenTrabajoIn,
        PresupuestoIn,
    )
    from clientes import repository as cli_repo
    from tecnicos import service as tec
    from tecnicos.schemas import CostoIn, TecnicoIn
    from datetime import date, timedelta

    suc = factory.sucursal("Lub Taller")
    # insumo Moebius 9415 como pieza perecedera con stock
    pieza = piezas_svc.crear(db, PiezaIn(codigo="MOEBIUS-9415", descripcion="Moebius 9415", tipo="original",
                                         costo_adquisicion=Decimal("12.00"), precio_venta_suelta=Decimal("30"),
                                         stock_minimo=0, unidad_medida="ml", perecedera=True), actor=jefe.id)
    piezas_svc.registrar_movimiento(db, pieza.id, MovimientoIn(
        sucursal_id=suc.id, tipo="ingreso", cantidad=10, lote="L1",
        fecha_caducidad=date.today() + timedelta(days=365)), actor=jefe.id)

    p9415 = lub.repository.producto_por_codigo(db, "9415")
    p9415.pieza_id = pieza.id
    db.flush()

    cal = Calibre(codigo="Omega 8800")
    db.add(cal)
    db.flush()
    lub.set_ficha(db, cal.id, FichaIn(puntos=[PuntoIn(nombre="Escape", producto_moebius_codigo="9415")]), user=jefe)

    reloj = Reloj(numero_serie="OM-8800-1", marca="Omega", referencia="X", calibre_id=cal.id,
                  sucursal_actual_id=suc.id, disponibilidad="disponible")
    db.add(reloj)
    db.flush()
    db.add(EventoSerie(numero_serie="OM-8800-1", reloj_id=reloj.id, tipo="venta", documento_tipo="venta", documento_id=1))
    db.flush()

    base = cli_repo.nivel_base(db)
    cliente = cli_repo.crear(db, tipo="natural", identificacion="0909090909",
                             numero_afiliado=cli_repo.siguiente_afiliado(db), nombre="C Lub",
                             telefono=None, email=None, direccion=None, fecha_nacimiento=None,
                             preferencias=None, notas=None,
                             nivel_fidelizacion_id=base.id if base else None, estado="activo")
    tecnico_u = factory.usuario(sucursales=[suc])
    t = tec.crear(db, TecnicoIn(nombre="Lub Téc", usuario_id=tecnico_u.id, sucursales=[suc.id]), actor=jefe.id)
    tec.set_costo(db, t.id, CostoIn(sueldo_mensual=Decimal("1600"), vigente_desde=date(2026, 1, 1)), user=jefe)

    ot = st.crear_ot(db, OrdenTrabajoIn(numero_serie="OM-8800-1", cliente_id=cliente.id, motivo="Mantención",
                                        tipo_reparacion="lubricacion", sucursal_id=suc.id), user=jefe)
    st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="diagnostico ok"), user=jefe)
    st.crear_presupuesto(db, ot.id, PresupuestoIn(precio_servicio=Decimal("150"), lineas=[]), user=jefe)
    st.aprobar_presupuesto(db, ot.id, AprobarPresupuestoIn(
        confirmado_por="Cliente", fecha_estimada_entrega=date.today() + timedelta(days=2)), user=jefe)

    stock_antes = piezas_svc.stock_en(db, pieza.id, suc.id)
    # usa 8200 en un punto donde se recomendaba 9415 → desviación
    reg = st.registrar_lubricacion_ot(db, ot.id, LubricacionIn(
        punto_nombre="Escape", producto_usado_codigo="8200"), user=jefe)
    assert reg.desviacion is True

    # ahora usa el recomendado (9415) → sin desviación + consume 1 de stock
    reg2 = st.registrar_lubricacion_ot(db, ot.id, LubricacionIn(
        punto_nombre="Escape", producto_usado_codigo="9415"), user=jefe)
    assert reg2.desviacion is False
    assert piezas_svc.stock_en(db, pieza.id, suc.id) == stock_antes - 1

    desv = lub.desviacion_lubricacion(db)
    assert any(d.orden_trabajo_id == ot.id and d.producto_usado == "8200" for d in desv)
