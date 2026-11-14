"""Feature 009 — ventas: confirmación atómica, margen de la venta y margen mínimo
protegido (Const. Ppio IX, cobertura obligatoria), garantías, CxC y anulación.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from shared.exceptions import ConflictError, ValidationError
from shared.guard import CurrentUser


@pytest.fixture
def mundo(db, factory):
    from clientes import repository as cli_repo
    from inventario.models import Reloj
    from piezas import service as piezas_svc
    from piezas.schemas import MovimientoIn, PiezaIn

    suc = factory.sucursal("Tienda 009")
    admin_u = factory.usuario(roles=[factory.gerencia()], sucursales=[suc])
    admin = CurrentUser(id=admin_u.id, identificacion=admin_u.identificacion, nombre=admin_u.nombre,
                        email=admin_u.email, estado="activo", token_scope="full",
                        roles=["Gerencia General"], rol_ids=[], sucursal_ids=[suc.id])
    vendedor_u = factory.usuario(sucursales=[suc])
    vendedor = CurrentUser(id=vendedor_u.id, identificacion=vendedor_u.identificacion, nombre=vendedor_u.nombre,
                           email=vendedor_u.email, estado="activo", token_scope="full",
                           roles=["Vendedor"], rol_ids=[], sucursal_ids=[suc.id])

    reloj = Reloj(numero_serie="VEN-001", marca="Omega", referencia="311.30", sucursal_actual_id=suc.id,
                  disponibilidad="disponible", costo_adquisicion=Decimal("3000"), precio_venta=Decimal("5000"))
    reloj2 = Reloj(numero_serie="VEN-002", marca="Tudor", referencia="M79230N", sucursal_actual_id=suc.id,
                   disponibilidad="disponible", costo_adquisicion=Decimal("80"), precio_venta=Decimal("120"))
    db.add_all([reloj, reloj2])
    db.flush()

    base = cli_repo.nivel_base(db)
    cliente = cli_repo.crear(db, tipo="natural", identificacion="0101010101",
                             numero_afiliado=cli_repo.siguiente_afiliado(db), nombre="Cliente 009",
                             telefono=None, email="c009@test.local", direccion=None, fecha_nacimiento=None,
                             preferencias=None, notas=None,
                             nivel_fidelizacion_id=base.id if base else None, estado="activo")

    pieza = piezas_svc.crear(db, PiezaIn(codigo="CORREA-1", descripcion="Correa piel", tipo="original",
                                         costo_adquisicion=Decimal("40"), precio_venta_suelta=Decimal("120"),
                                         stock_minimo=0), actor=admin.id)
    piezas_svc.registrar_movimiento(db, pieza.id, MovimientoIn(sucursal_id=suc.id, tipo="ingreso", cantidad=5),
                                    actor=admin.id)

    return {"db": db, "suc": suc, "admin": admin, "vendedor": vendedor,
            "cliente": cliente, "reloj": reloj, "reloj2": reloj2, "pieza": pieza}


def _crear(m, lineas, *, cliente_id="cli", user=None):
    from ventas import service as vs
    from ventas.schemas import VentaIn

    cid = m["cliente"].id if cliente_id == "cli" else cliente_id
    return vs.crear_venta(m["db"], VentaIn(cliente_id=cid, sucursal_id=m["suc"].id, lineas=lineas),
                          user=user or m["admin"])


# --------------------------------------------------------------- US1
def test_confirmar_baja_stock_y_evento_serie(mundo):
    from inventario import repository as inv_repo
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn, PagoVentaIn

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    assert v.total == Decimal("5000.00")

    vs.registrar_pago_venta(db, v.id, PagoVentaIn(medio_pago="efectivo", monto=Decimal("2000")), user=mundo["admin"])
    vs.registrar_pago_venta(db, v.id, PagoVentaIn(medio_pago="tarjeta", monto=Decimal("3000")), user=mundo["admin"])

    d = vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["admin"])
    assert d.estado == "confirmada"
    assert d.saldo == Decimal("0.00")
    assert d.numero_factura and d.numero_factura.count("-") == 2 and d.numero_factura.endswith("000000001")

    # desglose de IVA (PVP 5000, IVA 15% incluido)
    assert d.subtotal_sin_impuestos == Decimal("4347.83")
    assert d.iva_monto == Decimal("652.17")
    assert d.total == Decimal("5000.00")

    db.refresh(mundo["reloj"])
    assert mundo["reloj"].disponibilidad == "vendido"
    assert "venta" in [e.tipo for e in inv_repo.eventos_de_serie(db, "VEN-001")]
    assert any(c["tipo"] == "comprobante" for c in d.comprobantes)


def test_reloj_en_transito_no_se_confirma(mundo):
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    mundo["reloj"].disponibilidad = "en_transito"
    db.flush()
    with pytest.raises(ConflictError):
        vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["admin"])


def test_venta_credito_genera_cxc_por_el_saldo(mundo):
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn, PagoVentaIn

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    vs.registrar_pago_venta(db, v.id, PagoVentaIn(medio_pago="efectivo", monto=Decimal("3000")), user=mundo["admin"])
    vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["admin"])

    cxc = vs.cuentas_por_cobrar(db, cliente_id=mundo["cliente"].id, estado=None)
    assert len(cxc) == 1 and cxc[0].saldo == Decimal("2000.00") and cxc[0].origen_tipo == "venta"


# --------------------------------------------------------------- US2 (crítico)
def test_margen_venta_sobre_precio_neto_de_iva(mundo):
    from ventas import service as vs

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    # PVP con IVA 15% incluido → el margen se calcula sobre el precio neto de IVA:
    # reloj: 5000/1,15 = 4347,83 − 3000 = 1347,83
    assert v.margen_venta == Decimal("1347.83")

    # oculto sin rol administrativo
    vista = vs.obtener_detalle(db, v.id, user=mundo["vendedor"])
    assert vista.margen_venta is None and vista.costos_visibles is False
    assert all(ln.costo is None for ln in vista.lineas)


def test_factura_desglosa_iva_y_descuento(mundo):
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn, PagoVentaIn

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    vs.registrar_pago_venta(db, v.id, PagoVentaIn(medio_pago="efectivo", monto=Decimal("5000")), user=mundo["admin"])
    d = vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["admin"])
    ln = d.lineas[0]
    assert ln.base_imponible == Decimal("4347.83")
    assert ln.iva_monto == Decimal("652.17")
    assert ln.tarifa_iva == Decimal("15.00")
    assert d.total_descuento == Decimal("0.00")
    # el certificado y la factura no exponen costo ni margen
    assert ln.costo is not None  # el admin sí lo ve en la ficha
    vista_vendedor = vs.obtener_detalle(db, v.id, user=mundo["vendedor"])
    assert all(x.costo is None and x.margen is None for x in vista_vendedor.lineas)


def test_desglose_iva_visible_en_borrador(mundo):
    """Feedback del usuario (2026-09-11): el desglose de IVA/descuento no se veía
    en la ficha de la venta mientras estaba en borrador (solo se grababa al
    confirmar). Debe calcularse en vivo para que el vendedor lo vea antes de
    confirmar, sin esperar a la factura."""
    from ventas import service as vs

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    assert v.estado == "borrador"
    assert v.subtotal_sin_impuestos == Decimal("4347.83")
    assert v.iva_monto == Decimal("652.17")
    assert v.iva_porcentaje == Decimal("0.15")
    assert v.total_descuento == Decimal("0.00")

    vista = vs.obtener_detalle(db, v.id, user=mundo["admin"])
    assert vista.subtotal_sin_impuestos == Decimal("4347.83")
    assert vista.iva_monto == Decimal("652.17")


def test_descuento_y_cupon_juntos_422(mundo):
    from ventas import service as vs
    from ventas.schemas import DescuentoVentaIn

    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    with pytest.raises(ValidationError):
        vs.aplicar_descuento(mundo["db"], v.id, DescuentoVentaIn(descuento_id=1, cupon_codigo="X"), user=mundo["admin"])


def test_descuento_bajo_margen_minimo_requiere_autorizacion(mundo):
    from clientes import service as cli
    from clientes.schemas import DescuentoIn, MargenMinimoIn
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn, DescuentoVentaIn

    db = mundo["db"]
    # margen mínimo global 15% del costo, política "autorizar"
    cli.set_margen_minimo(db, MargenMinimoIn(tipo="porcentaje_costo", valor=Decimal("0.15"),
                                             ambito="global", politica="autorizar"), actor=mundo["admin"].id)
    desc = cli.crear_descuento(db, DescuentoIn(nombre="Liquidación", tipo="porcentaje", valor=Decimal("0.45"),
                                               alcance="tienda"), actor=mundo["admin"].id)

    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    # 5000 - 45% = 2750 ; costo 3000 → margen -250 < mínimo
    r = vs.aplicar_descuento(db, v.id, DescuentoVentaIn(descuento_id=desc.id), user=mundo["admin"])
    assert r.decision == "requiere_autorizacion"

    with pytest.raises(vs.NoAutorizadoError):
        vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["admin"])

    aut = cli.autorizar_margen_minimo(db, _AutIn(documento_tipo="venta", documento_id=v.id,
                                                 margen_resultante=Decimal("-250"), motivo="cierre de temporada"),
                                      user=mundo["admin"])
    d = vs.confirmar_venta(db, v.id, ConfirmarVentaIn(autorizacion_margen_minimo_id=aut["id"]), user=mundo["admin"])
    assert d.estado == "confirmada"


class _AutIn:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# --------------------------------------------------------------- US3
def test_garantias_fabrica_y_tienda(mundo):
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn, PagoVentaIn

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    vs.registrar_pago_venta(db, v.id, PagoVentaIn(medio_pago="efectivo", monto=Decimal("5000")), user=mundo["admin"])
    vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["admin"])

    gs = {g.tipo: g for g in vs.garantias(db, v.id)}
    assert set(gs) == {"fabrica", "tienda"}
    assert gs["fabrica"].fecha_fin == date.today() + timedelta(days=gs["fabrica"].periodo_dias)


# --------------------------------------------------------------- US6
def test_anular_reingresa_stock(mundo):
    from ventas import service as vs
    from ventas.schemas import AnularVentaIn, ConfirmarVentaIn, PagoVentaIn

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    vs.registrar_pago_venta(db, v.id, PagoVentaIn(medio_pago="efectivo", monto=Decimal("5000")), user=mundo["admin"])
    vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["admin"])

    vs.anular_venta(db, v.id, AnularVentaIn(motivo="cliente se arrepiente"), user=mundo["admin"])
    db.refresh(mundo["reloj"])
    assert mundo["reloj"].disponibilidad == "disponible"
    cxc = vs.cuentas_por_cobrar(db, cliente_id=mundo["cliente"].id, estado=None)
    assert all(c.estado == "anulada" for c in cxc) or not cxc


# --------------------------------------------------------------- consumidor final (D8)
def test_venta_de_reloj_exige_cliente_identificado(mundo):
    # reloj sin cliente → 422 (toda venta es de reloj ahora; ya no hay pieza suelta
    # que active la ruta de "consumidor final" anónimo — ver test siguiente)
    with pytest.raises(ValidationError):
        _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}], cliente_id=None)


def test_ventas_ya_no_admite_piezas_sueltas(mundo):
    """Feedback del usuario (2026-09-11): las piezas nunca se venden sueltas al
    mostrador, solo las consume el técnico al reparar (008). `item_tipo` deja de
    aceptar «pieza» — se rechaza en el propio schema, antes de llegar al service."""
    import pydantic
    from ventas.schemas import VentaIn

    with pytest.raises(pydantic.ValidationError):
        VentaIn(cliente_id=mundo["cliente"].id, sucursal_id=mundo["suc"].id,
               lineas=[{"item_tipo": "pieza", "pieza_id": mundo["pieza"].id, "cantidad": 1}])


# --------------------------------------------------------------- sucursal del vendedor / factura por correo
def test_sucursal_se_toma_del_vendedor(mundo):
    from ventas import service as vs
    from ventas.schemas import VentaIn

    db = mundo["db"]
    # el vendedor no envía sucursal_id: se usa la suya
    v = vs.crear_venta(db, VentaIn(cliente_id=mundo["cliente"].id,
                                   lineas=[{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}]),
                       user=mundo["vendedor"])
    assert v.sucursal_id == mundo["suc"].id
    assert v.vendedor_usuario_id == mundo["vendedor"].id

    # un vendedor de otra sucursal no puede registrar en la ajena
    otra = mundo["db"]  # noqa: F841
    from shared.guard import CurrentUser

    forastero = CurrentUser(id=mundo["vendedor"].id, identificacion="x", nombre="x", email="x",
                            estado="activo", token_scope="full", roles=["Vendedor"], rol_ids=[], sucursal_ids=[999])
    with pytest.raises((vs.NoAutorizadoError, ValidationError)):
        vs.crear_venta(db, VentaIn(cliente_id=mundo["cliente"].id, sucursal_id=mundo["suc"].id,
                                   lineas=[{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}]),
                       user=forastero)


def test_enviar_factura_requiere_correo_del_cliente(mundo):
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn, PagoVentaIn

    db = mundo["db"]
    v = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj"].id}])
    vs.registrar_pago_venta(db, v.id, PagoVentaIn(medio_pago="efectivo", monto=Decimal("5000")), user=mundo["admin"])
    vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["admin"])

    r = vs.enviar_factura_correo(db, v.id, user=mundo["admin"])  # tests: EMAIL_BACKEND=console → no envía real
    assert r.enviado is True and r.email == "c009@test.local"

    mundo["cliente"].email = None
    db.flush()
    v2 = _crear(mundo, [{"item_tipo": "reloj", "reloj_id": mundo["reloj2"].id}])
    vs.registrar_pago_venta(db, v2.id, PagoVentaIn(medio_pago="efectivo", monto=Decimal("120")), user=mundo["admin"])
    vs.confirmar_venta(db, v2.id, ConfirmarVentaIn(), user=mundo["admin"])
    r2 = vs.enviar_factura_correo(db, v2.id, user=mundo["admin"])
    assert r2.enviado is False
