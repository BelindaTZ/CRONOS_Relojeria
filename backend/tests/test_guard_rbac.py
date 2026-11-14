"""Guard RBAC de dos niveles — módulo crítico (Constitución, Principio IX).

Cubre: acceso a módulo sin operación, operación sin acceso a módulo, overrides de
usuario conceder/revocar, 401/403, y frescura de la autorización tras cambiar el rol.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures("_migrar")


def _cu(db, usuario):
    """Construye un CurrentUser como lo haría el guard (roles/sucursales frescos)."""
    import sqlalchemy as sa

    from shared.guard import CurrentUser
    from shared.models import Rol, UsuarioRol, UsuarioSucursal

    roles = db.execute(
        sa.select(Rol.id, Rol.nombre).join(UsuarioRol, UsuarioRol.rol_id == Rol.id).where(
            UsuarioRol.usuario_id == usuario.id
        )
    ).all()
    sucs = list(db.scalars(sa.select(UsuarioSucursal.sucursal_id).where(UsuarioSucursal.usuario_id == usuario.id)))
    return CurrentUser(
        id=usuario.id, identificacion=usuario.identificacion, nombre=usuario.nombre,
        email=usuario.email, estado=usuario.estado, token_scope="full",
        roles=[r.nombre for r in roles], rol_ids=[r.id for r in roles], sucursal_ids=sucs,
    )


def _autorizado(db, user, modulo, operacion) -> bool:
    from shared.guard import _overrides_usuario, _tiene_acceso_modulo, _tiene_operacion

    ov = _overrides_usuario(db, user.id)
    if not _tiene_acceso_modulo(db, user, modulo, ov):
        return False
    return _tiene_operacion(db, user, modulo, operacion, ov)


def test_acceso_a_modulo_sin_la_operacion_niega(db, factory):
    rol = factory.rol()
    factory.permitir(rol, "citas", ["crear", "consultar"])  # sin 'eliminar'
    u = factory.usuario(roles=[rol])
    user = _cu(db, u)

    assert _autorizado(db, user, "citas", "crear") is True
    assert _autorizado(db, user, "citas", "eliminar") is False


def test_operacion_sin_acceso_al_modulo_niega(db, factory):
    """La operación puede existir en el rol pero si no hay acceso al módulo -> 403."""
    rol = factory.rol()
    # concede la operación pero NO el permiso_modulo (situación inconsistente que
    # el guard debe cortar: acceso a módulo es prerrequisito)
    import sqlalchemy as sa

    from shared.models import Modulo, Operacion, PermisoOperacion

    m = db.scalars(sa.select(Modulo).where(Modulo.clave == "contable")).one()
    o = db.scalars(sa.select(Operacion).where(Operacion.clave == "consultar")).one()
    db.add(PermisoOperacion(rol_id=rol.id, modulo_id=m.id, operacion_id=o.id))
    db.flush()
    user = _cu(db, factory.usuario(roles=[rol]))

    assert _autorizado(db, user, "contable", "consultar") is False


def test_override_conceder_y_revocar(db, factory):
    rol = factory.rol()
    factory.permitir(rol, "citas", ["crear"])
    u = factory.usuario(roles=[rol])

    import sqlalchemy as sa

    from shared.models import Modulo, Operacion, PermisoUsuario

    citas = db.scalars(sa.select(Modulo).where(Modulo.clave == "citas")).one()
    inv = db.scalars(sa.select(Modulo).where(Modulo.clave == "inventario_relojes")).one()
    crear = db.scalars(sa.select(Operacion).where(Operacion.clave == "crear")).one()

    # revoca 'crear' en citas; concede acceso+crear en inventario
    db.add(PermisoUsuario(usuario_id=u.id, modulo_id=citas.id, operacion_id=crear.id, efecto="revocar"))
    db.add(PermisoUsuario(usuario_id=u.id, modulo_id=inv.id, operacion_id=None, efecto="conceder"))
    db.add(PermisoUsuario(usuario_id=u.id, modulo_id=inv.id, operacion_id=crear.id, efecto="conceder"))
    db.flush()
    user = _cu(db, u)

    assert _autorizado(db, user, "citas", "crear") is False  # revocado
    assert _autorizado(db, user, "inventario_relojes", "crear") is True  # concedido sin rol


def test_frescura_tras_cambio_de_rol(db, factory):
    from shared.guard import invalidar_cache

    rol_a = factory.rol()
    factory.permitir(rol_a, "citas", ["consultar"])
    rol_b = factory.rol()
    factory.permitir(rol_b, "contable", ["consultar"])
    u = factory.usuario(roles=[rol_a])

    user = _cu(db, u)
    assert _autorizado(db, user, "citas", "consultar") is True
    assert _autorizado(db, user, "contable", "consultar") is False

    # cambia el rol del usuario
    import sqlalchemy as sa

    from shared.models import UsuarioRol

    db.execute(sa.delete(UsuarioRol).where(UsuarioRol.usuario_id == u.id))
    db.add(UsuarioRol(usuario_id=u.id, rol_id=rol_b.id))
    db.flush()
    invalidar_cache()

    user2 = _cu(db, u)  # el guard recarga roles en cada petición
    assert _autorizado(db, user2, "citas", "consultar") is False
    assert _autorizado(db, user2, "contable", "consultar") is True


def test_endpoint_sin_token_401_y_con_token_sin_permiso_403(client, factory, auth_header, db):
    # sin token
    assert client.get("/roles").status_code == 401
    # token válido pero rol sin acceso a 'configuracion'
    rol = factory.rol()
    factory.permitir(rol, "citas", ["consultar"])
    u = factory.usuario(roles=[rol])
    assert client.get("/roles", headers=auth_header(u)).status_code == 403


def test_token_de_cambio_forzado_no_autoriza_endpoints_normales(client, factory, auth_header):
    g = factory.gerencia()
    u = factory.usuario(roles=[g])
    r = client.get("/roles", headers=auth_header(u, scope="password_change"))
    assert r.status_code == 403
