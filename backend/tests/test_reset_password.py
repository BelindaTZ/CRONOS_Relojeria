"""Restablecimiento de contraseña (US4): un solo uso, caducidad, cambio forzado, neutra."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from auth import service
from shared.models import SolicitudRestablecimiento, Usuario
from shared.security import verify_password


def _temporal_de(db, usuario_id) -> str | None:
    # el correo va a backend 'console'; recuperamos el hash y probamos por fuerza
    # bruta NO — en su lugar interceptamos generar_password_temporal.
    return None


def test_flujo_completo_un_solo_uso_y_cambio_forzado(client, factory, db, monkeypatch):
    from shared import security

    monkeypatch.setattr(security, "generar_password_temporal", lambda longitud=12: "TEMP-abc123")
    # el service importa el símbolo directamente:
    monkeypatch.setattr("auth.service.generar_password_temporal", lambda: "TEMP-abc123")

    u = factory.usuario(password="vieja-clave")
    r = client.post("/auth/olvide-contrasena", json={"identificacion": u.identificacion})
    assert r.status_code == 202

    sol = db.scalars(
        sa.select(SolicitudRestablecimiento).where(SolicitudRestablecimiento.usuario_id == u.id)
    ).one()
    assert verify_password("TEMP-abc123", sol.password_temporal_hash)

    # login con la temporal -> must_change_password
    login = client.post(
        "/auth/login", json={"identificacion": u.identificacion, "password": "TEMP-abc123"}
    ).json()
    assert login["must_change_password"] is True
    token = {"Authorization": f"Bearer {login['access_token']}"}

    # el token restringido no autoriza otros endpoints
    assert client.get("/perfil", headers=token).status_code == 403

    # cambiar contraseña sí
    r = client.post(
        "/auth/cambiar-contrasena", headers=token, json={"actual": "TEMP-abc123", "nueva": "nueva-clave-2026"}
    )
    assert r.status_code == 204

    # la temporal ya no sirve
    r2 = client.post(
        "/auth/login", json={"identificacion": u.identificacion, "password": "TEMP-abc123"}
    )
    assert r2.status_code == 401

    # login normal con la nueva
    ok = client.post(
        "/auth/login", json={"identificacion": u.identificacion, "password": "nueva-clave-2026"}
    )
    assert ok.status_code == 200 and ok.json()["must_change_password"] is False


def test_temporal_caducada_se_rechaza(client, factory, db, monkeypatch):
    monkeypatch.setattr("auth.service.generar_password_temporal", lambda: "TEMP-xyz")
    u = factory.usuario(password="p")
    client.post("/auth/olvide-contrasena", json={"identificacion": u.identificacion})
    sol = db.scalars(
        sa.select(SolicitudRestablecimiento).where(SolicitudRestablecimiento.usuario_id == u.id)
    ).one()
    sol.expira_en = datetime.now(timezone.utc) - timedelta(hours=1)
    db.flush()
    r = client.post("/auth/login", json={"identificacion": u.identificacion, "password": "TEMP-xyz"})
    assert r.status_code == 401


def test_respuesta_neutra_para_usuario_inexistente(client):
    r = client.post("/auth/olvide-contrasena", json={"identificacion": "0000000000"})
    assert r.status_code == 202
