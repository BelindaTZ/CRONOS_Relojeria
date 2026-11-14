"""Feature 005 — vista operativa de productividad por técnico (US5)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from shared.guard import CurrentUser
from tecnicos import service as tec
from tecnicos.schemas import ComponenteBonoIn, CostoIn, PeriodoIn, ReglaBonoIn, TecnicoIn


def _jefe(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def test_productividad_coincide_con_las_ot(db, factory, ot_fixture):
    jefe = _jefe(factory)
    t1 = tec.crear(db, TecnicoIn(nombre="Productivo"), actor=jefe.id)
    tec.set_costo(db, t1.id, CostoIn(sueldo_mensual=Decimal("1600"), vigente_desde=date(2026, 1, 1)), user=jefe)
    ot_fixture.instalar({"t1": t1.id})
    tec.crear_regla(
        db, ReglaBonoIn(nombre="Regla", vigente_desde=date(2026, 9, 1),
                        componentes=[ComponenteBonoIn(tipo="monto_por_meta", indicador="ot_completadas", umbral=20, valor=200)]),
        actor=jefe.id,
    )
    periodo = tec.crear_periodo(db, PeriodoIn(fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 9, 30)), actor=jefe.id)
    tec.calcular_bono(db, periodo_id=periodo.id)

    prod = {p.tecnico_id: p for p in tec.productividad(db, periodo_id=periodo.id)}
    p1 = prod[t1.id]
    assert p1.ot_completadas == 22
    assert p1.tiempo_promedio_horas == 2.0        # todas registran 2 h
    assert p1.margen_generado == Decimal("1100.00")
    assert p1.bono_alcanzado == Decimal("200.00")  # 22 ≥ 20


def test_productividad_endpoint_y_permiso(client, factory, auth_header):
    jefe = factory.usuario(roles=[factory.gerencia()])
    r = client.post("/tecnicos", json={"nombre": "Vista"}, headers=auth_header(jefe))
    tid = r.json()["id"]
    per = client.post("/periodos-liquidacion", json={"fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-30"},
                      headers=auth_header(jefe)).json()
    r = client.get(f"/productividad?periodo_id={per['id']}", headers=auth_header(jefe))
    assert r.status_code == 200
    fila = [f for f in r.json() if f["tecnico_id"] == tid][0]
    assert fila["ot_completadas"] == 0 and Decimal(fila["bono_alcanzado"]) == 0
