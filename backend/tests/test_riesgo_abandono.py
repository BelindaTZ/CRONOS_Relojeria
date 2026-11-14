"""Feature 006 (ampliación) — análisis de riesgo de abandono de clientes.

Solo niveles con valor (no base). En riesgo si el silencio supera N× la cadencia
mediana propia Y un piso mínimo de días. Historial mínimo para tener patrón.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from clientes import service as cli
from clientes.riesgo import TransaccionRiesgo, analizar
from clientes.schemas import (
    ClienteIn,
    ConsentimientoIn,
    CuponReactivacionIn,
    NivelIn,
    ReglaNivelIn,
)
from shared.guard import CurrentUser


def _gg(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


# ---------- función pura ----------
def test_analizar_marca_solo_cuando_pasa_piso_y_factor():
    hoy = date(2026, 9, 1)
    # compra cada ~30 días, última hace 40 días → dentro de patrón (< 2×30) y < piso 90 → None
    txs = [TransaccionRiesgo(fecha=hoy - timedelta(days=d)) for d in (200, 170, 140, 110, 80, 40)]
    assert analizar(txs, hoy=hoy) is None

    # cadencia ~30, última hace 100 días → 100 > 90 (piso) y 100 > 60 (2×30) → en riesgo;
    # ratio 100/30 ≈ 3,3 (< 4 = 2×factor) → severidad "atencion"
    txs2 = [TransaccionRiesgo(fecha=hoy - timedelta(days=d)) for d in (250, 220, 190, 160, 130, 100)]
    r = analizar(txs2, hoy=hoy)
    assert r is not None and r.dias_silencio == 100
    assert 29 <= r.cadencia_dias <= 31
    assert r.severidad == "atencion"

    # silencio enorme (> 4×cadencia) → crítico
    txs3 = [TransaccionRiesgo(fecha=hoy - timedelta(days=d)) for d in (400, 370, 340, 310)]
    r3 = analizar(txs3, hoy=hoy)
    assert r3 and r3.severidad == "critico"


def test_analizar_exige_historial_minimo():
    hoy = date(2026, 9, 1)
    txs = [TransaccionRiesgo(fecha=hoy - timedelta(days=d)) for d in (300, 150)]  # solo 2
    assert analizar(txs, hoy=hoy, min_transacciones=3) is None


# ---------- integración ----------
def test_reporte_clientes_en_riesgo_solo_niveles_con_valor(db, factory):
    gg = _gg(factory)
    cli.crear_nivel(db, NivelIn(nombre="Plata", orden=2, beneficios={},
                                regla=ReglaNivelIn(criterio="monto_acumulado", ventana_meses=12, umbral_monto=Decimal("1000"))),
                    actor=gg.id)

    en_riesgo = cli.crear(db, ClienteIn(tipo="natural", identificacion="1710500001", nombre="Silenciosa Plata",
                                        consentimiento=ConsentimientoIn(aceptado=True, version_texto=1)), actor=gg.id)
    al_dia = cli.crear(db, ClienteIn(tipo="natural", identificacion="1710500002", nombre="Al Día Plata",
                                     consentimiento=ConsentimientoIn(aceptado=True, version_texto=1)), actor=gg.id)
    bronce = cli.crear(db, ClienteIn(tipo="natural", identificacion="1710500003", nombre="Silencioso Bronce",
                                     consentimiento=ConsentimientoIn(aceptado=True, version_texto=1)), actor=gg.id)

    hoy = date.today()
    hist = {
        en_riesgo.id: [hoy - timedelta(days=d) for d in (300, 270, 240, 210, 180)],   # silencio 180, cadencia ~30
        al_dia.id: [hoy - timedelta(days=d) for d in (300, 270, 240, 210, 20)],        # última hace 20 d
        bronce.id: [hoy - timedelta(days=d) for d in (300, 270, 240, 210, 180)],       # silencioso pero Bronce
    }

    def _prov(_db, cliente_id):
        return [cli.TransaccionCliente(cliente_id=cliente_id, fecha=f, monto=Decimal("500"), tipo="venta")
                for f in hist.get(cliente_id, [])]

    cli.registrar_proveedor_transacciones(_prov)
    try:
        # subir a Plata a los dos primeros
        plata = cli.repository.por_nombre_nivel(db, "Plata")
        for cid in (en_riesgo.id, al_dia.id):
            c = cli.repository.obtener(db, cid)
            c.nivel_fidelizacion_id = plata.id
        db.flush()

        riesgo = cli.clientes_en_riesgo(db)
        ids = {r.cliente_id for r in riesgo}
        assert en_riesgo.id in ids
        assert al_dia.id not in ids     # compró hace 20 días
        assert bronce.id not in ids     # nivel base no se analiza

        # emitir cupón de reactivación desde el reporte
        cupon = cli.emitir_cupon_reactivacion(
            db, CuponReactivacionIn(cliente_id=en_riesgo.id, tipo="porcentaje", valor=Decimal("0.15")), actor=gg.id
        )
        assert cupon.codigo.startswith("REACT-") and cupon.limite_uso == "una_vez"
    finally:
        cli._PROVEEDORES_TX.clear()
