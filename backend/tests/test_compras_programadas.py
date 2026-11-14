"""Compras programadas (US5 — módulo con lógica): activa+vencida genera 1 borrador
y avanza fecha; pausada no genera; puntual no genera recurrencia."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from proveedores import repository, service
from proveedores.schemas import CompraProgramadaIn, LineaIn, ProveedorIn


def _programada(db, factory, *, vencida=True):
    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(db, ProveedorIn(razon_social="Prog"), actor=actor).id
    prox = datetime.now(timezone.utc) - timedelta(hours=1) if vencida else datetime.now(timezone.utc) + timedelta(days=10)
    p = service.crear_programada(
        db,
        CompraProgramadaIn(
            proveedor_id=pid, sucursal_destino_id=sid, frecuencia="mensual",
            plantilla_lineas=[LineaIn(item_tipo="pieza", item_ref="9010", cantidad=10, costo_unitario=45)],
            proxima_generacion=prox,
        ),
        actor=actor,
    )
    return actor, p


def test_activa_vencida_genera_un_borrador_y_avanza(db, factory):
    actor, p = _programada(db, factory, vencida=True)
    antes = repository.obtener_programada(db, p.id).proxima_generacion

    n = service.generar_programadas_vencidas(db, actor=actor)
    assert n == 1

    ordenes, total = service.listar_ordenes(db, proveedor_id=p.proveedor_id, tipo="programada", estado="borrador", offset=0, limit=10)
    assert total == 1
    assert ordenes[0].lineas[0].item_ref == "9010"
    despues = repository.obtener_programada(db, p.id).proxima_generacion
    assert despues > antes

    # segunda corrida inmediata: ya no está vencida
    assert service.generar_programadas_vencidas(db, actor=actor) == 0


def test_plantilla_conserva_el_detalle_completo_de_las_lineas(db, factory):
    """La plantilla (JSONB) y la orden generada llevan marca/calibre/año/observaciones
    del reloj y unidad/marca-compatible de la pieza — igual que una OC normal."""
    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(db, ProveedorIn(razon_social="Prog rica"), actor=actor).id
    p = service.crear_programada(
        db,
        CompraProgramadaIn(
            proveedor_id=pid, sucursal_destino_id=sid, frecuencia="mensual",
            proxima_generacion=datetime.now(timezone.utc) - timedelta(hours=1),
            plantilla_lineas=[
                LineaIn(item_tipo="reloj", item_ref="116500LN", marca="Rolex",
                        calibre_codigo="4130", anio=2024, observaciones="para vitrina", cantidad=1),
                LineaIn(item_tipo="pieza", item_ref="ACEITE-9010", descripcion="Aceite 9010",
                        pieza_tipo="original", unidad_medida="ml", marca_compatible="universal",
                        cantidad=2, costo_unitario=40),
            ],
        ),
        actor=actor,
    )
    plantilla = repository.obtener_programada(db, p.id).plantilla_lineas
    assert plantilla[0]["marca"] == "Rolex" and plantilla[0]["observaciones"] == "para vitrina"
    assert plantilla[1]["unidad_medida"] == "ml"

    assert service.generar_programadas_vencidas(db, actor=actor) == 1
    ordenes, _ = service.listar_ordenes(db, proveedor_id=pid, tipo="programada", estado="borrador", offset=0, limit=10)
    lineas = {l.item_tipo: l for l in ordenes[0].lineas}
    assert lineas["reloj"].marca == "Rolex" and lineas["reloj"].calibre_codigo == "4130"
    assert lineas["reloj"].anio == 2024 and lineas["reloj"].observaciones == "para vitrina"
    assert lineas["reloj"].costo_unitario is None
    assert lineas["pieza"].unidad_medida == "ml" and lineas["pieza"].marca_compatible == "universal"
    assert lineas["pieza"].costo_unitario == 40


def test_pausada_no_genera(db, factory):
    actor, p = _programada(db, factory, vencida=True)
    service.set_estado_programada(db, p.id, "pausada", actor=actor)
    assert service.generar_programadas_vencidas(db, actor=actor) == 0


def test_orden_puntual_no_crea_recurrencia(db, factory):
    from datetime import date

    from proveedores.schemas import OrdenCompraIn

    actor = factory.usuario().id
    sid = factory.sucursal().id
    pid = service.crear(db, ProveedorIn(razon_social="Puntual"), actor=actor).id
    o = service.crear_orden(
        db, OrdenCompraIn(proveedor_id=pid, sucursal_destino_id=sid,
                          lineas=[LineaIn(item_tipo="pieza", item_ref="x", cantidad=1, costo_unitario=1)]),
        actor=actor,
    )
    assert o.tipo == "puntual"
    assert service.listar_programadas(db) == [] or all(
        pr.proveedor_id != pid for pr in service.listar_programadas(db)
    )
