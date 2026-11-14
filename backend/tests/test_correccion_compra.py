"""Corrección de compra recibida (US6): 403 rol normal; 200 + auditoría rol elevado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import sqlalchemy as sa

from proveedores import service
from proveedores.schemas import (
    CorreccionIn,
    CorreccionLinea,
    LineaIn,
    OrdenCompraIn,
    ProveedorIn,
    RecepcionIn,
    RecepcionLineaIn,
)
from proveedores.service import NoAutorizadoError
from shared.guard import CurrentUser
from shared.models import RegistroAuditoria


def _orden_recibida(db, factory):
    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(db, ProveedorIn(razon_social="Corr"), actor=actor).id
    o = service.crear_orden(
        db, OrdenCompraIn(proveedor_id=pid, sucursal_destino_id=sid, fecha_pactada=date(2026, 9, 20),
                          lineas=[LineaIn(item_tipo="pieza", item_ref="9010", cantidad=2, costo_unitario=45)]),
        actor=actor,
    )
    service.emitir_orden(db, o.id, actor=actor)
    service.confirmar_orden(db, o.id, user=factory.current_user(gerencia=True))
    service.registrar_recepcion(
        db, o.id, RecepcionIn(fecha_real=date(2026, 9, 20),
                              lineas=[RecepcionLineaIn(linea_orden_compra_id=o.lineas[0].id, cantidad_recibida=2)]),
        actor=actor,
    )
    return o


def _cu(factory, db, elevado):
    roles = [factory.gerencia()] if elevado else [factory.rol("Vendedor")]
    u = factory.usuario(roles=roles)
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full",
                       roles=["Gerencia General"] if elevado else ["Vendedor"], rol_ids=[r.id for r in roles])


def test_correccion_rol_normal_403(db, factory):
    o = _orden_recibida(db, factory)
    normal = _cu(factory, db, elevado=False)
    with pytest.raises(NoAutorizadoError):
        service.corregir_orden(
            db, o.id, CorreccionIn(motivo="error de digitación",
                                   lineas=[CorreccionLinea(id=o.lineas[0].id, costo_unitario=Decimal("50"))]),
            user=normal,
        )


def test_correccion_rol_elevado_200_y_auditoria(db, factory):
    o = _orden_recibida(db, factory)
    elevado = _cu(factory, db, elevado=True)
    out = service.corregir_orden(
        db, o.id, CorreccionIn(motivo="error de digitación",
                               lineas=[CorreccionLinea(id=o.lineas[0].id, costo_unitario=Decimal("50"))]),
        user=elevado,
    )
    assert out.lineas[0].costo_unitario == Decimal("50.00")
    assert out.importe_a_pagar == Decimal("100.00")  # 2 * 50
    aud = db.scalars(
        sa.select(RegistroAuditoria).where(
            RegistroAuditoria.entidad == "orden_compra", RegistroAuditoria.accion == "corregir"
        )
    ).all()
    assert aud and aud[-1].despues.get("motivo") == "error de digitación"
