"""Feature 008 — órdenes de trabajo: ciclo de estados, presupuesto, costeo/margen
(Const. Ppio IX, cobertura obligatoria), cobro al retiro y entrega, y scoping
"solo las propias" del técnico.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from shared.exceptions import ConflictError, ValidationError
from shared.guard import CurrentUser


# --------------------------------------------------------------- mundo de prueba
@pytest.fixture
def mundo(db, factory):
    from clientes import repository as cli_repo
    from inventario.models import Calibre, EventoSerie, Reloj
    from tecnicos import service as tec

    suc = factory.sucursal("Taller 008")
    jefe_u = factory.usuario(roles=[factory.gerencia()], sucursales=[suc])
    jefe = CurrentUser(id=jefe_u.id, identificacion=jefe_u.identificacion, nombre=jefe_u.nombre,
                       email=jefe_u.email, estado="activo", token_scope="full",
                       roles=["Gerencia General"], rol_ids=[], sucursal_ids=[suc.id])

    cal = Calibre(codigo="Rolex 3235")
    db.add(cal)
    db.flush()

    reloj = Reloj(numero_serie="RLX-3235-001", marca="Rolex", referencia="126610LN",
                  calibre_id=cal.id, sucursal_actual_id=suc.id, disponibilidad="disponible")
    db.add(reloj)
    db.flush()
    db.add(EventoSerie(numero_serie="RLX-3235-001", reloj_id=reloj.id, tipo="venta",
                       documento_tipo="venta", documento_id=1))
    db.flush()

    base = cli_repo.nivel_base(db)
    cliente = cli_repo.crear(
        db, tipo="natural", identificacion="0102030405", numero_afiliado=cli_repo.siguiente_afiliado(db),
        nombre="Cliente 008", telefono=None, email="cliente008@test.local", direccion=None,
        fecha_nacimiento=None, preferencias=None, notas=None,
        nivel_fidelizacion_id=base.id if base else None, estado="activo",
    )

    from tecnicos.schemas import CostoIn, TecnicoIn

    tecnico_u = factory.usuario(sucursales=[suc])
    t = tec.crear(db, TecnicoIn(nombre="Ana Téc", usuario_id=tecnico_u.id,
                                especialidades_nuevas=["Rolex 3235"], sucursales=[suc.id]), actor=jefe.id)
    tec.set_costo(db, t.id, CostoIn(sueldo_mensual=Decimal("1600"), vigente_desde=date(2026, 1, 1)), user=jefe)

    tecnico = CurrentUser(id=tecnico_u.id, identificacion=tecnico_u.identificacion, nombre=tecnico_u.nombre,
                          email=tecnico_u.email, estado="activo", token_scope="full",
                          roles=[], rol_ids=[], sucursal_ids=[suc.id])

    return {
        "db": db, "suc": suc, "jefe": jefe, "cliente": cliente, "reloj": reloj,
        "tecnico_user": tecnico, "tecnico_id": t.id, "calibre_id": cal.id,
    }


def _crear_ot(m, *, serie="RLX-3235-001", override=None):
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import OrdenTrabajoIn

    return st.crear_ot(m["db"], OrdenTrabajoIn(
        numero_serie=serie, cliente_id=m["cliente"].id, motivo="No da cuerda",
        tipo_reparacion="servicio_completo", sucursal_id=m["suc"].id,
        override_adquisicion_motivo=override,
    ), user=m["jefe"])


# --------------------------------------------------------------- US1
def test_crear_ot_recibido_sin_fecha_estimada_y_asigna_tecnico(mundo):
    ot = _crear_ot(mundo)
    assert ot.estado == "recibido"
    assert ot.fecha_estimada_entrega is None
    assert ot.tecnico_id == mundo["tecnico_id"]  # sugerido por especialidad + sucursal
    assert ot.numero.startswith("OT-")


def test_ot_sin_venta_previa_exige_autorizacion(mundo):
    from inventario.models import Reloj

    r = Reloj(numero_serie="SIN-VENTA-1", marca="Rolex", referencia="x",
              sucursal_actual_id=mundo["suc"].id, disponibilidad="disponible")
    mundo["db"].add(r)
    mundo["db"].flush()

    with pytest.raises(ValidationError):
        _crear_ot(mundo, serie="SIN-VENTA-1")
    # con override sí procede
    ot = _crear_ot(mundo, serie="SIN-VENTA-1", override="Vendido antes del sistema — verificado con factura")
    assert ot.estado == "recibido"


def test_ot_reloj_en_transito_409(mundo):
    mundo["reloj"].disponibilidad = "en_transito"
    mundo["db"].flush()
    with pytest.raises(ConflictError):
        _crear_ot(mundo)


def test_tecnico_ve_su_ot_aunque_este_en_otra_sucursal(mundo, factory):
    """Bug real reportado por el usuario (2026-09-11): "el técnico no puede ver su
    orden". Causa: el listado intersectaba el scoping de sucursal del técnico con
    "solo sus OT" — si a un técnico se le asigna una unidad registrada en OTRA
    sucursal (p. ej. es el especialista de esa marca en toda la empresa), el AND
    la dejaba invisible aunque fuera 100% suya. El scoping de sucursal es para
    vistas agregadas (Vendedor/Gerente de Sucursal); un técnico ve sus OT
    asignadas sin importar en qué sucursal quedaron registradas."""
    from inventario.models import EventoSerie, Reloj
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import OrdenTrabajoIn

    db = mundo["db"]
    otra_suc = factory.sucursal("Otra sucursal 008")
    reloj2 = Reloj(numero_serie="RLX-3235-002", marca="Rolex", referencia="126610LN",
                   calibre_id=mundo["calibre_id"], sucursal_actual_id=otra_suc.id, disponibilidad="disponible")
    db.add(reloj2)
    db.flush()
    db.add(EventoSerie(numero_serie="RLX-3235-002", reloj_id=reloj2.id, tipo="venta",
                       documento_tipo="venta", documento_id=1))
    db.flush()

    ot1 = _crear_ot(mundo)  # en la sucursal del técnico
    ot2 = st.crear_ot(db, OrdenTrabajoIn(
        numero_serie="RLX-3235-002", cliente_id=mundo["cliente"].id,
        motivo="Correa floja", tipo_reparacion="ajuste_correa",
        sucursal_id=otra_suc.id, tecnico_id=mundo["tecnico_id"],
    ), user=mundo["jefe"])
    assert ot2.sucursal_id == otra_suc.id

    items, total = st.listar(
        db, user=mundo["tecnico_user"], estado=None, tecnico_id=None,
        sucursal_id=None, numero_serie=None, offset=0, limit=50,
    )
    ids = {i.id for i in items}
    assert ot1.id in ids
    assert ot2.id in ids, "el técnico debe ver una OT suya aunque esté registrada en otra sucursal"

    en_curso = st.ot_en_curso(db, user=mundo["tecnico_user"])
    assert ot2.id in {o.id for o in en_curso}


def test_relojes_elegibles_autorellena_cliente_dueno(mundo):
    """Feedback del usuario (2026-09-11): "el campo de número de serie es texto
    libre, debería... autollenarse el cliente dueño del reloj comprado". La unidad
    con una venta confirmada debe aparecer en el catálogo con su dueño real."""
    from servicio_tecnico import service as st
    from ventas import service as vs
    from ventas.schemas import ConfirmarVentaIn, LineaVentaIn, VentaIn

    db = mundo["db"]
    mundo["reloj"].precio_venta = Decimal("5000")
    mundo["reloj"].costo_adquisicion = Decimal("3000")
    db.flush()

    v = vs.crear_venta(
        db, VentaIn(cliente_id=mundo["cliente"].id, lineas=[LineaVentaIn(item_tipo="reloj", reloj_id=mundo["reloj"].id)]),
        user=mundo["jefe"],
    )
    vs.confirmar_venta(db, v.id, ConfirmarVentaIn(), user=mundo["jefe"])

    elegibles = st.relojes_elegibles(db, q="RLX-3235-001")
    assert len(elegibles) == 1
    assert elegibles[0].cliente_id == mundo["cliente"].id
    assert elegibles[0].cliente_nombre == "Cliente 008"


def test_relojes_elegibles_sin_venta_no_trae_cliente(mundo):
    """La ruta de excepción (unidad de alta manual, sin venta registrada aquí) debe
    seguir apareciendo en el catálogo pero SIN cliente auto-rellenado — el vendedor
    lo elige a mano, como hoy."""
    from inventario.models import Reloj
    from servicio_tecnico import service as st

    r = Reloj(numero_serie="SIN-VENTA-2", marca="Rolex", referencia="x",
              sucursal_actual_id=mundo["suc"].id, disponibilidad="disponible")
    db = mundo["db"]
    db.add(r)
    db.flush()

    elegibles = st.relojes_elegibles(db, q="SIN-VENTA-2")
    assert len(elegibles) == 1
    assert elegibles[0].cliente_id is None


def test_presupuesto_usa_precio_de_catalogo_no_costo(mundo):
    """Feedback del usuario (2026-09-11): "las piezas van a estar sin precio...
    no nos vamos a inventar uno para el cliente". Antes, dejar el precio en blanco
    caía silenciosamente al COSTO de adquisición (`costo_pieza`) — el cliente veía
    el precio de compra interno de la tienda, no un precio de venta real."""
    from piezas import service as piezas_svc
    from piezas.schemas import PiezaIn
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import DiagnosticoIn, LineaPresupuestoIn, PresupuestoIn

    db = mundo["db"]
    pieza = piezas_svc.crear(db, PiezaIn(
        codigo="CORONA-TEST", descripcion="Corona genérica", tipo="original",
        costo_adquisicion=Decimal("10"), precio_venta_suelta=Decimal("25"), stock_minimo=0,
    ), actor=mundo["jefe"].id)

    ot = _crear_ot(mundo)
    st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="Corona floja"), user=mundo["jefe"])
    p = st.crear_presupuesto(db, ot.id, PresupuestoIn(
        precio_servicio=Decimal("100"),
        lineas=[LineaPresupuestoIn(pieza_original_id=pieza.id, cantidad=1)],  # sin precio_original: debe usar el catálogo
    ), user=mundo["jefe"])
    assert p.lineas[0].precio_original == Decimal("25.00")  # nunca el costo (10)


def test_presupuesto_sin_precio_catalogo_exige_precio_manual(mundo):
    from piezas import service as piezas_svc
    from piezas.schemas import PiezaIn
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import DiagnosticoIn, LineaPresupuestoIn, PresupuestoIn

    db = mundo["db"]
    pieza = piezas_svc.crear(db, PiezaIn(
        codigo="SIN-PRECIO-TEST", descripcion="Pieza sin precio de catálogo", tipo="original",
        costo_adquisicion=Decimal("10"), stock_minimo=0,
    ), actor=mundo["jefe"].id)

    ot = _crear_ot(mundo)
    st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="Corona floja"), user=mundo["jefe"])
    with pytest.raises(ValidationError):
        st.crear_presupuesto(db, ot.id, PresupuestoIn(
            precio_servicio=Decimal("100"),
            lineas=[LineaPresupuestoIn(pieza_original_id=pieza.id, cantidad=1)],
        ), user=mundo["jefe"])

    # con precio manual sí procede
    p = st.crear_presupuesto(db, ot.id, PresupuestoIn(
        precio_servicio=Decimal("100"),
        lineas=[LineaPresupuestoIn(pieza_original_id=pieza.id, cantidad=1, precio_original=Decimal("18"))],
    ), user=mundo["jefe"])
    assert p.lineas[0].precio_original == Decimal("18")


def test_preferencia_de_pieza_no_admite_mixto(mundo):
    """Feedback del usuario (2026-09-11): "es o originales o no originales, no
    ambas" — una línea de presupuesto es binaria; "mixto" solo tiene sentido para
    describir el presupuesto EN CONJUNTO, nunca la elección de una sola línea."""
    import pydantic
    from servicio_tecnico.schemas import PreferenciaLineaIn

    with pytest.raises(pydantic.ValidationError):
        PreferenciaLineaIn(linea_id=1, preferencia="mixto")


def test_no_se_puede_elegir_no_original_sin_esa_opcion(mundo):
    from piezas import service as piezas_svc
    from piezas.schemas import PiezaIn
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import (
        AprobarPresupuestoIn, DiagnosticoIn, LineaPresupuestoIn, PreferenciaLineaIn, PresupuestoIn,
    )

    db = mundo["db"]
    pieza = piezas_svc.crear(db, PiezaIn(
        codigo="SOLO-ORIGINAL-TEST", descripcion="Pieza solo original", tipo="original",
        costo_adquisicion=Decimal("10"), precio_venta_suelta=Decimal("25"), stock_minimo=0,
    ), actor=mundo["jefe"].id)

    ot = _crear_ot(mundo)
    st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="Corona floja"), user=mundo["jefe"])
    p = st.crear_presupuesto(db, ot.id, PresupuestoIn(
        precio_servicio=Decimal("100"),
        lineas=[LineaPresupuestoIn(pieza_original_id=pieza.id, cantidad=1)],  # sin pieza_no_original_id
    ), user=mundo["jefe"])
    linea_id = p.lineas[0].id

    with pytest.raises(ValidationError):
        st.aprobar_presupuesto(db, ot.id, AprobarPresupuestoIn(
            confirmado_por="Cliente", fecha_estimada_entrega=date.today() + timedelta(days=3),
            preferencias=[PreferenciaLineaIn(linea_id=linea_id, preferencia="no_original")],
        ), user=mundo["jefe"])

    # "original" (la única opción real) sí procede
    d = st.aprobar_presupuesto(db, ot.id, AprobarPresupuestoIn(
        confirmado_por="Cliente", fecha_estimada_entrega=date.today() + timedelta(days=3),
        preferencias=[PreferenciaLineaIn(linea_id=linea_id, preferencia="original")],
    ), user=mundo["jefe"])
    assert d.estado == "en_reparacion"


# --------------------------------------------------------------- US1b + US5
def test_ciclo_diagnostico_presupuesto_reparacion(mundo):
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import AprobarPresupuestoIn, DiagnosticoIn, PresupuestoIn

    db = mundo["db"]
    ot = _crear_ot(mundo)

    st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="Rotor gastado"), user=mundo["jefe"])
    assert st.obtener_detalle(db, ot.id, user=mundo["jefe"]).estado == "en_diagnostico"

    st.crear_presupuesto(db, ot.id, PresupuestoIn(precio_servicio=Decimal("400"), lineas=[]), user=mundo["jefe"])
    d = st.obtener_detalle(db, ot.id, user=mundo["jefe"])
    assert d.estado == "presupuesto"

    # no se puede pasar a reparación sin aprobar
    with pytest.raises(ConflictError):
        st.cambiar_estado(db, ot.id, "en_reparacion", user=mundo["jefe"])

    manana = date.today() + timedelta(days=7)
    d = st.aprobar_presupuesto(db, ot.id, AprobarPresupuestoIn(
        confirmado_por="Cliente por WhatsApp", medio_confirmacion="whatsapp",
        fecha_estimada_entrega=manana,
    ), user=mundo["jefe"])
    assert d.estado == "en_reparacion"
    assert d.fecha_estimada_entrega == manana


def test_costeo_y_margen_real(mundo):
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import AprobarPresupuestoIn, DiagnosticoIn, HorasIn, PresupuestoIn

    db = mundo["db"]
    ot = _crear_ot(mundo)
    st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="diagnostico de prueba"), user=mundo["jefe"])
    st.crear_presupuesto(db, ot.id, PresupuestoIn(precio_servicio=Decimal("300"), lineas=[]), user=mundo["jefe"])
    st.aprobar_presupuesto(db, ot.id, AprobarPresupuestoIn(
        confirmado_por="Cliente", fecha_estimada_entrega=date.today() + timedelta(days=3),
    ), user=mundo["jefe"])

    # 4 horas × tarifa (1600/160 = 10) = 40 de mano de obra; sin piezas ni insumos
    st.registrar_horas(db, ot.id, HorasIn(horas=Decimal("4")), user=mundo["jefe"])
    c = st.get_costeo(db, ot.id, user=mundo["jefe"])
    assert c.costo_mano_obra == Decimal("40.00")
    assert c.costo_interno == Decimal("40.00")
    # precio del presupuesto = 300 → margen real 260
    assert c.margen_real == Decimal("260.00")


def test_costeo_oculto_para_no_administrativo(mundo):
    from servicio_tecnico import service as st

    ot = _crear_ot(mundo)
    with pytest.raises(st.NoAutorizadoError):
        st.get_costeo(mundo["db"], ot.id, user=mundo["tecnico_user"])
    vista = st.obtener_detalle(mundo["db"], ot.id, user=mundo["tecnico_user"])
    assert vista.costo_interno is None and vista.costos_visibles is False


def test_entrega_bloqueada_sin_pago_y_ok_con_pago(mundo):
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import (
        AprobarPresupuestoIn,
        CambioEstadoIn,
        DiagnosticoIn,
        EntregarIn,
        PagoOTIn,
        PresupuestoIn,
    )

    db = mundo["db"]
    ot = _crear_ot(mundo)
    st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="diagnostico de prueba"), user=mundo["jefe"])
    st.crear_presupuesto(db, ot.id, PresupuestoIn(precio_servicio=Decimal("200"), lineas=[]), user=mundo["jefe"])
    st.aprobar_presupuesto(db, ot.id, AprobarPresupuestoIn(
        confirmado_por="Cliente", fecha_estimada_entrega=date.today() + timedelta(days=1),
    ), user=mundo["jefe"])
    st.cambiar_estado(db, ot.id, "listo", user=mundo["jefe"])

    with pytest.raises(ConflictError):
        st.entregar(db, ot.id, EntregarIn(), user=mundo["jefe"])

    st.registrar_pago_ot(db, ot.id, PagoOTIn(medio_pago="efectivo", monto=Decimal("200")), user=mundo["jefe"])
    d = st.entregar(db, ot.id, EntregarIn(), user=mundo["jefe"])
    assert d.estado == "entregado"
    assert d.fecha_real_entrega is not None

    # queda en el historial de serie (003)
    from inventario import repository as inv_repo

    eventos = [e.tipo for e in inv_repo.eventos_de_serie(db, "RLX-3235-001")]
    assert "servicio" in eventos


def test_scoping_tecnico_solo_sus_ot(mundo, factory):
    from servicio_tecnico import service as st
    from servicio_tecnico.schemas import DiagnosticoIn

    db = mundo["db"]
    ot = _crear_ot(mundo)  # asignada a mundo["tecnico_id"]

    # otro técnico-usuario, sin la OT
    otro_u = factory.usuario(sucursales=[mundo["suc"]])
    from tecnicos.schemas import TecnicoIn
    from tecnicos import service as tec

    tec.crear(db, TecnicoIn(nombre="Otro Téc", usuario_id=otro_u.id, sucursales=[mundo["suc"].id]), actor=mundo["jefe"].id)
    otro = CurrentUser(id=otro_u.id, identificacion=otro_u.identificacion, nombre=otro_u.nombre,
                       email=otro_u.email, estado="activo", token_scope="full",
                       roles=[], rol_ids=[], sucursal_ids=[mundo["suc"].id])

    with pytest.raises(st.NoAutorizadoError):
        st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="me meto"), user=otro)

    # el técnico asignado sí puede
    st.registrar_diagnostico(db, ot.id, DiagnosticoIn(diagnostico="diagnostico ok"), user=mundo["tecnico_user"])
    items, _ = st.listar(db, user=otro, estado=None, tecnico_id=None, sucursal_id=None,
                         numero_serie=None, offset=0, limit=50)
    assert all(o.tecnico_id != mundo["tecnico_id"] for o in items)
