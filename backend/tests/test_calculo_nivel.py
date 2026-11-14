"""Feature 006 — motor de nivel de fidelización (US2, US3).

**Crítico (Const. Ppio IX)**: el nivel calculado debe coincidir con el cálculo
manual sobre fixtures; sube tras una venta; no duplica el historial si no cambia;
el recálculo masivo conserva el historial.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from clientes import repository
from clientes import service as cli
from clientes.nivel import NivelRegla, TransaccionInfo, calcular_nivel
from clientes.schemas import ClienteIn, ConsentimientoIn, NivelIn, ReglaNivelIn
from shared.guard import CurrentUser


def _gg(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def _cliente(db, factory, ident, nombre):
    return cli.crear(db, ClienteIn(tipo="natural", identificacion=ident, nombre=nombre,
                                   consentimiento=ConsentimientoIn(aceptado=True, version_texto=1)),
                     actor=factory.usuario().id)


def _niveles_estandar(db, gg):
    cli.crear_nivel(db, NivelIn(nombre="Plata", orden=2, beneficios={"desc_servicio": 0.1},
                                regla=ReglaNivelIn(criterio="monto_acumulado", ventana_meses=12, umbral_monto=Decimal("3000"))),
                    actor=gg.id)
    cli.crear_nivel(db, NivelIn(nombre="Oro", orden=3, beneficios={"desc_servicio": 0.2},
                                regla=ReglaNivelIn(criterio="combinacion", ventana_meses=12,
                                                   umbral_monto=Decimal("15000"), umbral_frecuencia=3)),
                    actor=gg.id)


# ---------- función pura ----------
def test_calcular_nivel_puro_elige_el_de_mayor_orden_que_cumple():
    niveles = [
        NivelRegla(nivel_id=1, orden=1, es_base=True, criterio=None, ventana_meses=12, umbral_monto=None, umbral_frecuencia=None),
        NivelRegla(nivel_id=2, orden=2, es_base=False, criterio="monto_acumulado", ventana_meses=12, umbral_monto=Decimal("3000"), umbral_frecuencia=None),
        NivelRegla(nivel_id=3, orden=3, es_base=False, criterio="frecuencia", ventana_meses=12, umbral_monto=None, umbral_frecuencia=4),
    ]
    hoy = date(2026, 9, 1)
    txs = [TransaccionInfo(fecha=date(2026, m, 1), monto=Decimal("1000"), tipo="venta") for m in range(2, 6)]
    # 4 tx, 4000 acumulado → cumple monto (nivel 2) y frecuencia (nivel 3) → gana el 3
    assert calcular_nivel(txs, niveles, hoy=hoy) == 3
    # solo 2 tx de 2000 → ni monto ni frecuencia → base
    assert calcular_nivel(txs[:2], niveles, hoy=hoy) == 1
    # fuera de ventana no cuenta
    viejas = [TransaccionInfo(fecha=date(2020, 1, 1), monto=Decimal("99999"), tipo="venta")]
    assert calcular_nivel(viejas, niveles, hoy=hoy) == 1


# ---------- integración con fixtures ----------
def test_clientes_de_prueba_se_clasifican_bien(db, factory, tx_fixture):
    gg = _gg(factory)
    _niveles_estandar(db, gg)
    frec = _cliente(db, factory, "1710000010", "Cliente Frecuente")
    ocas = _cliente(db, factory, "1710000011", "Cliente Ocasional")
    vip = _cliente(db, factory, "1710000012", "Cliente VIP")
    tx_fixture.instalar({"c_frecuente": frec.id, "c_ocasional": ocas.id, "c_vip": vip.id})

    assert cli.recalcular_nivel(db, cliente_id=frec.id).nivel_nuevo == "Plata"   # ~5800 en 12m
    assert cli.recalcular_nivel(db, cliente_id=ocas.id).nivel_nuevo == "Bronce"  # solo 450 en ventana
    assert cli.recalcular_nivel(db, cliente_id=vip.id).nivel_nuevo == "Oro"      # 17700 y 3 tx


def test_sube_de_nivel_tras_una_venta_y_registra_el_hecho(db, factory):
    gg = _gg(factory)
    _niveles_estandar(db, gg)
    c = _cliente(db, factory, "1710000020", "Sube Nivel")

    ventas = []

    def _prov(_db, cliente_id):
        return [x for x in ventas if x.cliente_id == cliente_id]

    cli.registrar_proveedor_transacciones(_prov)
    try:
        # aún sin ventas → Bronce
        assert cli.recalcular_nivel(db, cliente_id=c.id).cambio is False

        ventas.append(cli.TransaccionCliente(cliente_id=c.id, fecha=date.today(), monto=Decimal("4000"), tipo="venta", documento_id=88))
        r = cli.recalcular_nivel(db, cliente_id=c.id, hecho="venta", documento_id=88)
        assert r.cambio is True and r.nivel_nuevo == "Plata"

        hist = repository.historial_nivel(db, c.id)
        assert len(hist) == 1 and hist[0].hecho_disparador == "venta" and hist[0].documento_id == 88

        # recalcular otra vez sin cambio → no duplica el historial
        assert cli.recalcular_nivel(db, cliente_id=c.id, hecho="venta").cambio is False
        assert len(repository.historial_nivel(db, c.id)) == 1
    finally:
        cli._PROVEEDORES_TX.clear()


def test_recalculo_masivo_al_cambiar_regla_conserva_historial(db, factory, tx_fixture):
    gg = _gg(factory)
    _niveles_estandar(db, gg)
    frec = _cliente(db, factory, "1710000030", "Frecuente 2")
    tx_fixture.instalar({"c_frecuente": frec.id})
    cli.recalcular_nivel(db, cliente_id=frec.id)  # → Plata
    assert len(repository.historial_nivel(db, frec.id)) == 1

    # bajar el umbral de Oro por debajo de su acumulado (~5800) → recálculo masivo lo sube
    oro = repository.por_nombre_nivel(db, "Oro")
    cli.set_regla_nivel(db, oro.id, ReglaNivelIn(criterio="monto_acumulado", ventana_meses=12,
                                                 umbral_monto=Decimal("5000")), actor=gg.id)
    db.refresh(repository.obtener(db, frec.id))
    assert repository.obtener(db, frec.id).nivel_fidelizacion_id == oro.id
    # el historial previo (Bronce→Plata) sigue ahí + el nuevo (Plata→Oro)
    assert len(repository.historial_nivel(db, frec.id)) == 2
