"""Cliente de solo lectura del warehouse analítico (ClickHouse, feature 012).

Usado por `reportes_estado` (012) y `dashboards` (013) — ambos leen el mismo
warehouse, así que la conexión vive aquí (Ppio X: código compartido entre
2+ módulos vive en `shared/`, nunca duplicado). Import perezoso: ningún
módulo abre esta conexión al arrancar (research 012-D7, Spec 013 FR-016).
"""

from __future__ import annotations

from shared.config import get_settings


def get_client(*, connect_timeout: float = 3.0, send_receive_timeout: float = 8.0):
    """Cliente `clickhouse-connect`. Lanza si no hay conexión — el llamante
    decide cómo degradar (nunca se llama en el arranque ni en `/health`)."""
    import clickhouse_connect

    s = get_settings()
    return clickhouse_connect.get_client(
        host=s.clickhouse_host,
        port=s.clickhouse_http_port,
        username=s.clickhouse_user,
        password=s.clickhouse_password,
        database=s.clickhouse_db,
        connect_timeout=connect_timeout,
        send_receive_timeout=send_receive_timeout,
    )
