"""Feature 012, US1 (T008): la app operativa (000-011) no depende de ClickHouse
ni de Airflow para funcionar (Spec §FR-011, Const. Ppio III). En el entorno de
tests ninguno de los dos servicios existe — si algo del arranque o de un
endpoint operativo los tocara, estos tests fallarían por timeout/error."""
from __future__ import annotations


def test_health_no_depende_de_clickhouse_ni_airflow(client):
    r = client.get("/health")
    assert r.status_code in (200, 503)  # 503 solo si PostgreSQL/MinIO fallan — nunca por 012
    assert "clickhouse" not in r.text.lower()
    assert "airflow" not in r.text.lower()


def test_endpoint_operativo_normal_sigue_vivo(client, factory, auth_header):
    """Un endpoint cualquiera de una feature operativa (001) responde normal —
    demuestra que el arranque del backend no abrió conexión a 012."""
    rol = factory.gerencia()
    u = factory.usuario(roles=[rol])
    r = client.get("/sucursales", headers=auth_header(u))
    assert r.status_code == 200
