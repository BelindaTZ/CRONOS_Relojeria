"""Feature 005 — recálculo en cascada del bono (US3, FR-011).

**Crítico (Const. Ppio IX + "Parámetros configurables — recálculo en cascada")**:
cambiar `horas_productivas_estandar_mes` recalcula los bonos de periodos ABIERTOS
(cambia el prorrateo por costo de MO); un periodo CERRADO conserva su valor.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from shared.guard import CurrentUser
from shared.parametros import set_parametro
from tecnicos import service as tec
from tecnicos.schemas import ComponenteBonoIn, CostoIn, PeriodoIn, ReglaBonoIn, TecnicoIn


def _jefe(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def test_cambiar_horas_estandar_recalcula_solo_periodos_abiertos(db, factory, ot_fixture):
    jefe = _jefe(factory)
    tec.registrar_consumidores()  # engancha el consumidor de `shared/parametros`

    t1 = tec.crear(db, TecnicoIn(nombre="T1"), actor=jefe.id)
    tec.set_costo(db, t1.id, CostoIn(sueldo_mensual=Decimal("1600"), vigente_desde=date(2026, 1, 1)), user=jefe)
    ot_fixture.instalar({"t1": t1.id})
    tec.crear_regla(
        db, ReglaBonoIn(nombre="Regla", vigente_desde=date(2026, 9, 1),
                        componentes=[ComponenteBonoIn(tipo="monto_por_meta", indicador="ot_completadas", umbral=20, valor=200)]),
        actor=jefe.id,
    )

    cerrado = tec.crear_periodo(db, PeriodoIn(fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 9, 30)), actor=jefe.id)
    tec.calcular_bono(db, periodo_id=cerrado.id)
    tec.cerrar_periodo(db, cerrado.id, actor=jefe.id)
    bono_cerrado_antes = [b for b in tec.listar_bonos(db, periodo_id=cerrado.id, tecnico_id=t1.id)][0]
    ot_cerrado_antes = sorted(o.monto for o in bono_cerrado_antes.bono_ot)

    abierto = tec.crear_periodo(db, PeriodoIn(fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 31)), actor=jefe.id)
    tec.calcular_bono(db, periodo_id=abierto.id)

    # cambia el parámetro → dispara el recálculo en cascada
    set_parametro(db, clave="horas_productivas_estandar_mes", valor=170, actor=jefe.id)

    # el periodo cerrado NO cambia
    bono_cerrado_despues = [b for b in tec.listar_bonos(db, periodo_id=cerrado.id, tecnico_id=t1.id)][0]
    assert bono_cerrado_despues.valor_total == bono_cerrado_antes.valor_total
    assert sorted(o.monto for o in bono_cerrado_despues.bono_ot) == ot_cerrado_antes
    assert bono_cerrado_despues.estado == "definitivo"

    # el periodo abierto SÍ se recalculó (nueva tarifa horaria)
    bono_abierto = [b for b in tec.listar_bonos(db, periodo_id=abierto.id, tecnico_id=t1.id)][0]
    assert bono_abierto.estado == "preliminar"
    assert Decimal(str(bono_abierto.desglose["indicadores"]["ot_completadas"])) == 1  # 1 OT en octubre (fixture 2001)
