"""Proveedores (US1): RUC duplicado 409; editar razón social / RUC sin rol elevado 403;
toda edición audita; inactivar en vez de borrar."""

from __future__ import annotations

import sqlalchemy as sa
import pytest

from proveedores import service
from proveedores.schemas import ProveedorIn, ProveedorPatch
from proveedores.service import NoAutorizadoError
from shared.guard import CurrentUser
from shared.models import RegistroAuditoria


def _user(factory, db, elevado: bool) -> CurrentUser:
    roles = [factory.gerencia()] if elevado else [factory.rol("Vendedor")]
    u = factory.usuario(roles=roles)
    return CurrentUser(
        id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
        estado="activo", token_scope="full",
        roles=["Gerencia General"] if elevado else ["Vendedor"], rol_ids=[r.id for r in roles],
    )


def test_ruc_duplicado_409(db, factory):
    actor = factory.usuario()
    service.crear(db, ProveedorIn(razon_social="Alfa", ruc_nit="1790000000001"), actor=actor.id)
    from shared.exceptions import ConflictError

    with pytest.raises(ConflictError):
        service.crear(db, ProveedorIn(razon_social="Beta", ruc_nit="1790000000001"), actor=actor.id)


def test_editar_ruc_sin_rol_elevado_403(db, factory):
    actor = factory.usuario()
    p = service.crear(db, ProveedorIn(razon_social="Alfa", ruc_nit="1790000000002"), actor=actor.id)
    normal = _user(factory, db, elevado=False)
    with pytest.raises(NoAutorizadoError):
        service.actualizar(db, p.id, ProveedorPatch(ruc_nit="9999999999999"), user=normal)


def test_editar_campos_libres_ok_y_audita(db, factory):
    actor = factory.usuario()
    p = service.crear(db, ProveedorIn(razon_social="Alfa", ruc_nit="1790000000003"), actor=actor.id)
    normal = _user(factory, db, elevado=False)
    out = service.actualizar(db, p.id, ProveedorPatch(telefono="0999", contacto_nombre="Juan Pérez"), user=normal)
    assert out.telefono == "0999"
    aud = db.scalars(
        sa.select(RegistroAuditoria).where(
            RegistroAuditoria.entidad == "proveedor", RegistroAuditoria.accion == "editar"
        )
    ).all()
    assert aud


def test_editar_razon_social_con_rol_elevado_ok(db, factory):
    actor = factory.usuario()
    p = service.crear(db, ProveedorIn(razon_social="Alfa", ruc_nit="1790000000004"), actor=actor.id)
    elevado = _user(factory, db, elevado=True)
    out = service.actualizar(db, p.id, ProveedorPatch(razon_social="A Corregida"), user=elevado)
    assert out.razon_social == "A Corregida"


def test_inactivar_no_borra(db, factory):
    actor = factory.usuario()
    p = service.crear(db, ProveedorIn(razon_social="Alfa"), actor=actor.id)
    out = service.inactivar(db, p.id, actor=actor.id)
    assert out.estado == "inactivo"
    from proveedores import repository

    assert repository.obtener(db, p.id) is not None  # sigue existiendo
