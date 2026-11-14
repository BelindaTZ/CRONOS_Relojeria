"""Feature 005 — esquema de bono por productividad configurable (US2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from shared.guard import CurrentUser
from tecnicos import service as tec
from tecnicos.schemas import ComponenteBonoIn, ReglaBonoIn


def _jefe(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def test_regla_vigente_y_auditada_con_componentes(db, factory):
    jefe = _jefe(factory)
    r = tec.crear_regla(
        db,
        ReglaBonoIn(
            nombre="Bono 2026", periodicidad="mensual", vigente_desde=date(2026, 9, 1),
            componentes=[
                ComponenteBonoIn(tipo="monto_por_meta", indicador="ot_completadas", umbral=20, valor=200),
                ComponenteBonoIn(tipo="porcentaje_margen", indicador="margen_generado", umbral=0, valor=Decimal("0.05")),
            ],
        ),
        actor=jefe.id,
    )
    assert r.activa and len(r.componentes) == 2
    assert {c.indicador for c in r.componentes} == {"ot_completadas", "margen_generado"}

    from shared.models import RegistroAuditoria

    audit = db.query(RegistroAuditoria).filter_by(entidad="regla_bono", entidad_id=str(r.id)).all()
    assert audit and audit[0].accion == "crear"


def test_una_regla_nueva_desactiva_la_anterior(db, factory):
    jefe = _jefe(factory)
    r1 = tec.crear_regla(
        db, ReglaBonoIn(nombre="v1", componentes=[ComponenteBonoIn(tipo="monto_por_meta", indicador="ot_completadas", umbral=10, valor=100)]),
        actor=jefe.id,
    )
    r2 = tec.crear_regla(
        db, ReglaBonoIn(nombre="v2", componentes=[ComponenteBonoIn(tipo="monto_por_meta", indicador="ot_completadas", umbral=15, valor=150)]),
        actor=jefe.id,
    )
    reglas = {x.id: x for x in tec.listar_reglas(db)}
    assert reglas[r1.id].activa is False
    assert reglas[r2.id].activa is True
