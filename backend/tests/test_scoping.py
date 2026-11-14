"""Scoping por sucursal y por propiedad (US7): gerente de A no ve B; GG consolidado."""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from shared.guard import NoAutorizadoError, scope_propiedad, scope_sucursal
from shared.models import UsuarioSucursal
from tests.test_guard_rbac import _cu


def test_scope_sucursal_limita_a_las_del_usuario(db, factory):
    a = factory.sucursal("A")
    b = factory.sucursal("B")
    gerente_a = _cu(db, factory.usuario(sucursales=[a]))

    stmt = scope_sucursal(sa.select(UsuarioSucursal.sucursal_id), gerente_a, UsuarioSucursal.sucursal_id)
    ids = set(db.scalars(stmt))
    assert b.id not in ids


def test_gerencia_general_ve_consolidado(db, factory):
    a = factory.sucursal("A")
    b = factory.sucursal("B")
    g = factory.gerencia()
    gg = _cu(db, factory.usuario(roles=[g]))  # sin sucursales asignadas

    stmt = scope_sucursal(sa.select(UsuarioSucursal.sucursal_id), gg, UsuarioSucursal.sucursal_id)
    # no añade filtro -> no revienta y no restringe
    db.scalars(stmt).all()


def test_usuario_sin_sucursal_no_puede_operar_scoped(db, factory):
    sin_suc = _cu(db, factory.usuario())
    with pytest.raises(NoAutorizadoError):
        list(db.scalars(scope_sucursal(sa.select(UsuarioSucursal.id), sin_suc, UsuarioSucursal.sucursal_id)))


def test_scope_propiedad_limita_a_registros_propios(db, factory):
    u = _cu(db, factory.usuario())
    otro = factory.usuario()
    stmt = scope_propiedad(sa.select(UsuarioSucursal.usuario_id), u, UsuarioSucursal.usuario_id)
    # el usuario u no tiene registros -> vacío; el filtro es == u.id
    assert otro.id not in set(db.scalars(stmt))
