"""Login: credenciales válidas/inválidas, refresh válido/revocado, rate-limit."""

from __future__ import annotations


def test_login_ok_devuelve_par_de_tokens(client, factory):
    u = factory.usuario(password="clave-buena-1")
    r = client.post("/auth/login", json={"identificacion": u.identificacion, "password": "clave-buena-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["must_change_password"] is False


def test_login_credenciales_invalidas_401(client, factory):
    u = factory.usuario(password="clave-buena-1")
    r = client.post("/auth/login", json={"identificacion": u.identificacion, "password": "mala"})
    assert r.status_code == 401


def test_refresh_devuelve_nuevo_access(client, factory):
    u = factory.usuario(password="c")
    login = client.post("/auth/login", json={"identificacion": u.identificacion, "password": "c"}).json()
    r = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_refresh_revocado_tras_logout_falla(client, factory, auth_header):
    u = factory.usuario(password="c")
    login = client.post("/auth/login", json={"identificacion": u.identificacion, "password": "c"}).json()
    client.post("/auth/logout", headers=auth_header(u), json={"refresh_token": login["refresh_token"]})
    r = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 401


def test_rate_limit_bloquea_tras_n_intentos(client, factory, monkeypatch):
    from shared import ratelimit

    monkeypatch.setattr(ratelimit.get_settings(), "login_max_intentos", 3, raising=False)
    u = factory.usuario(password="c")
    ident = u.identificacion
    for _ in range(3):
        client.post("/auth/login", json={"identificacion": ident, "password": "mala"})
    r = client.post("/auth/login", json={"identificacion": ident, "password": "c"})
    assert r.status_code == 429
    ratelimit.limpiar_exito(f"login:{ident}")
