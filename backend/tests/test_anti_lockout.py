"""Anti-lockout de Gerencia General (FR-026 — regla crítica)."""

from __future__ import annotations

import pytest

from shared.exceptions import ConflictError
from usuarios import service
from usuarios.schemas import UsuarioPatch


def test_no_se_puede_desactivar_al_unico_gerencia(db, factory):
    g = factory.gerencia()
    unico = factory.usuario(roles=[g])
    with pytest.raises(ConflictError):
        service.actualizar(db, unico.id, UsuarioPatch(estado="inactivo"), actor=unico.id)


def test_no_se_puede_quitar_el_rol_al_unico_gerencia(db, factory):
    g = factory.gerencia()
    otro_rol = factory.rol("Vendedor")
    unico = factory.usuario(roles=[g])
    with pytest.raises(ConflictError):
        service.set_roles(db, unico.id, [otro_rol.id], actor=unico.id)


def test_se_permite_si_queda_otro_gerencia_activo(db, factory):
    g = factory.gerencia()
    factory.usuario(roles=[g])  # segundo Gerencia General
    saliente = factory.usuario(roles=[g])
    otro_rol = factory.rol("Vendedor")
    # ahora sí se puede cambiar el rol del saliente
    out = service.set_roles(db, saliente.id, [otro_rol.id], actor=saliente.id)
    assert "Vendedor" in out.roles and "Gerencia General" not in out.roles
