"""Autoservicio (US3): email/foto editables; rol/identificación/sucursales inmutables."""

from __future__ import annotations


def test_get_perfil_muestra_datos_en_solo_lectura(client, factory, auth_header):
    rol = factory.rol("Vendedor")
    suc = factory.sucursal("Centro")
    u = factory.usuario(roles=[rol], sucursales=[suc])
    r = client.get("/perfil", headers=auth_header(u))
    assert r.status_code == 200
    body = r.json()
    assert body["identificacion"] == u.identificacion
    assert "Vendedor" in body["roles"]
    assert "Centro" in body["sucursales"]


def test_patch_perfil_cambia_email_y_audita(client, factory, auth_header, db):
    import sqlalchemy as sa

    from shared.models import RegistroAuditoria

    u = factory.usuario()
    nuevo = "nuevo-correo@test.local"
    r = client.patch("/perfil", headers=auth_header(u), data={"email": nuevo})
    assert r.status_code == 200
    assert r.json()["email"] == nuevo

    db.refresh(u)
    assert u.email == nuevo
    aud = db.scalars(
        sa.select(RegistroAuditoria).where(RegistroAuditoria.entidad == "usuario_autoservicio")
    ).all()
    assert any(a.actor_usuario_id == u.id for a in aud)


def test_patch_perfil_ignora_campos_no_permitidos(client, factory, auth_header, db):
    rol = factory.rol("Vendedor")
    otro_rol = factory.rol("Gerente")
    u = factory.usuario(roles=[rol])
    # intentar colar rol_id / identificacion en el form: se ignoran (no son campos del endpoint)
    r = client.patch(
        "/perfil",
        headers=auth_header(u),
        data={"email": "x@test.local", "rol_id": str(otro_rol.id), "identificacion": "9999999999"},
    )
    assert r.status_code == 200
    db.refresh(u)
    assert u.identificacion != "9999999999"
    assert "Vendedor" in client.get("/perfil", headers=auth_header(u)).json()["roles"]
    assert "Gerente" not in client.get("/perfil", headers=auth_header(u)).json()["roles"]
