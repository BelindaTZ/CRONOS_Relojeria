"""Feature 010 — contabilidad: partida doble (Const. Ppio IX, cobertura obligatoria),
caja/arqueo, aging de CxC/CxP, protesto de cheque, gastos pagado/por-pagar,
gastos recurrentes, motor de asiento automático y rentabilidad por sucursal.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from shared.exceptions import ConflictError, ValidationError
from shared.guard import CurrentUser


# --------------------------------------------------------------- mundo de prueba
@pytest.fixture
def mundo(db, factory):
    from clientes import repository as cli_repo
    from inventario.models import Reloj
    from piezas import service as piezas_svc
    from piezas.schemas import PiezaIn

    suc = factory.sucursal("Sucursal 010")
    gg_u = factory.usuario(roles=[factory.gerencia()], sucursales=[suc])
    gg = CurrentUser(id=gg_u.id, identificacion=gg_u.identificacion, nombre=gg_u.nombre, email=gg_u.email,
                     estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[suc.id])
    gs_u = factory.usuario(sucursales=[suc])
    gs = CurrentUser(id=gs_u.id, identificacion=gs_u.identificacion, nombre=gs_u.nombre, email=gs_u.email,
                     estado="activo", token_scope="full", roles=["Gerente de Sucursal"], rol_ids=[], sucursal_ids=[suc.id])
    ct_u = factory.usuario(sucursales=[suc])
    contador = CurrentUser(id=ct_u.id, identificacion=ct_u.identificacion, nombre=ct_u.nombre, email=ct_u.email,
                           estado="activo", token_scope="full", roles=["Contador"], rol_ids=[], sucursal_ids=[suc.id])

    reloj = Reloj(numero_serie="CTB-001", marca="Tudor", referencia="M79230N", sucursal_actual_id=suc.id,
                  disponibilidad="disponible", costo_adquisicion=Decimal("2000"), precio_venta=Decimal("3450"))
    db.add(reloj)
    db.flush()

    base = cli_repo.nivel_base(db)
    cliente = cli_repo.crear(db, tipo="natural", identificacion="0202020202",
                             numero_afiliado=cli_repo.siguiente_afiliado(db), nombre="Cliente 010",
                             telefono=None, email="c010@test.local", direccion=None, fecha_nacimiento=None,
                             preferencias=None, notas=None,
                             nivel_fidelizacion_id=base.id if base else None, estado="activo")

    from shared.models import CategoriaGasto

    cat_local = db.query(CategoriaGasto).filter_by(nombre="Arriendo").one()
    cat_personal = db.query(CategoriaGasto).filter_by(nombre="Sueldos de técnicos").one()

    return {"db": db, "suc": suc, "gg": gg, "gs": gs, "contador": contador, "cliente": cliente, "reloj": reloj,
            "cat_local": cat_local, "cat_personal": cat_personal}


def _crear_y_confirmar_venta(m, *, monto_pagado=None):
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn, PagoVentaIn, VentaIn

    db = m["db"]
    v = vs.crear_venta(db, VentaIn(cliente_id=m["cliente"].id, sucursal_id=m["suc"].id,
                                   lineas=[{"item_tipo": "reloj", "reloj_id": m["reloj"].id}]), user=m["gg"])
    if monto_pagado:
        vs.registrar_pago_venta(db, v.id, PagoVentaIn(medio_pago="efectivo", monto=Decimal(str(monto_pagado))), user=m["gg"])
    return vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=m["gg"])


# --------------------------------------------------------------- US1 (crítico)
def test_asiento_descuadrado_no_se_guarda(mundo):
    from contabilidad import service as ct

    with pytest.raises(ValidationError):
        ct.crear_asiento(mundo["db"], fecha=date.today(), glosa="prueba",
                         lineas=[{"cuenta_codigo": "1.1.01", "debe": 100, "haber": 0},
                                 {"cuenta_codigo": "4.01", "debe": 0, "haber": 90}])


def test_asiento_balanceado_se_refleja_en_mayor_y_balance(mundo):
    from contabilidad import service as ct

    db = mundo["db"]
    ct.crear_asiento(db, fecha=date.today(), glosa="Aporte de capital",
                     lineas=[{"cuenta_codigo": "1.1.01", "debe": 500, "haber": 0},
                             {"cuenta_codigo": "3.01", "debe": 0, "haber": 500}])
    mayor = ct.mayor(db, cuenta_codigo="1.1.01", periodo=None)
    assert mayor.saldo == Decimal("500.00")

    bal = ct.balance_comprobacion(db, periodo=None)
    assert bal.cuadrado and bal.total_debe == bal.total_haber


def test_venta_confirmada_genera_asiento_automatico(mundo):
    from contabilidad import repository as ct_repo

    v = _crear_y_confirmar_venta(mundo, monto_pagado=3450)
    filas, total = ct_repo.buscar_asientos(mundo["db"], origen="venta", desde=None, hasta=None, offset=0, limit=10)
    assert total >= 1
    asiento = filas[0]
    td = sum(l.debe for l in asiento.lineas)
    th = sum(l.haber for l in asiento.lineas)
    assert td == th


# --------------------------------------------------------------- US2 caja
def test_apertura_movimiento_cierre_con_diferencia(mundo):
    from contabilidad import caja as ct_caja
    from contabilidad.schemas import CerrarCajaIn, MovimientoCajaIn

    db = mundo["db"]
    ct_caja.abrir_sesion(db, mundo["suc"].id, saldo_inicial=Decimal("100"), user=mundo["gg"])
    ct_caja.registrar_movimiento(db, mundo["suc"].id, MovimientoCajaIn(tipo="entrada", monto=Decimal("50")), user=mundo["gg"])
    ct_caja.registrar_movimiento(db, mundo["suc"].id, MovimientoCajaIn(tipo="salida", monto=Decimal("20")), user=mundo["gg"])
    # esperado = 100 + 50 - 20 = 130; contado 125 -> diferencia -5
    s = ct_caja.cerrar_sesion(db, mundo["suc"].id, CerrarCajaIn(efectivo_contado=Decimal("125")), user=mundo["gg"])
    assert s.efectivo_esperado == Decimal("130.00")
    assert s.diferencia == Decimal("-5.00")
    assert s.estado == "cerrada"


def test_movimiento_sin_sesion_abierta_409(mundo):
    from contabilidad import caja as ct_caja
    from contabilidad.schemas import MovimientoCajaIn

    with pytest.raises(ConflictError):
        ct_caja.registrar_movimiento(mundo["db"], mundo["suc"].id, MovimientoCajaIn(tipo="entrada", monto=Decimal("10")), user=mundo["gg"])


# --------------------------------------------------------------- US3 CxC (crítico)
def test_cxc_saldo_exacto_y_cobro_parcial_con_aging(mundo):
    from contabilidad import service as ct
    from contabilidad.schemas import CobroCxcIn

    db = mundo["db"]
    v = _crear_y_confirmar_venta(mundo, monto_pagado=1000)  # saldo 2450
    cxc = [c for c in ct.listar_cxc(db, cliente_id=mundo["cliente"].id, estado="pendiente") if c.origen_id == v.id]
    assert len(cxc) == 1 and cxc[0].saldo == Decimal("2450.00")

    actualizada = ct.registrar_cobro_cxc(db, cxc[0].id, CobroCxcIn(monto=Decimal("450"), medio_pago="transferencia"), user=mundo["gg"])
    assert actualizada.saldo == Decimal("2000.00") and actualizada.estado == "pendiente"

    aging = ct.aging_cxc(db)
    assert aging.total >= Decimal("2000.00")
    assert any(t.tramo == "0-30" for t in aging.tramos)


# --------------------------------------------------------------- US4 CxP (crítico)
def test_cxp_de_compra_y_de_gasto_comparten_aging_y_pago(mundo):
    from contabilidad import service as ct
    from contabilidad.schemas import PagoCxpIn
    from proveedores import repository as prov_repo
    from proveedores import service as prov_service
    from proveedores.models import LineaOrdenCompra
    from proveedores.schemas import LineaIn, OrdenCompraIn, ProveedorIn, RecepcionIn, RecepcionLineaIn

    db = mundo["db"]
    prov_service._RECEPTORES_CXP.clear()
    prov_service.registrar_receptor_cxp(ct.recibir_compra_cxp)

    prov = prov_service.crear(db, ProveedorIn(razon_social="Insumos ETA", email="eta@x.com"), actor=mundo["gg"].id)
    orden = prov_service.crear_orden(
        db, OrdenCompraIn(proveedor_id=prov.id, sucursal_destino_id=mundo["suc"].id, fecha_pactada=date.today(),
                          lineas=[LineaIn(item_tipo="pieza", item_ref="INS-CT1", descripcion="Correa", cantidad=5, costo_unitario=10)]),
        actor=mundo["gg"].id,
    )
    o = prov_repo.obtener_orden(db, orden.id)
    prov_service.emitir_orden(db, o.id, actor=mundo["gg"].id)
    prov_service.confirmar_orden(db, o.id, user=mundo["gg"])
    linea_id = db.query(LineaOrdenCompra).filter_by(orden_compra_id=o.id).first().id
    prov_service.registrar_recepcion(
        db, o.id, RecepcionIn(fecha_real=date.today(), lineas=[RecepcionLineaIn(linea_orden_compra_id=linea_id, cantidad_recibida=5)]),
        actor=mundo["gg"].id,
    )
    prov_service._RECEPTORES_CXP.clear()

    cxp_compra = ct.listar_cxp(db, proveedor_id=prov.id, beneficiario_id=None, origen_tipo="orden_compra", estado=None)
    assert len(cxp_compra) == 1 and cxp_compra[0].saldo == Decimal("50.00")

    # invariante: exactamente una contraparte (proveedor xor beneficiario) por CxP
    from contabilidad import repository as ct_repo
    import sqlalchemy.exc

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        ct_repo.crear_cxp(db, origen_tipo="orden_compra", orden_compra_id=o.id, gasto_id=None,
                          proveedor_id=None, beneficiario_id=None, monto_original=10, saldo=10, estado="pendiente")
        db.flush()
    db.rollback()


def test_pago_cxp_con_retencion_reduce_saldo(mundo):
    from contabilidad import repository as ct_repo
    from contabilidad import service as ct
    from contabilidad.schemas import PagoCxpIn, RetencionIn

    db = mundo["db"]
    ben = ct.crear_beneficiario(db, _Obj(nombre="EMAPA", identificacion=None, tipo_servicio="agua"), actor=mundo["gg"].id)
    gasto = ct_repo.crear_gasto(db, sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_local"].id,
                                monto=Decimal("200"), fecha=date.today(), descripcion="Agua", estado_pago="por_pagar",
                                estado="confirmado", beneficiario_id=ben["id"])
    cxp = ct_repo.crear_cxp(db, origen_tipo="gasto", orden_compra_id=None, gasto_id=gasto.id,
                            proveedor_id=None, beneficiario_id=ben["id"], monto_original=Decimal("200"),
                            saldo=Decimal("200"), estado="pendiente")
    db.flush()
    out = ct.registrar_pago_cxp(db, cxp.id, PagoCxpIn(monto=Decimal("200"), medio_pago="efectivo",
                                                      retencion=RetencionIn(porcentaje=Decimal("2"), monto=Decimal("4"))),
                                user=mundo["gg"])
    assert out.saldo == Decimal("0.00") and out.estado == "saldada"


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# --------------------------------------------------------------- US5 gastos (crítico)
def test_gasto_sin_categoria_valida_422(mundo):
    from contabilidad import gastos as ct_gastos

    with pytest.raises(ValidationError):
        ct_gastos.registrar_gasto(mundo["db"], _Obj(
            sucursal_id=mundo["suc"].id, categoria_gasto_id=999999, monto=Decimal("50"), fecha=date.today(),
            descripcion="x", estado_pago="pagado", medio_pago="efectivo", proveedor_id=None, beneficiario_id=None,
        ), soporte=None, soporte_nombre=None, user=mundo["gg"])


def test_gasto_por_pagar_sin_contraparte_422(mundo):
    from contabilidad import gastos as ct_gastos

    with pytest.raises(ValidationError):
        ct_gastos.registrar_gasto(mundo["db"], _Obj(
            sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_local"].id, monto=Decimal("50"),
            fecha=date.today(), descripcion="agua", estado_pago="por_pagar", medio_pago=None,
            proveedor_id=None, beneficiario_id=None,
        ), soporte=None, soporte_nombre=None, user=mundo["gg"])


def test_gasto_pagado_sin_medio_422(mundo):
    from contabilidad import gastos as ct_gastos

    with pytest.raises(ValidationError):
        ct_gastos.registrar_gasto(mundo["db"], _Obj(
            sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_local"].id, monto=Decimal("50"),
            fecha=date.today(), descripcion="luz", estado_pago="pagado", medio_pago=None,
            proveedor_id=None, beneficiario_id=None,
        ), soporte=None, soporte_nombre=None, user=mundo["gg"])


def test_gerente_de_sucursal_no_registra_gastos(mundo):
    from contabilidad import gastos as ct_gastos
    from contabilidad.service import NoAutorizadoError

    with pytest.raises(NoAutorizadoError):
        ct_gastos.registrar_gasto(mundo["db"], _Obj(
            sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_local"].id, monto=Decimal("50"),
            fecha=date.today(), descripcion="arriendo", estado_pago="pagado", medio_pago="efectivo",
            proveedor_id=None, beneficiario_id=None,
        ), soporte=None, soporte_nombre=None, user=mundo["gs"])


def test_contador_registra_confirma_y_paga_como_gerencia_general(mundo):
    """Const. §3: "Contador / Administrativo — módulo contable, cuentas por cobrar/
    pagar, gastos". No es solo un rol de RBAC con acceso al módulo `contable`: el
    service también debe dejarlo pasar donde antes exigía literalmente Gerencia
    General (`puede_gestionar_contabilidad`, no `es_gerencia`)."""
    from contabilidad import gastos as ct_gastos
    from contabilidad import service as ct
    from contabilidad.schemas import PagoCxpIn, PeriodoIn

    db = mundo["db"]
    contador = mundo["contador"]

    g = ct_gastos.registrar_gasto(db, _Obj(
        sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_local"].id, monto=Decimal("80"),
        fecha=date.today(), descripcion="Papelería", estado_pago="pagado", medio_pago="efectivo",
        proveedor_id=None, beneficiario_id=None,
    ), soporte=None, soporte_nombre=None, user=contador)
    assert g.estado == "confirmado"

    ben = ct.crear_beneficiario(db, _Obj(nombre="EMAPA", identificacion=None, tipo_servicio="agua"), actor=contador.id)
    por_pagar = ct_gastos.registrar_gasto(db, _Obj(
        sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_local"].id, monto=Decimal("40"),
        fecha=date.today(), descripcion="Agua", estado_pago="por_pagar", medio_pago=None,
        proveedor_id=None, beneficiario_id=ben["id"],
    ), soporte=None, soporte_nombre=None, user=contador)
    assert por_pagar.cuenta_por_pagar_id is not None

    cxp = ct.listar_cxp(db, proveedor_id=None, beneficiario_id=ben["id"], origen_tipo="gasto", estado="pendiente")[0]
    pagado = ct.registrar_pago_cxp(db, cxp.id, PagoCxpIn(monto=Decimal("40"), medio_pago="efectivo"), user=contador)
    assert pagado.estado == "saldada"

    periodo = ct.crear_periodo(db, PeriodoIn(fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 1, 31)), user=contador)
    cerrado = ct.cerrar_periodo(db, periodo.id, user=contador)
    assert cerrado.estado == "cerrado"


def test_gasto_por_pagar_aparece_en_cxp_y_gasto_pagado_genera_movimiento_y_asiento(mundo):
    from contabilidad import caja as ct_caja
    from contabilidad import gastos as ct_gastos
    from contabilidad import service as ct

    db = mundo["db"]
    ben = ct.crear_beneficiario(db, _Obj(nombre="CNT", identificacion=None, tipo_servicio="telecom"), actor=mundo["gg"].id)
    g1 = ct_gastos.registrar_gasto(db, _Obj(
        sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_local"].id, monto=Decimal("35"),
        fecha=date.today(), descripcion="Internet", estado_pago="por_pagar", medio_pago=None,
        proveedor_id=None, beneficiario_id=ben["id"],
    ), soporte=None, soporte_nombre=None, user=mundo["gg"])
    assert g1.cuenta_por_pagar_id is not None
    cxp = ct.listar_cxp(db, proveedor_id=None, beneficiario_id=ben["id"], origen_tipo="gasto", estado=None)
    assert len(cxp) == 1 and cxp[0].saldo == Decimal("35.00")

    ct_caja.abrir_sesion(db, mundo["suc"].id, saldo_inicial=Decimal("0"), user=mundo["gg"])
    g2 = ct_gastos.registrar_gasto(db, _Obj(
        sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_personal"].id, monto=Decimal("800"),
        fecha=date.today(), descripcion="Sueldo técnico", estado_pago="pagado", medio_pago="efectivo",
        proveedor_id=None, beneficiario_id=None,
    ), soporte=None, soporte_nombre=None, user=mundo["gg"])
    assert g2.movimiento_caja_id is not None


# --------------------------------------------------------------- US5b gastos recurrentes
def test_gasto_recurrente_genera_borrador_sin_asiento_y_confirmar_lo_cierra(mundo):
    from contabilidad import gastos as ct_gastos
    from contabilidad import recurrentes as ct_rec
    from contabilidad.schemas import ConfirmarGastoIn

    db = mundo["db"]
    ben = ct_rec.repository.crear_beneficiario(db, nombre="Agua Potable Municipal", identificacion=None, tipo_servicio="agua")
    rec = ct_rec.crear(db, _Obj(
        categoria_gasto_id=mundo["cat_local"].id, sucursal_id=mundo["suc"].id, proveedor_id=None,
        beneficiario_id=ben.id, descripcion="Agua mensual", monto_estimado=Decimal("60"), frecuencia="mensual",
        proxima_generacion=date.today() - timedelta(days=1),
    ), user=mundo["gg"])

    n = ct_rec.generar_vencidos(db, hoy=date.today())
    assert n == 1
    items, total = ct_gastos.listar_gastos(db, user=mundo["gg"], sucursal_id=None, categoria_gasto_id=None,
                                           estado_pago=None, estado="borrador", desde=None, hasta=None, offset=0, limit=10)
    assert total == 1 and items[0].asiento_id is None and items[0].cuenta_por_pagar_id is None

    ct_rec.set_estado(db, rec.id, "pausado", user=mundo["gg"])
    n2 = ct_rec.generar_vencidos(db, hoy=date.today() + timedelta(days=40))
    assert n2 == 0

    confirmado = ct_gastos.confirmar_gasto(db, items[0].id, ConfirmarGastoIn(
        monto=Decimal("62"), estado_pago="por_pagar", beneficiario_id=ben.id,
    ), user=mundo["gg"])
    assert confirmado.estado == "confirmado" and confirmado.cuenta_por_pagar_id is not None


# --------------------------------------------------------------- US6 rentabilidad
def test_rentabilidad_sucursal_descuenta_gastos(mundo):
    from contabilidad import gastos as ct_gastos
    from contabilidad import service as ct

    db = mundo["db"]
    _crear_y_confirmar_venta(mundo, monto_pagado=3450)
    ct_gastos.registrar_gasto(db, _Obj(
        sucursal_id=mundo["suc"].id, categoria_gasto_id=mundo["cat_local"].id, monto=Decimal("100"),
        fecha=date.today(), descripcion="Arriendo", estado_pago="por_pagar", medio_pago=None,
        proveedor_id=None, beneficiario_id=ct.crear_beneficiario(db, _Obj(nombre="Arrendador X", identificacion=None, tipo_servicio="arriendo"), actor=mundo["gg"].id)["id"],
    ), soporte=None, soporte_nombre=None, user=mundo["gg"])

    r = ct.rentabilidad_sucursal(db, periodo=None, sucursal_id=mundo["suc"].id)
    assert len(r) == 1
    fila = r[0]
    assert fila.ingresos > 0
    assert fila.gastos_operativos == Decimal("100.00")
    assert fila.utilidad_neta == fila.ingresos - fila.costos - fila.gastos_operativos


# --------------------------------------------------------------- US7 cheques (crítico)
def test_protesto_de_cheque_revierte_cobro_y_reactiva_cxc(mundo):
    from contabilidad import service as ct
    from contabilidad.schemas import ChequeIn, CobroCxcIn

    db = mundo["db"]
    v = _crear_y_confirmar_venta(mundo)  # sin pago -> saldo completo 3450
    cxc = [c for c in ct.listar_cxc(db, cliente_id=mundo["cliente"].id, estado="pendiente") if c.origen_id == v.id][0]

    actualizada = ct.registrar_cobro_cxc(db, cxc.id, CobroCxcIn(
        monto=cxc.saldo, medio_pago="cheque",
        cheque=ChequeIn(tipo="recibido", banco="Pichincha", numero="0001", monto=cxc.saldo, fecha=date.today(),
                        cliente_id=mundo["cliente"].id, documento_origen_tipo="cobro_cxc", documento_origen_id=None),
    ), user=mundo["gg"])
    assert actualizada.estado == "saldada"

    cheque = ct.listar_cheques(db, tipo="recibido", estado="en_cartera")[0]
    # el cobro quedó vinculado al cheque; ajustamos el origen para el protesto (lo hace el propio flujo de cobro)
    from contabilidad import repository as ct_repo

    cobro = ct_repo.cobros_de_cxc(db, cxc.id)[-1]
    cheque_row = ct_repo.obtener_cheque(db, cheque["id"], for_update=True)
    cheque_row.documento_origen_id = cobro.id
    db.flush()

    ct.protestar_cheque(db, cheque["id"], user=mundo["gg"])
    reactivada = [c for c in ct.listar_cxc(db, cliente_id=mundo["cliente"].id, estado="pendiente") if c.origen_id == v.id]
    assert reactivada and reactivada[0].saldo == cxc.saldo


# --------------------------------------------------------------- cierre de periodo
def test_periodo_cerrado_exige_ajuste(mundo):
    from contabilidad import service as ct
    from contabilidad.schemas import PeriodoIn

    db = mundo["db"]
    hoy = date.today()
    p = ct.crear_periodo(db, PeriodoIn(fecha_inicio=hoy - timedelta(days=5), fecha_fin=hoy + timedelta(days=5)), user=mundo["gg"])
    ct.cerrar_periodo(db, p.id, user=mundo["gg"])

    with pytest.raises(ConflictError):
        ct.crear_asiento(db, fecha=hoy, glosa="fuera de lugar",
                         lineas=[{"cuenta_codigo": "1.1.01", "debe": 10, "haber": 0},
                                 {"cuenta_codigo": "3.01", "debe": 0, "haber": 10}])

    original = ct.crear_asiento(db, fecha=hoy - timedelta(days=40), glosa="anterior",
                                lineas=[{"cuenta_codigo": "1.1.01", "debe": 10, "haber": 0},
                                        {"cuenta_codigo": "3.01", "debe": 0, "haber": 10}])
    ajuste = ct.crear_asiento(db, fecha=hoy, glosa="ajuste del asiento anterior",
                              lineas=[{"cuenta_codigo": "1.1.01", "debe": 10, "haber": 0},
                                      {"cuenta_codigo": "3.01", "debe": 0, "haber": 10}],
                              ajuste_de_asiento_id=original.id)
    assert ajuste.ajuste_de_asiento_id == original.id
