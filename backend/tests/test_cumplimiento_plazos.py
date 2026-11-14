"""Cumplimiento de plazos (US4 — módulo con cálculo): a tiempo / +2 / +5 días →
indicador y nota_plazos esperados; nota_calidad/nota_soporte intactas."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from proveedores import repository, service
from proveedores.schemas import LineaIn, OrdenCompraIn, ProveedorIn, RecepcionIn, RecepcionLineaIn


def _recepcion(db, factory, actor, sid, pid, desfase_dias: int):
    pactada = date(2026, 9, 20)
    o = service.crear_orden(
        db,
        OrdenCompraIn(proveedor_id=pid, sucursal_destino_id=sid, fecha_pactada=pactada,
                      lineas=[LineaIn(item_tipo="pieza", item_ref="9010", cantidad=1, costo_unitario=10)]),
        actor=actor,
    )
    service.emitir_orden(db, o.id, actor=actor)
    service.confirmar_orden(db, o.id, user=factory.current_user(gerencia=True))
    service.registrar_recepcion(
        db, o.id,
        RecepcionIn(fecha_real=pactada + timedelta(days=desfase_dias),
                    lineas=[RecepcionLineaIn(linea_orden_compra_id=o.lineas[0].id, cantidad_recibida=1)]),
        actor=actor,
    )


def test_indicador_es_promedio_y_nota_plazos_derivada(db, factory):
    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(db, ProveedorIn(razon_social="Prov P"), actor=actor).id

    for d in (0, 2, 5):
        _recepcion(db, factory, actor, sid, pid, d)

    p = repository.obtener(db, pid)
    assert p.indicador_plazos_dias == Decimal("2.33")  # (0+2+5)/3

    cal = service.calificar(db, pid, nota_calidad=Decimal("4"), nota_soporte=Decimal("5"), actor=actor)
    # indicador 2.33 → tramo <=5 → nota_plazos 3.0
    assert cal.nota_plazos == Decimal("3.0")
    assert cal.nota_calidad == Decimal("4.0")
    assert cal.nota_soporte == Decimal("5.0")


def test_recepcion_a_tiempo_da_nota_maxima(db, factory):
    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(db, ProveedorIn(razon_social="Prov P2"), actor=actor).id
    _recepcion(db, factory, actor, sid, pid, 0)
    cal = service.calificar(db, pid, nota_calidad=None, nota_soporte=None, actor=actor)
    assert cal.nota_plazos == Decimal("5.0")


def test_calificacion_manual_no_altera_plazos(db, factory):
    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(db, ProveedorIn(razon_social="Prov P3"), actor=actor).id
    _recepcion(db, factory, actor, sid, pid, 8)  # indicador 8 → tramo <=10 → 2.0
    cal = service.calificar(db, pid, nota_calidad=Decimal("1"), nota_soporte=Decimal("1"), actor=actor)
    assert cal.nota_plazos == Decimal("2.0")
