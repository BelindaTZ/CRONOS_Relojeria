"""Catálogos editables (decisiones 2026-09-10): condicion_pago maestro; medio_pago
activar/inactivar + agregar; contraseña temporal generada por el sistema."""

from __future__ import annotations

from configuracion import service as cfg
from configuracion.schemas import ActivoIn, CondicionPagoIn, MedioPagoIn
from usuarios import service as usuarios_service
from usuarios.schemas import UsuarioIn


def test_condicion_pago_semilla_y_alta(db, factory):
    actor = factory.usuario().id
    base = cfg.listar_condiciones_pago(db)
    assert any(c.nombre == "Contado" for c in base)
    assert any(c.nombre == "30 días" for c in base)

    nueva = cfg.crear_condicion_pago(db, CondicionPagoIn(nombre="90 días", dias_credito=90), actor=actor)
    assert nueva.dias_credito == 90
    assert any(c.nombre == "90 días" for c in cfg.listar_condiciones_pago(db))


def test_condicion_pago_inactivar(db, factory):
    actor = factory.usuario().id
    c = cfg.crear_condicion_pago(db, CondicionPagoIn(nombre="Consignación"), actor=actor)
    off = cfg.set_activo_condicion_pago(db, c.id, False, actor=actor)
    assert off.activo is False
    assert not any(x.id == c.id for x in cfg.listar_condiciones_pago(db, solo_activas=True))


def test_medio_pago_agregar_y_inactivar(db, factory):
    actor = factory.usuario().id
    m = cfg.crear_medio_pago(db, MedioPagoIn(nombre="Crédito directo"), actor=actor)
    assert m.clave == "credito_directo"
    claves = {x.clave for x in cfg.listar_medios_pago(db)}
    assert {"efectivo", "credito_directo"} <= claves

    efectivo = next(x for x in cfg.listar_medios_pago(db) if x.clave == "efectivo")
    off = cfg.set_activo_medio_pago(db, efectivo.id, False, actor=actor)
    assert off.activo is False


def test_alta_de_usuario_genera_contrasena_temporal(db, factory):
    actor = factory.usuario().id
    rol = factory.rol("Vendedor")
    out = usuarios_service.crear(
        db,
        UsuarioIn(identificacion="1799999999", nombre="Demo User", email="demo@example.com", rol_ids=[rol.id]),
        actor=actor,
    )
    assert out.password_temporal and len(out.password_temporal) >= 10

    from shared.models import Usuario

    u = db.get(Usuario, out.id)
    assert u.must_change_password is True
