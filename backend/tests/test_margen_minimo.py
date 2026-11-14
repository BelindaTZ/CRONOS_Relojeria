"""Feature 006 — margen mínimo protegido (US4).

**Crítico (Const. Ppio IX + Ppio V)**: el margen se calcula SIEMPRE en backend; un
descuento que deja el margen bajo el mínimo se bloquea o exige autorización de
Gerencia General; descuento y cupón no se combinan.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from clientes import service as cli
from clientes.schemas import AplicarDescuentoIn, AutorizarMargenIn, DescuentoAplicableIn, MargenMinimoIn
from shared.descuentos import BeneficioAplicable
from shared.descuentos import aplicar as aplicar_desc
from shared.exceptions import ValidationError
from shared.guard import CurrentUser


def _gg(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def _no_gg(factory):
    u = factory.usuario()
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Vendedor"], rol_ids=[], sucursal_ids=[])


def test_descuento_bajo_minimo_requiere_autorizacion(db, factory):
    # margen_minimo global por defecto = 15 % sobre costo, política "autorizar"
    r = cli.aplicar_descuento(db, AplicarDescuentoIn(
        item_ref="OMEGA-310", costo=Decimal("6000"), precio_lista=Decimal("8000"),
        descuento=DescuentoAplicableIn(tipo="porcentaje", valor=Decimal("0.30")),
    ))
    # precio_final 5600 → margen -400; mínimo = 6000×0.15 = 900 → cae por debajo
    assert r.precio_final == Decimal("5600.00")
    assert r.margen_resultante == Decimal("-400.00")
    assert r.decision == "requiere_autorizacion"


def test_descuento_deja_margen_ok_permite(db, factory):
    r = cli.aplicar_descuento(db, AplicarDescuentoIn(
        item_ref="OMEGA-310", costo=Decimal("6000"), precio_lista=Decimal("8000"),
        descuento=DescuentoAplicableIn(tipo="porcentaje", valor=Decimal("0.05")),
    ))
    # precio_final 7600 → margen 1600 ≥ 900 → permitir
    assert r.decision == "permitir"


def test_margen_exactamente_en_el_minimo_permite(db, factory):
    # costo 1000, mínimo 15 % = 150. precio_final que deja margen 150 → 1150.
    r = cli.aplicar_descuento(db, AplicarDescuentoIn(
        item_ref="X", costo=Decimal("1000"), precio_lista=Decimal("1200"),
        descuento=DescuentoAplicableIn(tipo="monto", valor=Decimal("50")),
    ))
    assert r.precio_final == Decimal("1150.00") and r.margen_resultante == Decimal("150.00")
    assert r.decision == "permitir"  # >= mínimo


def test_politica_bloquear(db, factory):
    gg = _gg(factory)
    cli.set_margen_minimo(db, MargenMinimoIn(tipo="porcentaje_costo", valor=Decimal("0.15"),
                                             ambito="global", politica="bloquear"), actor=gg.id)
    r = cli.aplicar_descuento(db, AplicarDescuentoIn(
        item_ref="X", costo=Decimal("6000"), precio_lista=Decimal("8000"),
        descuento=DescuentoAplicableIn(tipo="porcentaje", valor=Decimal("0.30")),
    ))
    assert r.decision == "bloquear"


def test_precedencia_producto_sobre_global(db, factory):
    gg = _gg(factory)
    cli.set_margen_minimo(db, MargenMinimoIn(tipo="monto", valor=Decimal("50"),
                                             ambito="producto", ref="BARATO-1"), actor=gg.id)
    # global sigue 15 % → para BARATO-1 manda el mínimo de 50
    r = cli.aplicar_descuento(db, AplicarDescuentoIn(
        item_ref="BARATO-1", costo=Decimal("100"), precio_lista=Decimal("200"),
        descuento=DescuentoAplicableIn(tipo="monto", valor=Decimal("60")),
    ))
    # precio_final 140 → margen 40 < 50 → requiere_autorizacion
    assert r.margen_minimo_aplicado.ambito == "producto"
    assert r.decision == "requiere_autorizacion"


def test_descuento_y_cupon_juntos_422(db, factory):
    with pytest.raises(ValidationError):
        aplicar_desc(db, item_ref="X", costo=Decimal("100"), precio_lista=Decimal("150"),
                     descuento=BeneficioAplicable(tipo="porcentaje", valor=Decimal("0.1")),
                     cupon=BeneficioAplicable(tipo="monto", valor=Decimal("10")))


def test_autorizacion_solo_gerencia_general_y_se_audita(db, factory):
    gg = _gg(factory)
    a = cli.autorizar_margen_minimo(db, AutorizarMargenIn(
        documento_tipo="venta", documento_id=999, motivo="Cliente VIP, cierre de trimestre",
        margen_resultante=Decimal("-400"),
    ), user=gg)
    assert a["documento_id"] == 999

    from shared.models import RegistroAuditoria

    aud = db.query(RegistroAuditoria).filter_by(entidad="autorizacion_margen_minimo").all()
    assert aud and aud[0].accion == "autorizar"

    with pytest.raises(cli.NoAutorizadoError):
        cli.autorizar_margen_minimo(db, AutorizarMargenIn(
            documento_tipo="venta", documento_id=1000, motivo="no debería"), user=_no_gg(factory))


def test_frontend_no_puede_forzar_el_margen(client, factory, auth_header):
    gg = factory.usuario(roles=[factory.gerencia()])
    # el endpoint no acepta 'margen_resultante' de entrada — el backend lo recalcula
    r = client.post("/_internal/descuentos/aplicar", json={
        "item_ref": "X", "costo": 6000, "precio_lista": 8000,
        "descuento": {"tipo": "porcentaje", "valor": 0.30},
        "margen_resultante": 5000,  # intento de forzar
    }, headers=auth_header(gg))
    assert r.status_code == 200
    assert r.json()["margen_resultante"] == "-400.00"
    assert r.json()["decision"] == "requiere_autorizacion"
