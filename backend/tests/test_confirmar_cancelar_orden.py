"""OC v2 (decisiones 2026-09-10): confirmación del proveedor + regla de cancelación."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from proveedores import service
from proveedores.schemas import CancelarIn, LineaIn, OrdenCompraIn, ProveedorIn, RecepcionIn, RecepcionLineaIn
from proveedores.service import NoAutorizadoError
from shared.exceptions import ConflictError, ValidationError


def _orden_emitida(db, factory, *, fecha_pactada=None):
    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(
        db, ProveedorIn(razon_social="Prov OC", email="proveedor@example.com"), actor=actor
    ).id
    o = service.crear_orden(
        db, OrdenCompraIn(proveedor_id=pid, sucursal_destino_id=sid, fecha_pactada=fecha_pactada,
                          lineas=[LineaIn(item_tipo="pieza", item_ref="9010", cantidad=3, costo_unitario=10)]),
        actor=actor,
    )
    service.emitir_orden(db, o.id, actor=actor)
    return actor, o.id


def test_confirmar_requiere_rol_elevado(db, factory):
    _, oid = _orden_emitida(db, factory)
    normal = factory.current_user()  # sin roles
    with pytest.raises(NoAutorizadoError):
        service.confirmar_orden(db, oid, user=normal)


def test_confirmar_ok_y_habilita_recepcion(db, factory):
    actor, oid = _orden_emitida(db, factory)
    elevado = factory.current_user(gerencia=True)
    linea_prev = service.repository.obtener_orden(db, oid).lineas[0].id

    # antes de confirmar no se puede recibir
    with pytest.raises(ConflictError):
        service.registrar_recepcion(
            db, oid, RecepcionIn(fecha_real=date.today(),
                                 lineas=[RecepcionLineaIn(linea_orden_compra_id=linea_prev, cantidad_recibida=1)]),
            actor=actor,
        )

    out = service.confirmar_orden(db, oid, user=elevado)
    assert out.estado == "confirmada"
    assert out.fecha_confirmacion is not None

    linea_id = out.lineas[0].id
    rec = service.registrar_recepcion(
        db, oid, RecepcionIn(fecha_real=date.today(),
                             lineas=[RecepcionLineaIn(linea_orden_compra_id=linea_id, cantidad_recibida=3)]),
        actor=actor,
    )
    assert rec.estado == "recibida"


def test_confirmar_solo_desde_emitida(db, factory):
    actor, oid = _orden_emitida(db, factory)
    elevado = factory.current_user(gerencia=True)
    service.confirmar_orden(db, oid, user=elevado)
    with pytest.raises(ConflictError):
        service.confirmar_orden(db, oid, user=elevado)  # ya está confirmada


def test_cancelar_exige_motivo(db, factory):
    actor, oid = _orden_emitida(db, factory)
    with pytest.raises(ValidationError):
        service.cancelar_orden(db, oid, motivo="   ", actor=actor)


def test_cancelar_bloqueado_dentro_de_24h_de_la_fecha_pactada(db, factory):
    # fecha pactada = mañana → dentro de la ventana de 24 h
    actor, oid = _orden_emitida(db, factory, fecha_pactada=date.today() + timedelta(days=1))
    with pytest.raises(ConflictError):
        service.cancelar_orden(db, oid, motivo="ya no se necesita", actor=actor)


def test_cancelar_permitido_con_holgura_y_avisa_al_proveedor(db, factory, monkeypatch):
    enviados = []
    monkeypatch.setattr("proveedores.service.enviar", lambda plantilla, a, ctx: enviados.append((plantilla, a)))
    actor, oid = _orden_emitida(db, factory, fecha_pactada=date.today() + timedelta(days=30))
    out = service.cancelar_orden(db, oid, motivo="cambio de plan de compras", actor=actor)
    assert out.estado == "cancelada"
    assert enviados and enviados[0][0] == "cancelacion_orden"
