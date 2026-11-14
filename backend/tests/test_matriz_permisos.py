"""Matriz de permisos (US1): operación sin acceso a módulo -> 422; guardado válido
se refleja en el guard."""

from __future__ import annotations

import pytest

from rbac import service as rbac_service
from rbac.schemas import PermisoModuloIn
from shared.exceptions import ValidationError


def test_operacion_sin_acceso_al_modulo_es_422(db, factory):
    actor = factory.usuario()
    rol = factory.rol("Vendedor")
    with pytest.raises(ValidationError):
        rbac_service.set_permisos_rol(
            db,
            rol.id,
            [PermisoModuloIn(modulo="citas", acceso=False, operaciones=["crear"])],
            actor=actor.id,
        )


def test_guardado_valido_se_refleja_en_el_guard(db, factory):
    actor = factory.usuario()
    from shared.guard import _overrides_usuario, _tiene_acceso_modulo, _tiene_operacion
    from tests.test_guard_rbac import _cu

    rol = factory.rol("Vendedor")
    rbac_service.set_permisos_rol(
        db,
        rol.id,
        [PermisoModuloIn(modulo="citas", acceso=True, operaciones=["crear", "consultar"])],
        actor=actor.id,
    )
    u = factory.usuario(roles=[rol])
    user = _cu(db, u)
    ov = _overrides_usuario(db, user.id)
    assert _tiene_acceso_modulo(db, user, "citas", ov)
    assert _tiene_operacion(db, user, "citas", "crear", ov)
    assert not _tiene_operacion(db, user, "citas", "eliminar", ov)


def test_reemplazo_de_matriz_quita_permisos_anteriores(db, factory):
    actor = factory.usuario()
    from shared.guard import _overrides_usuario, _tiene_acceso_modulo
    from tests.test_guard_rbac import _cu

    rol = factory.rol()
    rbac_service.set_permisos_rol(
        db, rol.id, [PermisoModuloIn(modulo="contable", acceso=True, operaciones=["consultar"])], actor=actor.id
    )
    rbac_service.set_permisos_rol(
        db, rol.id, [PermisoModuloIn(modulo="citas", acceso=True, operaciones=["consultar"])], actor=actor.id
    )
    user = _cu(db, factory.usuario(roles=[rol]))
    ov = _overrides_usuario(db, user.id)
    assert _tiene_acceso_modulo(db, user, "citas", ov)
    assert not _tiene_acceso_modulo(db, user, "contable", ov)
