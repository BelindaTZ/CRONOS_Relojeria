"""Feature 005 — ficha de técnico y costo interno de mano de obra (US1).

**Crítico (Const. Ppio IX)**: tarifa horaria y `costo_mo_ot`. Además: el sueldo no
es visible sin permiso; el propio técnico no edita su ficha ni se inactiva.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from shared.exceptions import ValidationError
from shared.guard import CurrentUser
from tecnicos import costeo
from tecnicos import service as tec
from tecnicos.schemas import CostoIn, EstadoIn, TecnicoIn, TecnicoPatch


def _jefe(factory):
    u = factory.usuario(roles=[factory.gerencia()])
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=["Gerencia General"], rol_ids=[], sucursal_ids=[])


def _usuario_plano(u):
    return CurrentUser(id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                       estado="activo", token_scope="full", roles=[], rol_ids=[], sucursal_ids=[])


def test_tarifa_hora_y_costo_mo_ot(db, factory):
    jefe = _jefe(factory)
    t = tec.crear(db, TecnicoIn(nombre="J. Pérez", especialidades_nuevas=["Rolex"]), actor=jefe.id)
    tec.set_costo(db, t.id, CostoIn(sueldo_mensual=Decimal("1600"), vigente_desde=date(2026, 9, 1)), user=jefe)

    # tarifa = 1600 / 160 = 10
    assert costeo.tarifa_hora(db, t.id) == Decimal("10.00")

    con_horas = costeo.costo_mo_ot(db, tecnico_id=t.id, horas=3)
    assert con_horas.costo_mo == Decimal("30.00") and con_horas.base == "horas_registradas"

    # sin horas → tarifa × tiempo_estimado_horas_default (2)
    sin_horas = costeo.costo_mo_ot(db, tecnico_id=t.id, tipo_reparacion="servicio_completo")
    assert sin_horas.costo_mo == Decimal("20.00") and sin_horas.base == "tiempo_estimado"


def test_sin_esquema_de_costo_no_hay_tarifa(db, factory):
    jefe = _jefe(factory)
    t = tec.crear(db, TecnicoIn(nombre="Sin costo"), actor=jefe.id)
    with pytest.raises(ValidationError):
        costeo.tarifa_hora(db, t.id)


def test_sueldo_oculto_sin_permiso(db, factory):
    jefe = _jefe(factory)
    t = tec.crear(db, TecnicoIn(nombre="Con costo"), actor=jefe.id)
    tec.set_costo(db, t.id, CostoIn(sueldo_mensual=Decimal("1500"), vigente_desde=date(2026, 9, 1)), user=jefe)

    visto_jefe = tec.obtener_detalle(db, t.id, user=jefe)
    assert visto_jefe.costos_visibles and visto_jefe.costo_vigente.sueldo_mensual == Decimal("1500.00")

    plano = _usuario_plano(factory.usuario())
    visto_plano = tec.obtener_detalle(db, t.id, user=plano)
    assert visto_plano.costos_visibles is False and visto_plano.costo_vigente is None


def test_tecnico_no_edita_su_ficha_ni_se_inactiva(db, factory):
    jefe = _jefe(factory)
    u = factory.usuario()
    t = tec.crear(db, TecnicoIn(nombre="Auto", usuario_id=u.id), actor=jefe.id)
    yo = _usuario_plano(u)

    with pytest.raises(tec.NoAutorizadoError):
        tec.actualizar(db, t.id, TecnicoPatch(certificaciones="me autoasciendo"), user=yo)
    with pytest.raises(tec.NoAutorizadoError):
        tec.set_estado(db, t.id, "inactivo", user=yo)
    with pytest.raises(tec.NoAutorizadoError):
        tec.set_costo(db, t.id, CostoIn(sueldo_mensual=Decimal("9999"), vigente_desde=date(2026, 9, 1)), user=yo)

    # el jefe sí puede
    tec.set_estado(db, t.id, "inactivo", user=jefe)
    assert tec.obtener_detalle(db, t.id, user=jefe).estado == "inactivo"


def test_endpoint_costo_y_autoedicion_403(client, factory, auth_header):
    jefe_rol = factory.gerencia()
    jefe = factory.usuario(roles=[jefe_rol])
    # el técnico-usuario TIENE permiso de módulo para editar, pero aun así no puede
    # tocar su propia ficha (FR-017a): el bloqueo es de negocio, no solo de RBAC.
    rol_tec = factory.rol("Técnico")
    factory.permitir(rol_tec, "tecnicos", ["consultar", "editar"])
    tecnico_user = factory.usuario(roles=[rol_tec])

    r = client.post("/tecnicos", json={"nombre": "API Test", "usuario_id": tecnico_user.id}, headers=auth_header(jefe))
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = client.post(f"/tecnicos/{tid}/costo", json={"sueldo_mensual": 1600, "vigente_desde": "2026-09-01"},
                    headers=auth_header(jefe))
    assert r.status_code == 201 and r.json()["tarifa_hora"] == "10.00"

    # el propio técnico intenta cambiar su costo → 403
    r = client.patch(f"/tecnicos/{tid}", json={"certificaciones": "x"}, headers=auth_header(tecnico_user))
    assert r.status_code == 403
    r = client.put(f"/tecnicos/{tid}/estado", json={"estado": "inactivo"}, headers=auth_header(tecnico_user))
    assert r.status_code == 403
