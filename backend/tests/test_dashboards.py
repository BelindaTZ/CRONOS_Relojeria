"""Feature 013 (dashboards y reportes) — fachada de lectura sobre el warehouse
de 012. El entorno de tests no tiene ClickHouse alcanzable (mismo criterio que
012): estos tests cubren gating RBAC, scope, degradación limpia y el catálogo,
no cifras reales (esas se verificaron a mano contra el stack real — ver
CONVENCIONES.md §26)."""
from __future__ import annotations

from dashboards.warehouse import CATALOGO


def test_catalogo_cubre_los_18_reportes():
    assert len(CATALOGO) == 18


def test_panel_solo_gerencia_general(client, factory, auth_header):
    rol = factory.rol("Gerente de Sucursal")
    suc = factory.sucursal()
    u = factory.usuario(roles=[rol], sucursales=[suc])
    r = client.get("/panel?periodo=2026-09", headers=auth_header(u))
    assert r.status_code == 403


def test_panel_gerencia_general_degrada_limpio_sin_clickhouse(client, factory, auth_header):
    rol = factory.gerencia()
    u = factory.usuario(roles=[rol])
    r = client.get("/panel?periodo=2026-09", headers=auth_header(u))
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["disponible"], bool)
    if not body["disponible"]:
        assert body["kpis"] == []
        assert body["motivo"]


def test_reporte_analitico_exige_permiso_reportes(client, factory, auth_header):
    rol = factory.rol("Vendedor")
    u = factory.usuario(roles=[rol])
    r = client.get("/reportes/analitico/mermas-perdidas", headers=auth_header(u))
    assert r.status_code == 403


def test_reporte_analitico_slug_desconocido_404(client, factory, auth_header):
    rol = factory.gerencia()
    u = factory.usuario(roles=[rol])
    r = client.get("/reportes/analitico/no-existe", headers=auth_header(u))
    assert r.status_code == 404


def test_reporte_analitico_degrada_limpio_nunca_500(client, factory, auth_header):
    rol = factory.gerencia()
    u = factory.usuario(roles=[rol])
    r = client.get("/reportes/analitico/margen-por-marca-modelo?periodo=2026-09", headers=auth_header(u))
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["disponible"], bool)
    if body["disponible"]:
        assert body["slug"] == "margen-por-marca-modelo"
        assert body["tipo_grafico"] == "barras"


def test_reporte_analitico_gerente_sucursal_no_puede_pedir_otra_sucursal(client, factory, auth_header):
    rol = factory.rol("Gerente de Sucursal")
    suc = factory.sucursal()
    otra = factory.sucursal()
    u = factory.usuario(roles=[rol], sucursales=[suc])
    r = client.get(f"/reportes/analitico/valor-total-inventario?sucursal_id={otra.id}", headers=auth_header(u))
    assert r.status_code == 403


def test_indice_abierto_a_cualquier_autenticado_pero_filtra_complejos(client, factory, auth_header):
    rol = factory.rol("Vendedor")
    u = factory.usuario(roles=[rol])
    r = client.get("/reportes/indice", headers=auth_header(u))
    assert r.status_code == 200
    body = r.json()
    assert body["simples"]  # el vendedor ve al menos algún reporte simple permitido
    assert body["complejos"] == []  # sin "reportes:consultar", no ve los analíticos


def test_indice_gerencia_ve_los_18_complejos(client, factory, auth_header):
    rol = factory.gerencia()
    u = factory.usuario(roles=[rol])
    r = client.get("/reportes/indice", headers=auth_header(u))
    assert r.status_code == 200
    assert len(r.json()["complejos"]) == 18
