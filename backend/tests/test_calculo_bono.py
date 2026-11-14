"""Feature 005 — motor de cálculo del bono acumulado (US3).

**Crítico (Const. Ppio IX)**: el motor debe dar el mismo resultado que el cálculo
manual sobre un set de OT de prueba; el bono nunca es negativo; el prorrateo suma
exactamente el `valor_total`.
"""

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


def _setup(db, factory, ot_fixture):
    jefe = _jefe(factory)
    t1 = tec.crear(db, TecnicoIn(nombre="Técnico 1"), actor=jefe.id)
    t2 = tec.crear(db, TecnicoIn(nombre="Técnico 2 (sin OT)"), actor=jefe.id)
    tec.set_costo(db, t1.id, CostoIn(sueldo_mensual=Decimal("1600"), vigente_desde=date(2026, 1, 1)), user=jefe)
    tec.set_costo(db, t2.id, CostoIn(sueldo_mensual=Decimal("1600"), vigente_desde=date(2026, 1, 1)), user=jefe)
    ot_fixture.instalar({"t1": t1.id})  # t2 no tiene OT
    periodo = tec.crear_periodo(db, PeriodoIn(fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 9, 30)), actor=jefe.id)
    return jefe, t1, t2, periodo


def test_bono_22_ot_mas_porcentaje_margen(db, factory, ot_fixture):
    jefe, t1, t2, periodo = _setup(db, factory, ot_fixture)
    tec.crear_regla(
        db,
        ReglaBonoIn(
            nombre="Bono 2026", vigente_desde=date(2026, 9, 1),
            componentes=[
                ComponenteBonoIn(tipo="monto_por_meta", indicador="ot_completadas", umbral=20, valor=200),
                ComponenteBonoIn(tipo="porcentaje_margen", indicador="margen_generado", umbral=0, valor=Decimal("0.05")),
            ],
        ),
        actor=jefe.id,
    )
    bonos = {b.tecnico_id: b for b in tec.calcular_bono(db, periodo_id=periodo.id)}

    # 22 OT en septiembre, margen 22×50 = 1100 → 200 + 0.05×1100 = 255
    b1 = bonos[t1.id]
    assert b1.valor_total == Decimal("255.00")
    assert b1.estado == "preliminar"
    assert Decimal(str(sum(o.monto for o in b1.bono_ot))) == Decimal("255.00")  # prorrateo exacto
    assert len(b1.bono_ot) == 22
    ind = b1.desglose["indicadores"]
    assert ind["ot_completadas"] == 22.0 and ind["margen_generado"] == 1100.0

    # técnico sin OT → bono 0, sin bono_ot
    assert bonos[t2.id].valor_total == Decimal("0.00")
    assert bonos[t2.id].bono_ot == []


def test_bono_combinacion_y_umbral_no_alcanzado(db, factory, ot_fixture):
    jefe, t1, _, periodo = _setup(db, factory, ot_fixture)
    # umbral 30 OT (no se alcanza con 22) → ese componente no aporta;
    # combinacion sobre calidad (95.45 ≥ 90) → 10 + 10×margen? no: combinacion usa el mismo valor.
    tec.crear_regla(
        db,
        ReglaBonoIn(
            nombre="Combi", vigente_desde=date(2026, 9, 1),
            componentes=[
                ComponenteBonoIn(tipo="monto_por_meta", indicador="ot_completadas", umbral=30, valor=500),
                ComponenteBonoIn(tipo="combinacion", indicador="calidad", umbral=90, valor=Decimal("0.10")),
            ],
        ),
        actor=jefe.id,
    )
    bonos = {b.tecnico_id: b for b in tec.calcular_bono(db, periodo_id=periodo.id)}
    b1 = bonos[t1.id]
    # componente 1 no aporta (22 < 30). componente 2: 0.10 + 0.10×1100 = 110.10
    assert b1.valor_total == Decimal("110.10")
    comp = {c["indicador"]: c for c in b1.desglose["componentes"]}
    assert comp["ot_completadas"]["aporta"] is False
    assert comp["calidad"]["aporta"] is True


def test_sin_ot_no_hay_bono_aunque_un_indicador_por_defecto_supere_su_umbral(db, factory, ot_fixture):
    """FR-010: periodo sin OT ⇒ bono 0. La calidad por defecto es 100 (sin reprocesos),
    pero un componente 'calidad ≥ 95' NO debe pagar si el técnico no trabajó."""
    jefe, _, t2, periodo = _setup(db, factory, ot_fixture)  # t2 no tiene OT
    tec.crear_regla(
        db,
        ReglaBonoIn(
            nombre="Calidad", vigente_desde=date(2026, 9, 1),
            componentes=[ComponenteBonoIn(tipo="monto_por_meta", indicador="calidad", umbral=95, valor=80)],
        ),
        actor=jefe.id,
    )
    b2 = {b.tecnico_id: b for b in tec.calcular_bono(db, periodo_id=periodo.id)}[t2.id]
    assert b2.valor_total == Decimal("0.00")
    assert b2.desglose.get("sin_ot_en_el_periodo") is True


def test_sin_regla_vigente_el_bono_es_cero(db, factory, ot_fixture):
    jefe, t1, _, periodo = _setup(db, factory, ot_fixture)
    bonos = tec.calcular_bono(db, periodo_id=periodo.id, tecnico_id=t1.id)
    assert bonos[0].valor_total == Decimal("0.00")
    assert bonos[0].desglose.get("sin_regla_vigente") is True


def test_cerrar_periodo_marca_bonos_definitivos(db, factory, ot_fixture):
    jefe, t1, _, periodo = _setup(db, factory, ot_fixture)
    tec.crear_regla(
        db, ReglaBonoIn(nombre="Regla", vigente_desde=date(2026, 9, 1),
                        componentes=[ComponenteBonoIn(tipo="monto_por_meta", indicador="ot_completadas", umbral=20, valor=200)]),
        actor=jefe.id,
    )
    tec.calcular_bono(db, periodo_id=periodo.id)
    tec.cerrar_periodo(db, periodo.id, actor=jefe.id)
    b1 = [b for b in tec.listar_bonos(db, periodo_id=periodo.id, tecnico_id=t1.id)][0]
    assert b1.estado == "definitivo" and b1.valor_total == Decimal("200.00")
