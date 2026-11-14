"""Lógica del módulo `tecnicos` (feature 005).

- Ficha de RRHH técnico: especialidades (catálogo), certificaciones, sucursales,
  vínculo 1—1 opcional a `usuario`. Inactivación solo Técnico Jefe / Gerencia.
- Costo interno de mano de obra por **tarifa horaria** (sueldo mensual ÷ horas
  productivas estándar, parámetro de 001). El contrato para 008 vive en `costeo.py`.
- **Motor de bono por productividad configurable** (§5): `regla_bono` con una lista
  de `componente_bono` (indicador + umbral + valor); el bono del técnico en un
  periodo = Σ de los componentes cuyo indicador supera su umbral. Nunca negativo.
- El bono acumulado se **prorratea** entre las OT cerradas del periodo,
  proporcional al costo de MO de cada una (`bono_ot`), y 008 lo suma al costo de MO
  en los reportes de margen.
- Los datos de OT los aporta 008 vía `registrar_proveedor_ot`; hasta entonces el
  motor se valida con fixtures (Const. Ppio IX, cobertura obligatoria).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from tecnicos import costeo, repository
from tecnicos.models import BonoAcumulado, BonoOt, PeriodoLiquidacion, Tecnico
from tecnicos.schemas import (
    BonoOtOut,
    BonoOut,
    CostoOut,
    ProductividadOut,
    ReglaBonoOut,
    ComponenteBonoOut,
    PeriodoOut,
    TecnicoOut,
)

logger = logging.getLogger("cronos.tecnicos")

_CENT = Decimal("0.01")
# Roles que pueden mantener a los técnicos e inactivarlos (FR-017).
_ROLES_JEFE = {"Gerencia General", "Técnico Jefe"}
# Roles que ven el costo interno de MO y el desglose del bono (FR-014, §6).
_ROLES_VER_COSTOS = {"Gerencia General", "Gerente de Sucursal", "Contador", "Administrador", "Técnico Jefe"}


class NoAutorizadoError(ConflictError):
    status_code = 403
    code = "no_autorizado"


def es_jefe(user: CurrentUser) -> bool:
    return bool(_ROLES_JEFE & set(getattr(user, "roles", []) or []))


def puede_ver_costos(user: CurrentUser) -> bool:
    return bool(_ROLES_VER_COSTOS & set(getattr(user, "roles", []) or []))


# =========================================================== OT (proveedor de 008)
@dataclass(frozen=True)
class OrdenTrabajoInfo:
    orden_trabajo_id: int
    tecnico_id: int
    fecha_cierre: date
    margen_real: Decimal
    horas_registradas: float | None = None
    tipo_reparacion: str | None = None
    dentro_de_tiempo: bool = True
    es_reproceso: bool = False


ProveedorOT = Callable[[Session, date, date, int | None], "list[OrdenTrabajoInfo]"]
_PROVEEDOR_OT: list[ProveedorOT] = []


def registrar_proveedor_ot(fn: ProveedorOT) -> None:
    """008 registra aquí la función que entrega las OT cerradas de un rango."""
    _PROVEEDOR_OT.append(fn)


def _ots_del_periodo(db: Session, inicio: date, fin: date, tecnico_id: int | None) -> list[OrdenTrabajoInfo]:
    if not _PROVEEDOR_OT:
        return []
    salida: list[OrdenTrabajoInfo] = []
    for fn in _PROVEEDOR_OT:
        salida.extend(fn(db, inicio, fin, tecnico_id) or [])
    return salida


# =========================================================== salida técnico
def _costo_out(db: Session, tecnico_id: int) -> CostoOut | None:
    esquema = repository.costo_vigente(db, tecnico_id)
    if esquema is None:
        return None
    horas = costeo.horas_estandar_mes(db)
    return CostoOut(
        sueldo_mensual=Decimal(esquema.sueldo_mensual),
        vigente_desde=esquema.vigente_desde,
        tarifa_hora=(Decimal(esquema.sueldo_mensual) / horas).quantize(_CENT, rounding=ROUND_HALF_UP),
        horas_estandar_mes=horas,
    )


def _tecnico_out(db: Session, t: Tecnico, *, ver_costos: bool) -> TecnicoOut:
    esp_ids = repository.especialidad_ids(db, t.id)
    nombres = repository.nombres_especialidad(db, esp_ids)
    return TecnicoOut(
        id=t.id, nombre=t.nombre, certificaciones=t.certificaciones, estado=t.estado,
        usuario_id=t.usuario_id,
        especialidades=[nombres.get(i, f"#{i}") for i in esp_ids],
        especialidad_ids=esp_ids,
        sucursal_ids=repository.sucursal_ids(db, t.id),
        costos_visibles=ver_costos,
        costo_vigente=_costo_out(db, t.id) if ver_costos else None,
        creado_en=t.creado_en,
    )


# =========================================================== CRUD técnico
def listar(db, *, user, q, especialidad, sucursal_id, offset, limit):
    filas, total = repository.buscar(
        db, q=q, especialidad=especialidad, sucursal_id=sucursal_id,
        solo_activos=False, offset=offset, limit=limit,
    )
    vc = puede_ver_costos(user)
    return [_tecnico_out(db, t, ver_costos=vc) for t in filas], total


def _resolver_especialidades(db: Session, ids: list[int], nuevas: list[str]) -> list[int]:
    resueltos = list(ids or [])
    for nombre in nuevas or []:
        nombre = (nombre or "").strip()
        if not nombre:
            continue
        e = repository.especialidad_por_nombre(db, nombre) or repository.crear_especialidad(db, nombre)
        resueltos.append(e.id)
    return list(dict.fromkeys(resueltos))


def crear(db: Session, datos, *, actor: int) -> TecnicoOut:
    if datos.usuario_id is not None:
        from shared.models import Usuario

        if db.get(Usuario, datos.usuario_id) is None:
            raise ValidationError("El usuario vinculado no existe", field="usuario_id")
    t = repository.crear(
        db, nombre=datos.nombre.strip(),
        certificaciones=(datos.certificaciones or "").strip() or None,
        usuario_id=datos.usuario_id, estado="activo",
    )
    esp = _resolver_especialidades(db, datos.especialidades, datos.especialidades_nuevas)
    if esp:
        repository.set_especialidades(db, t.id, esp)
    if datos.sucursales:
        repository.set_sucursales(db, t.id, datos.sucursales)
    registrar_cambio(db, actor=actor, accion="crear", entidad="tecnico", entidad_id=t.id,
                     despues={"nombre": t.nombre, "usuario_id": t.usuario_id})
    return _tecnico_out(db, t, ver_costos=True)


def _tecnico_es_el_usuario(t: Tecnico, user: CurrentUser) -> bool:
    return t.usuario_id is not None and t.usuario_id == user.id


def actualizar(db: Session, tid: int, datos, *, user: CurrentUser) -> TecnicoOut:
    t = repository.obtener(db, tid)
    if t is None:
        raise NotFoundError("Técnico no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    # FR-017a: el propio técnico NO edita su ficha profesional (solo contacto/foto vía 001).
    if _tecnico_es_el_usuario(t, user) and not es_jefe(user):
        raise NoAutorizadoError(
            "Tus especialidades, certificaciones y costo los mantiene el Técnico Jefe. "
            "Tus datos de contacto y foto se editan en «Mis datos»."
        )
    if not es_jefe(user):
        raise NoAutorizadoError("Editar la ficha de un técnico requiere Técnico Jefe o Gerencia General")

    antes = _tecnico_out(db, t, ver_costos=True).model_dump()
    if "nombre" in cambios and cambios["nombre"]:
        t.nombre = cambios["nombre"].strip()
    if "certificaciones" in cambios:
        t.certificaciones = (cambios["certificaciones"] or "").strip() or None
    if "usuario_id" in cambios:
        t.usuario_id = cambios["usuario_id"]
    if cambios.get("especialidades") is not None or cambios.get("especialidades_nuevas") is not None:
        repository.set_especialidades(
            db, t.id,
            _resolver_especialidades(db, cambios.get("especialidades") or [], cambios.get("especialidades_nuevas") or []),
        )
    if cambios.get("sucursales") is not None:
        repository.set_sucursales(db, t.id, cambios["sucursales"])
    t.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="tecnico", entidad_id=tid,
                     antes=antes, despues=_tecnico_out(db, t, ver_costos=True).model_dump())
    return _tecnico_out(db, t, ver_costos=puede_ver_costos(user))


def obtener_detalle(db: Session, tid: int, *, user: CurrentUser) -> TecnicoOut:
    t = repository.obtener(db, tid)
    if t is None:
        raise NotFoundError("Técnico no encontrado")
    return _tecnico_out(db, t, ver_costos=puede_ver_costos(user))


def set_estado(db: Session, tid: int, estado: str, *, user: CurrentUser) -> TecnicoOut:
    t = repository.obtener(db, tid)
    if t is None:
        raise NotFoundError("Técnico no encontrado")
    if not es_jefe(user):
        raise NoAutorizadoError("Inactivar o reactivar un técnico requiere Técnico Jefe o Gerencia General")
    if _tecnico_es_el_usuario(t, user):
        raise NoAutorizadoError("Un técnico no puede cambiar su propio estado")
    if estado == t.estado:
        return _tecnico_out(db, t, ver_costos=puede_ver_costos(user))
    t.estado = estado
    t.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="tecnico", entidad_id=tid,
                     antes={"estado": "activo" if estado == "inactivo" else "inactivo"},
                     despues={"estado": estado})
    return _tecnico_out(db, t, ver_costos=puede_ver_costos(user))


def set_costo(db: Session, tid: int, datos, *, user: CurrentUser) -> CostoOut:
    t = repository.obtener(db, tid)
    if t is None:
        raise NotFoundError("Técnico no encontrado")
    if not es_jefe(user):
        raise NoAutorizadoError("El costo interno de mano de obra solo lo fija el Técnico Jefe o Gerencia General")
    if _tecnico_es_el_usuario(t, user):
        raise NoAutorizadoError("Un técnico no puede fijar su propio costo de mano de obra")
    anterior = repository.costo_vigente(db, tid)
    repository.insertar_costo(
        db, tecnico_id=tid, sueldo_mensual=datos.sueldo_mensual,
        vigente_desde=datos.vigente_desde, creado_por=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="editar", entidad="esquema_costo_mano_obra", entidad_id=tid,
                     antes={"sueldo_mensual": str(anterior.sueldo_mensual)} if anterior else None,
                     despues={"sueldo_mensual": str(datos.sueldo_mensual), "vigente_desde": str(datos.vigente_desde)})
    _recalcular_bonos_periodos_abiertos(db, motivo="costo_mano_obra")
    return _costo_out(db, tid)


# =========================================================== especialidades
def listar_especialidades(db: Session) -> list[dict]:
    return [{"id": e.id, "nombre": e.nombre, "activo": e.activo} for e in repository.listar_especialidades(db)]


def crear_especialidad(db: Session, nombre: str, *, actor: int) -> dict:
    if repository.especialidad_por_nombre(db, nombre):
        raise ConflictError("Ya existe una especialidad con ese nombre", field="nombre")
    e = repository.crear_especialidad(db, nombre)
    registrar_cambio(db, actor=actor, accion="crear", entidad="especialidad", entidad_id=e.id,
                     despues={"nombre": e.nombre})
    return {"id": e.id, "nombre": e.nombre, "activo": e.activo}


# =========================================================== regla de bono
def _regla_out(r) -> ReglaBonoOut:
    return ReglaBonoOut(
        id=r.id, nombre=r.nombre, periodicidad=r.periodicidad, vigente_desde=r.vigente_desde,
        activa=r.activa, creado_en=r.creado_en,
        componentes=[
            ComponenteBonoOut(id=c.id, tipo=c.tipo, indicador=c.indicador, umbral=c.umbral, valor=c.valor)
            for c in r.componentes
        ],
    )


def listar_reglas(db: Session) -> list[ReglaBonoOut]:
    return [_regla_out(r) for r in repository.listar_reglas(db)]


def crear_regla(db: Session, datos, *, actor: int) -> ReglaBonoOut:
    vigencia = datos.vigente_desde or date.today()
    # una sola regla activa por vez: la nueva reemplaza a la anterior desde su vigencia.
    for r in repository.listar_reglas(db, solo_activas=True):
        r.activa = False
    r = repository.crear_regla(
        db, nombre=datos.nombre.strip(), periodicidad=datos.periodicidad,
        vigente_desde=vigencia, activa=True, creado_por=actor,
    )
    for c in datos.componentes:
        repository.agregar_componente(
            db, regla_bono_id=r.id, tipo=c.tipo, indicador=c.indicador,
            umbral=c.umbral, valor=c.valor,
        )
    db.refresh(r)
    registrar_cambio(db, actor=actor, accion="crear", entidad="regla_bono", entidad_id=r.id,
                     despues={"nombre": r.nombre, "componentes": len(datos.componentes)})
    # FR-011: recalcula los periodos de liquidación aún abiertos.
    _recalcular_bonos_periodos_abiertos(db, motivo="regla_bono")
    return _regla_out(r)


# =========================================================== indicadores + motor
def _indicadores(ots: list[OrdenTrabajoInfo]) -> dict[str, Decimal]:
    n = len(ots)
    if n == 0:
        return {
            "ot_completadas": Decimal(0), "cumplimiento_tiempos": Decimal(0),
            "margen_generado": Decimal(0), "calidad": Decimal(100),
        }
    dentro = sum(1 for o in ots if o.dentro_de_tiempo)
    reprocesos = sum(1 for o in ots if o.es_reproceso)
    return {
        "ot_completadas": Decimal(n),
        "cumplimiento_tiempos": (Decimal(dentro) / n * 100).quantize(_CENT),
        "margen_generado": sum((Decimal(str(o.margen_real)) for o in ots), Decimal(0)),
        "calidad": (Decimal(100) - Decimal(reprocesos) / n * 100).quantize(_CENT),
    }


def _evaluar_regla(regla, indicadores: dict[str, Decimal]) -> tuple[Decimal, dict]:
    margen = indicadores["margen_generado"]
    total = Decimal(0)
    detalle = []
    for c in regla.componentes:
        ind_val = indicadores.get(c.indicador, Decimal(0))
        aporta = ind_val >= Decimal(c.umbral)
        monto = Decimal(0)
        if aporta:
            if c.tipo == "monto_por_meta":
                monto = Decimal(c.valor)
            elif c.tipo == "porcentaje_margen":
                monto = Decimal(c.valor) * margen
            elif c.tipo == "combinacion":
                monto = Decimal(c.valor) + Decimal(c.valor) * margen
        monto = max(monto, Decimal(0)).quantize(_CENT)  # un componente nunca resta (es un bono)
        total += monto
        detalle.append({
            "indicador": c.indicador, "tipo": c.tipo,
            "valor_indicador": float(ind_val), "umbral": float(c.umbral),
            "aporta": bool(aporta), "monto": float(monto),
        })
    total = max(total, Decimal(0)).quantize(_CENT)
    return total, {"componentes": detalle, "regla_bono_id": regla.id}


def _costo_mo_seguro(db: Session, tecnico_id: int, ot: OrdenTrabajoInfo) -> Decimal:
    try:
        return costeo.costo_mo_ot(
            db, tecnico_id=tecnico_id, horas=ot.horas_registradas,
            tipo_reparacion=ot.tipo_reparacion, en_fecha=ot.fecha_cierre,
        ).costo_mo
    except (ValidationError, NotFoundError):
        return Decimal(0)


def _materializar_bono(
    db: Session, *, tecnico: Tecnico, periodo: PeriodoLiquidacion,
    ots: list[OrdenTrabajoInfo],
) -> BonoAcumulado:
    regla = repository.regla_vigente(db, periodo.fecha_fin)
    indic = _indicadores(ots)
    if regla is None:
        valor_total, desglose, regla_id = Decimal(0), {"componentes": [], "sin_regla_vigente": True}, None
    elif not ots:
        # FR-010: un periodo sin OT arroja bono 0 (aunque un indicador por defecto,
        # p. ej. calidad = 100, supere su umbral).
        valor_total, desglose, regla_id = Decimal(0), {"componentes": [], "sin_ot_en_el_periodo": True}, regla.id
    else:
        valor_total, desglose = _evaluar_regla(regla, indic)
        regla_id = regla.id
    desglose["indicadores"] = {k: float(v) for k, v in indic.items()}

    estado = "definitivo" if periodo.estado == "cerrado" else "preliminar"
    bono = repository.bono_de(db, tecnico_id=tecnico.id, periodo_id=periodo.id)
    if bono is None:
        bono = BonoAcumulado(tecnico_id=tecnico.id, periodo_liquidacion_id=periodo.id)
        db.add(bono)
    else:
        db.query(BonoOt).filter_by(bono_acumulado_id=bono.id).delete()
    bono.regla_bono_id = regla_id
    bono.valor_total = valor_total
    bono.desglose = desglose
    bono.estado = estado
    bono.calculado_en = datetime.now(timezone.utc)
    db.flush()

    # prorrateo entre las OT cerradas del periodo, proporcional al costo de MO.
    if ots and valor_total > 0:
        costos = {o.orden_trabajo_id: _costo_mo_seguro(db, tecnico.id, o) for o in ots}
        suma = sum(costos.values(), Decimal(0))
        repartido = Decimal(0)
        for i, o in enumerate(ots):
            if i == len(ots) - 1:
                monto = (valor_total - repartido).quantize(_CENT)
            elif suma > 0:
                monto = (valor_total * costos[o.orden_trabajo_id] / suma).quantize(_CENT)
            else:
                monto = (valor_total / len(ots)).quantize(_CENT)
            repartido += monto
            db.add(BonoOt(bono_acumulado_id=bono.id, orden_trabajo_id=o.orden_trabajo_id, monto=monto))
        db.flush()
    return bono


def _bono_out(db: Session, bono: BonoAcumulado) -> BonoOut:
    t = db.get(Tecnico, bono.tecnico_id)
    return BonoOut(
        tecnico_id=bono.tecnico_id, tecnico_nombre=t.nombre if t else None,
        periodo_id=bono.periodo_liquidacion_id, regla_bono_id=bono.regla_bono_id,
        valor_total=Decimal(bono.valor_total), desglose=bono.desglose, estado=bono.estado,
        calculado_en=bono.calculado_en,
        bono_ot=[BonoOtOut(orden_trabajo_id=o.orden_trabajo_id, monto=Decimal(o.monto)) for o in bono.ots],
    )


def calcular_bono(db: Session, *, periodo_id: int, tecnico_id: int | None = None) -> list[BonoOut]:
    periodo = repository.obtener_periodo(db, periodo_id)
    if periodo is None:
        raise NotFoundError("Periodo de liquidación no encontrado")

    if tecnico_id is not None:
        t = repository.obtener(db, tecnico_id)
        if t is None:
            raise NotFoundError("Técnico no encontrado")
        tecnicos = [t]
    else:
        tecnicos = repository.tecnicos_activos(db)

    salida = []
    for t in tecnicos:
        ots = _ots_del_periodo(db, periodo.fecha_inicio, periodo.fecha_fin, t.id)
        bono = _materializar_bono(db, tecnico=t, periodo=periodo, ots=ots)
        salida.append(_bono_out(db, bono))
    return salida


def listar_bonos(db: Session, *, periodo_id: int | None, tecnico_id: int | None) -> list[BonoOut]:
    return [_bono_out(db, b) for b in repository.listar_bonos(db, periodo_id=periodo_id, tecnico_id=tecnico_id)]


def _recalcular_bonos_periodos_abiertos(db: Session, *, motivo: str) -> int:
    """FR-011 / recálculo en cascada: recalcula `bono_acumulado` de periodos abiertos.
    Los periodos cerrados conservan su valor histórico."""
    n = 0
    for periodo in repository.periodos_abiertos(db):
        objetivos = {b.tecnico_id for b in repository.listar_bonos(db, periodo_id=periodo.id, tecnico_id=None)}
        objetivos.update(t.id for t in repository.tecnicos_activos(db))
        for tid in objetivos:
            t = repository.obtener(db, tid)
            if t is None:
                continue
            ots = _ots_del_periodo(db, periodo.fecha_inicio, periodo.fecha_fin, tid)
            _materializar_bono(db, tecnico=t, periodo=periodo, ots=ots)
            n += 1
    logger.info("recálculo de bonos (%s): %d filas de periodos abiertos", motivo, n)
    return n


# =========================================================== periodos
def _periodo_out(p: PeriodoLiquidacion) -> PeriodoOut:
    return PeriodoOut(
        id=p.id, fecha_inicio=p.fecha_inicio, fecha_fin=p.fecha_fin, estado=p.estado,
        cerrado_en=p.cerrado_en, creado_en=p.creado_en,
    )


def listar_periodos(db: Session) -> list[PeriodoOut]:
    return [_periodo_out(p) for p in repository.listar_periodos(db)]


def crear_periodo(db: Session, datos, *, actor: int) -> PeriodoOut:
    if datos.fecha_fin < datos.fecha_inicio:
        raise ValidationError("La fecha de fin no puede ser anterior a la de inicio", field="fecha_fin")
    p = repository.crear_periodo(db, fecha_inicio=datos.fecha_inicio, fecha_fin=datos.fecha_fin, estado="abierto")
    registrar_cambio(db, actor=actor, accion="crear", entidad="periodo_liquidacion", entidad_id=p.id,
                     despues={"inicio": str(p.fecha_inicio), "fin": str(p.fecha_fin)})
    return _periodo_out(p)


def cerrar_periodo(db: Session, pid: int, *, actor: int) -> PeriodoOut:
    p = repository.obtener_periodo(db, pid)
    if p is None:
        raise NotFoundError("Periodo de liquidación no encontrado")
    if p.estado == "cerrado":
        raise ConflictError("El periodo ya está cerrado")
    # recalcula por última vez y marca los bonos como definitivos
    for t in repository.tecnicos_activos(db):
        ots = _ots_del_periodo(db, p.fecha_inicio, p.fecha_fin, t.id)
        _materializar_bono(db, tecnico=t, periodo=p, ots=ots)
    p.estado = "cerrado"
    p.cerrado_por = actor
    p.cerrado_en = datetime.now(timezone.utc)
    for b in repository.listar_bonos(db, periodo_id=p.id, tecnico_id=None):
        b.estado = "definitivo"
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="periodo_liquidacion", entidad_id=pid,
                     antes={"estado": "abierto"}, despues={"estado": "cerrado"})
    return _periodo_out(p)


# =========================================================== productividad
def productividad(db: Session, *, periodo_id: int, tecnico_id: int | None = None) -> list[ProductividadOut]:
    periodo = repository.obtener_periodo(db, periodo_id)
    if periodo is None:
        raise NotFoundError("Periodo de liquidación no encontrado")
    tecnicos = (
        [repository.obtener(db, tecnico_id)] if tecnico_id is not None else repository.tecnicos_activos(db)
    )
    salida = []
    for t in tecnicos:
        if t is None:
            continue
        ots = _ots_del_periodo(db, periodo.fecha_inicio, periodo.fecha_fin, t.id)
        indic = _indicadores(ots)
        horas = []
        for o in ots:
            if o.horas_registradas is not None:
                horas.append(float(o.horas_registradas))
            else:
                horas.append(float(costeo.tiempo_estimado_horas(db, o.tipo_reparacion)))
        bono = repository.bono_de(db, tecnico_id=t.id, periodo_id=periodo_id)
        salida.append(ProductividadOut(
            tecnico_id=t.id, tecnico_nombre=t.nombre,
            ot_completadas=len(ots),
            tiempo_promedio_horas=round(sum(horas) / len(horas), 2) if horas else 0.0,
            margen_generado=indic["margen_generado"],
            bono_alcanzado=Decimal(bono.valor_total) if bono else Decimal(0),
        ))
    return salida


# =========================================================== consumidores 001
def _recalcular_por_parametro(db: Session, clave: str) -> int:
    return _recalcular_bonos_periodos_abiertos(db, motivo=f"parametro:{clave}")


_consumidores_registrados = False


def registrar_consumidores() -> None:
    global _consumidores_registrados
    if _consumidores_registrados:
        return
    from shared.parametros import registrar_consumidor

    registrar_consumidor(
        "horas_productivas_estandar_mes", _recalcular_por_parametro, nombre="tecnicos.recalculo_bonos"
    )
    _consumidores_registrados = True


# =========================================================== API pública (008)
def costo_mo_ot(db: Session, *, tecnico_id: int, horas: float | None = None, tipo_reparacion: str | None = None):
    return costeo.costo_mo_ot(db, tecnico_id=tecnico_id, horas=horas, tipo_reparacion=tipo_reparacion)


def especialidades_de(db: Session, tecnico_id: int) -> list[str]:
    ids = repository.especialidad_ids(db, tecnico_id)
    return list(repository.nombres_especialidad(db, ids).values())


def tecnico_activo(db: Session, tecnico_id: int) -> bool:
    t = repository.obtener(db, tecnico_id)
    return t is not None and t.estado == "activo"


def tecnico_de_usuario(db: Session, usuario_id: int) -> int | None:
    """Público (008): id de técnico ligado a un usuario (scoping 'solo las propias')."""
    t = repository.por_usuario(db, usuario_id)
    return t.id if t else None


def sugerir_tecnico(
    db: Session, *, marca: str | None = None, calibre_codigo: str | None = None, sucursal_id: int | None = None,
) -> int | None:
    """Público (008): técnico activo sugerido para una OT según especialidad y
    sucursal. La especialidad es texto libre (Const. §3.3: "Rolex, Omega,
    complicaciones, etc." — de marca, no solo de calibre): se prueba primero
    por MARCA del reloj (el ejemplo principal de la especificación), luego por
    calibre completo, luego por la primera palabra del calibre (p.ej. "ETA" de
    "ETA 2824"). Sin match exacto, cualquier técnico activo de la sucursal."""
    candidatos = []
    if marca:
        candidatos.append(marca)
    if calibre_codigo:
        candidatos.append(calibre_codigo)
        primera = calibre_codigo.split()[0]
        if primera != calibre_codigo:
            candidatos.append(primera)
    for esp in candidatos:
        filas = repository.por_especialidad_y_sucursal(db, especialidad=esp, sucursal_id=sucursal_id)
        if filas:
            return filas[0].id
    filas = repository.por_especialidad_y_sucursal(db, especialidad=None, sucursal_id=sucursal_id)
    return filas[0].id if filas else None


def datos_para_correo(db: Session, tecnico_id: int) -> dict | None:
    """Público (008 §FR-003a; email al propio técnico añadido 011/flujo principal):
    datos generales del técnico para el aviso al cliente, y su email para avisarle
    a él mismo de la nueva OT asignada."""
    t = repository.obtener(db, tecnico_id)
    if t is None:
        return None
    email = None
    if t.usuario_id:
        from shared.models import Usuario

        u = db.get(Usuario, t.usuario_id)
        email = u.email if u else None
    return {
        "nombre": t.nombre,
        "especialidades": especialidades_de(db, tecnico_id),
        "certificaciones": t.certificaciones,
        "email": email,
    }


def bono_ot_de_orden(db: Session, orden_trabajo_id: int) -> Decimal:
    """Bono prorrateado que le corresponde a una OT (008 lo suma al costo de MO)."""
    from sqlalchemy import select as _select

    total = db.scalar(
        _select(BonoOt.monto).where(BonoOt.orden_trabajo_id == orden_trabajo_id)
    )
    return Decimal(total) if total is not None else Decimal(0)
