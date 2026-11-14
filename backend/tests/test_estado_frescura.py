"""Feature 012, US4 (T024): `GET /reportes/estado-frescura` degrada limpio con
ClickHouse no disponible (el entorno de tests no lo levanta) — nunca un 500.
`POST /reportes/actualizar-ahora` igual con Airflow (Spec §FR-011, contrato
`pipeline-estado.openapi.yaml`). También el gating RBAC del módulo `reportes`."""
from __future__ import annotations


def test_estado_frescura_degrada_limpio_nunca_500(client, factory, auth_header):
    """`disponible` refleja si ClickHouse respondió — nunca un 500 ni al alcanzar
    el servicio real (si el entorno lo levantó) ni al fallar la conexión."""
    rol = factory.gerencia()
    u = factory.usuario(roles=[rol])
    r = client.get("/reportes/estado-frescura", headers=auth_header(u))
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["disponible"], bool)
    if not body["disponible"]:
        assert body["dominios"] == []


def test_actualizar_ahora_nunca_500(client, factory, auth_header):
    """202 si Airflow aceptó el disparo, 409 si ya había una corrida en curso,
    503 si Airflow no responde (contrato `pipeline-estado.openapi.yaml`) — lo
    que nunca debe pasar es un 500, esté o no 012 levantada en el entorno."""
    rol = factory.gerencia()
    u = factory.usuario(roles=[rol])
    r = client.post("/reportes/actualizar-ahora", headers=auth_header(u))
    assert r.status_code in (202, 409, 503)


def test_reportes_exige_permiso_del_modulo(client, factory, auth_header):
    """Un rol sin el módulo `reportes` (p. ej. Vendedor) recibe 403, no 200/500."""
    rol = factory.rol("Vendedor")
    factory.permitir(rol, "ventas", ["crear", "consultar"])
    u = factory.usuario(roles=[rol])
    r = client.get("/reportes/estado-frescura", headers=auth_header(u))
    assert r.status_code == 403
