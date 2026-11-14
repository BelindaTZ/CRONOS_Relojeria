"""Feature 011 — mermas: registro/costeo a costo de adquisición (Const. Ppio IX,
cobertura obligatoria), umbral de autorización, baja + asiento contable,
reingreso y derivación desde traslados (004)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from shared.exceptions import ConflictError, ValidationError
from shared.guard import CurrentUser


@pytest.fixture
def mundo(db, factory):
    from inventario.models import Reloj
    from piezas import service as piezas_svc
    from piezas.schemas import MovimientoIn, PiezaIn

    suc = factory.sucursal("Sucursal 011")
    gg_u = factory.usuario(roles=[factory.gerencia()], sucursales=[suc])
    gg = CurrentUser(id=gg_u.id, identificacion=gg_u.identificacion, nombre=gg_u.nombre, email=gg_u.email,
                     estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[suc.id])
    gs_u = factory.usuario(sucursales=[suc])
    gs = CurrentUser(id=gs_u.id, identificacion=gs_u.identificacion, nombre=gs_u.nombre, email=gs_u.email,
                     estado="activo", token_scope="full", roles=["Gerente de Sucursal"], rol_ids=[], sucursal_ids=[suc.id])
    from tecnicos.models import Tecnico

    tec_u = factory.usuario(sucursales=[suc])
    tecnico = CurrentUser(id=tec_u.id, identificacion=tec_u.identificacion, nombre=tec_u.nombre, email=tec_u.email,
                          estado="activo", token_scope="full", roles=["Técnico"], rol_ids=[], sucursal_ids=[suc.id])
    tecnico_ficha = Tecnico(usuario_id=tec_u.id, nombre=tec_u.nombre)
    db.add(tecnico_ficha)
    db.flush()

    reloj = Reloj(numero_serie="MRM-001", marca="Tudor", referencia="M79230N", sucursal_actual_id=suc.id,
                  disponibilidad="disponible", costo_adquisicion=Decimal("2000"), precio_venta=Decimal("3450"))
    db.add(reloj)
    db.flush()

    pieza = piezas_svc.crear(
        db, PiezaIn(codigo="9010-011", descripcion="Moebius 9010", costo_adquisicion=Decimal("15")), actor=gg.id,
    )
    piezas_svc.registrar_movimiento(
        db, pieza.id, MovimientoIn(sucursal_id=suc.id, tipo="ingreso", cantidad=5), actor=gg.id,
    )

    return {"db": db, "suc": suc, "gg": gg, "gs": gs, "tecnico": tecnico, "tecnico_ficha": tecnico_ficha,
            "reloj": reloj, "pieza": pieza}


# ==================================================================== US1
def test_merma_de_reloj_costea_a_costo_de_adquisicion(mundo):
    from mermas import service as ms
    from mermas.schemas import MermaIn

    m = ms.crear_merma(mundo["db"], MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])
    assert m.estado == "en_evaluacion"
    assert m.costo_perdida == Decimal("2000.00")
    assert m.costo_visible is True


def test_categoria_de_merma_precisa_la_causa(mundo):
    """Feedback del usuario: falta el motivo específico dentro de la causa
    (robo, defecto de fábrica, o un incidente puntual como una caída)."""
    from configuracion import repository as cfg_repo
    from mermas import service as ms
    from mermas.schemas import MermaIn
    from shared.exceptions import ValidationError

    db = mundo["db"]
    cat = cfg_repo.crear_categoria_merma(db, nombre="Caída accidental (test)", causa="dano_tienda")

    m = ms.crear_merma(db, MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_tienda", categoria_merma_id=cat.id,
        descripcion="Se cayó del mostrador al limpiarlo.", fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])
    assert m.categoria_merma_nombre == "Caída accidental (test)"
    assert m.descripcion == "Se cayó del mostrador al limpiarlo."

    otra_causa = cfg_repo.crear_categoria_merma(db, nombre="Robo con violencia (test)", causa="robo_perdida")
    with pytest.raises(ValidationError):
        ms.crear_merma(db, MermaIn(
            bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_tienda", categoria_merma_id=otra_causa.id,
            fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
        ), user=mundo["gg"])


def test_costo_oculto_para_rol_sin_privilegio(mundo):
    from mermas import service as ms
    from mermas.schemas import MermaIn

    m = ms.crear_merma(mundo["db"], MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["tecnico"])
    assert m.costo_perdida is None and m.costo_visible is False


def test_merma_sobre_reloj_vendido_409(mundo):
    from mermas import service as ms
    from mermas.schemas import MermaIn

    mundo["reloj"].disponibilidad = "vendido"
    mundo["db"].flush()
    with pytest.raises(ConflictError):
        ms.crear_merma(mundo["db"], MermaIn(
            bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="robo_perdida",
            fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
        ), user=mundo["gg"])


def test_merma_de_pieza_sobre_stock_422(mundo):
    from mermas import service as ms
    from mermas.schemas import MermaIn

    with pytest.raises(ValidationError):
        ms.crear_merma(mundo["db"], MermaIn(
            bien_tipo="pieza", pieza_id=mundo["pieza"].id, cantidad=99, causa="dano_tienda",
            fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
        ), user=mundo["gg"])


def test_merma_de_pieza_costea_por_cantidad(mundo):
    from mermas import service as ms
    from mermas.schemas import MermaIn

    m = ms.crear_merma(mundo["db"], MermaIn(
        bien_tipo="pieza", pieza_id=mundo["pieza"].id, cantidad=3, causa="defecto_fabrica",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])
    assert m.costo_perdida == Decimal("45.00")  # 15 x 3


# ==================================================================== US2
def test_baja_sobre_umbral_sin_autorizacion_409(mundo):
    from mermas import service as ms
    from mermas.schemas import EstadoIn, MermaIn

    # umbral sembrado = 200; el reloj cuesta 2000 -> exige autorización
    m = ms.crear_merma(mundo["db"], MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gs"])
    with pytest.raises(ConflictError):
        ms.cambiar_estado(mundo["db"], m.id, EstadoIn(estado="dado_de_baja"), user=mundo["gs"])


def test_autorizacion_registra_quien_y_cuando_y_permite_la_baja(mundo):
    from mermas import service as ms
    from mermas.schemas import AutorizarBajaIn, EstadoIn, MermaIn

    m = ms.crear_merma(mundo["db"], MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gs"])
    autorizado = ms.autorizar_baja(mundo["db"], m.id, AutorizarBajaIn(observacion="acta revisada"), user=mundo["gg"])
    assert autorizado.autorizacion is not None
    assert autorizado.autorizacion.autorizador_nombre == mundo["gg"].nombre

    baja = ms.cambiar_estado(mundo["db"], m.id, EstadoIn(estado="dado_de_baja"), user=mundo["gs"])
    assert baja.estado == "dado_de_baja"


def test_baja_bajo_el_umbral_no_exige_autorizacion(mundo):
    from mermas import service as ms
    from mermas.schemas import EstadoIn, MermaIn

    m = ms.crear_merma(mundo["db"], MermaIn(
        bien_tipo="pieza", pieza_id=mundo["pieza"].id, cantidad=2, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gs"])  # costo 30, bajo el umbral de 200
    baja = ms.cambiar_estado(mundo["db"], m.id, EstadoIn(estado="dado_de_baja"), user=mundo["gs"])
    assert baja.estado == "dado_de_baja"


# ==================================================================== US3
def test_baja_retira_del_inventario_conserva_historial_y_genera_asiento(mundo):
    from contabilidad import service as ct
    from mermas import service as ms
    from mermas.schemas import AutorizarBajaIn, EstadoIn, MermaIn

    db = mundo["db"]
    m = ms.crear_merma(db, MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])
    ms.autorizar_baja(db, m.id, AutorizarBajaIn(), user=mundo["gg"])
    baja = ms.cambiar_estado(db, m.id, EstadoIn(estado="dado_de_baja"), user=mundo["gg"])

    assert mundo["reloj"].disponibilidad == "dado_de_baja"
    assert baja.asiento_id is not None

    mayor = ct.mayor(db, cuenta_codigo="6.04", periodo=None)
    assert any(mv.asiento_id == baja.asiento_id for mv in mayor.movimientos)
    balance = ct.balance_comprobacion(db, periodo=None)
    fila_perdida = next(f for f in balance.filas if f.cuenta_codigo == "6.04")
    assert fila_perdida.debe == Decimal("2000.00")


# ==================================================================== US4
def test_reingreso_devuelve_el_bien_al_stock(mundo):
    """"Reparado y reingresado" se marca ANTES de la baja definitiva (mientras la
    merma sigue 'en evaluación', tal como plantea el escenario de aceptación de
    US4) — el bien nunca salió del inventario activo (solo `dado_de_baja` lo
    saca), así que reingresar lo deja `disponible` y la merma queda en su
    historial sin generar asiento."""
    from mermas import service as ms
    from mermas.schemas import EstadoIn, MermaIn

    db = mundo["db"]
    m = ms.crear_merma(db, MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_servicio",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])
    assert mundo["reloj"].disponibilidad == "disponible"

    reingreso = ms.cambiar_estado(db, m.id, EstadoIn(estado="reparado_reingresado"), user=mundo["gg"])
    assert reingreso.estado == "reparado_reingresado"
    assert reingreso.asiento_id is None
    assert mundo["reloj"].disponibilidad == "disponible"
    assert [h.estado for h in reingreso.historial] == ["en_evaluacion", "reparado_reingresado"]


def test_reingreso_revierte_una_baja_ya_confirmada_si_se_reabre(mundo):
    """El "undo" de inventario (`inventario.revertir_reloj_baja`) sí existe para
    una unidad genuinamente `dado_de_baja` — se prueba directo, sin pasar por el
    endpoint de mermas (que trata `dado_de_baja` como terminal, ver test de abajo)."""
    from inventario import marcar_reloj_baja, revertir_reloj_baja

    db = mundo["db"]
    marcar_reloj_baja(db, mundo["reloj"].id, documento_id=999, actor=mundo["gg"].id)
    assert mundo["reloj"].disponibilidad == "dado_de_baja"
    revertir_reloj_baja(db, mundo["reloj"].id, documento_id=999, actor=mundo["gg"].id)
    assert mundo["reloj"].disponibilidad == "disponible"


def test_dado_de_baja_es_terminal_no_admite_reingreso(mundo):
    from mermas import service as ms
    from mermas.schemas import AutorizarBajaIn, EstadoIn, MermaIn

    db = mundo["db"]
    m = ms.crear_merma(db, MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])
    ms.autorizar_baja(db, m.id, AutorizarBajaIn(), user=mundo["gg"])
    ms.cambiar_estado(db, m.id, EstadoIn(estado="dado_de_baja"), user=mundo["gg"])
    with pytest.raises(ConflictError):
        ms.cambiar_estado(db, m.id, EstadoIn(estado="reparado_reingresado"), user=mundo["gg"])


# ==================================================================== US5
def test_merma_derivada_de_servicio_guarda_vinculo_sin_sancion(mundo):
    from mermas import service as ms
    from mermas.schemas import MermaIn

    m = ms.crear_merma(mundo["db"], MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="dano_servicio",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
        orden_trabajo_id=77, tecnico_id=mundo["tecnico_ficha"].id,
    ), user=mundo["tecnico"])
    assert m.orden_trabajo_id == 77
    assert m.tecnico_id == mundo["tecnico_ficha"].id
    # sin campo de sanción en el modelo — solo trazabilidad (Esp. §4.12)


def test_merma_derivada_de_transferencia_vincula_y_resuelve_discrepancia(mundo, factory):
    from traslados import repository as tr_repo
    from traslados import service as tr_svc
    from traslados.models import DiscrepanciaTransferencia, LineaTransferencia, Transferencia
    from mermas import service as ms
    from mermas.schemas import MermaIn

    db = mundo["db"]
    otra_suc = factory.sucursal("Sucursal 011b")
    t = Transferencia(sucursal_origen_id=otra_suc.id, sucursal_destino_id=mundo["suc"].id,
                      estado="parcial", motivo="prueba")
    db.add(t)
    db.flush()
    linea = LineaTransferencia(transferencia_id=t.id, item_tipo="reloj", reloj_id=mundo["reloj"].id,
                               cantidad_enviada=1, cantidad_recibida=0)
    db.add(linea)
    db.flush()
    disc = tr_repo.crear_discrepancia(db, linea_transferencia_id=linea.id, cantidad_faltante=1)

    payload = tr_svc.discrepancia_para_merma(db, disc.id)
    assert payload["causa"] == "dano_transito" and payload["transferencia_id"] == t.id

    m = ms.crear_merma(db, MermaIn(
        bien_tipo="reloj", reloj_id=payload["reloj_id"], causa=payload["causa"],
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id, transferencia_id=t.id,
    ), user=mundo["gg"], discrepancia_id=disc.id)

    db.refresh(disc)
    assert disc.resuelta is True and disc.merma_id == m.id


# ==================================================================== US6
def test_reporte_agrupa_por_causa_monto_y_frecuencia(mundo):
    from mermas import service as ms
    from mermas.schemas import MermaIn

    db = mundo["db"]
    ms.crear_merma(db, MermaIn(
        bien_tipo="pieza", pieza_id=mundo["pieza"].id, cantidad=1, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])
    ms.crear_merma(db, MermaIn(
        bien_tipo="pieza", pieza_id=mundo["pieza"].id, cantidad=2, causa="dano_tienda",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])
    ms.crear_merma(db, MermaIn(
        bien_tipo="reloj", reloj_id=mundo["reloj"].id, causa="robo_perdida",
        fecha_evento=date.today(), sucursal_id=mundo["suc"].id,
    ), user=mundo["gg"])

    reporte = ms.reporte_mermas(db, user=mundo["gg"], causa=None, sucursal_id=None, desde=None, hasta=None)
    por_causa = {r.causa: r for r in reporte}
    assert por_causa["dano_tienda"].frecuencia == 2
    assert por_causa["dano_tienda"].monto_total == Decimal("45.00")  # 15 + 30
    assert por_causa["robo_perdida"].frecuencia == 1
