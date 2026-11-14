"""Lógica central del módulo `contabilidad` (feature 010): libro diario y
derivados (mayor, balance de comprobación, estado de resultados), cierre de
periodo, subledger de CxC (cobros + aging) y rentabilidad por sucursal.

- **Partida doble**: `crear_asiento` nunca guarda un asiento con `Σ debe ≠ Σ haber`
  (FR-002; ACC001). Mayor y balance son **consultas** sobre `linea_asiento`
  (research D2) — no hay tablas materializadas.
- **Periodo cerrado**: un asiento con fecha dentro de un periodo `cerrado` exige
  `ajuste_de_asiento_id` (asiento de ajuste nuevo, fechado y auditado); el original
  es inmutable (FR-016, ACC009). Sin periodo definido para la fecha, se permite
  (el negocio puede no tener periodos formales aún) — igual que "sin regla
  configurada" (ACC006), no bloquea la operación de origen.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from contabilidad import repository
from contabilidad.models import Asiento
from contabilidad.schemas import (
    AgingOut,
    AsientoOut,
    BalanceComprobacionOut,
    CxcOut,
    CxpOut,
    EstadoResultadosOut,
    FilaBalanceOut,
    LineaAsientoOut,
    MayorOut,
    MovimientoMayorOut,
    PeriodoOut,
    RentabilidadSucursalOut,
    TramoAgingOut,
)
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser

logger = logging.getLogger("cronos.contabilidad")

_CENT = Decimal("0.01")
_TRAMOS = [(0, 30, "0-30"), (31, 60, "31-60"), (61, 90, "61-90"), (91, None, "+90")]


class NoAutorizadoError(ConflictError):
    status_code = 403
    code = "no_autorizado"


def _q(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


_ROLES_CONTABLES = {"Gerencia General", "Contador"}


def es_gerencia(user: CurrentUser) -> bool:
    return "Gerencia General" in set(getattr(user, "roles", []) or [])


def puede_gestionar_contabilidad(user: CurrentUser) -> bool:
    """Gastos, CxP y periodos contables: Gerencia General **o** Contador (Const. §3,
    "Contador / Administrativo: Módulo contable, cuentas por cobrar/pagar, gastos").
    Distinto de `es_gerencia`, que sigue reservado a lo que es estrictamente
    prerrogativa del propietario (nada dentro de este módulo, por ahora)."""
    return bool(_ROLES_CONTABLES & set(getattr(user, "roles", []) or []))


def _sucursales(user: CurrentUser) -> list[int] | None:
    from inventario import sucursales_visibles

    return sucursales_visibles(user, None)


# ============================================================ plan de cuentas
def _cuenta_out(c) -> dict:
    return {
        "id": c.id, "codigo": c.codigo, "nombre": c.nombre, "tipo": c.tipo,
        "cuenta_padre_id": c.cuenta_padre_id, "imputable": c.imputable, "activa": c.activa,
    }


def plan_cuentas(db: Session) -> list[dict]:
    return [_cuenta_out(c) for c in repository.listar_cuentas(db)]


def crear_cuenta(db: Session, datos, *, actor: int) -> dict:
    if repository.cuenta_por_codigo(db, datos.codigo):
        raise ConflictError("Ya existe una cuenta con ese código", field="codigo")
    padre_id = None
    if datos.cuenta_padre_codigo:
        padre = repository.cuenta_por_codigo(db, datos.cuenta_padre_codigo)
        if padre is None:
            raise ValidationError("Cuenta padre inexistente", field="cuenta_padre_codigo")
        padre_id = padre.id
    c = repository.crear_cuenta(
        db, codigo=datos.codigo.strip(), nombre=datos.nombre.strip(), tipo=datos.tipo,
        cuenta_padre_id=padre_id, imputable=datos.imputable,
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="cuenta_contable", entidad_id=c.id,
                     despues={"codigo": c.codigo, "nombre": c.nombre})
    return _cuenta_out(c)


def _cuenta_id(db: Session, codigo: str):
    c = repository.cuenta_por_codigo(db, codigo)
    if c is None:
        raise ValidationError(f"Cuenta contable inexistente: {codigo}", field="cuenta")
    return c


# ============================================================ periodo
def _periodo_activo_o_none(db: Session, fecha: date):
    return repository.periodo_de_fecha(db, fecha)


def listar_periodos(db: Session) -> list[PeriodoOut]:
    return [
        PeriodoOut(id=p.id, fecha_inicio=p.fecha_inicio, fecha_fin=p.fecha_fin,
                  estado=p.estado, cerrado_en=p.cerrado_en)
        for p in repository.listar_periodos(db)
    ]


def crear_periodo(db: Session, datos, *, user: CurrentUser) -> PeriodoOut:
    if not puede_gestionar_contabilidad(user):
        raise NoAutorizadoError("Solo Gerencia General o Contador administra los periodos contables")
    if datos.fecha_fin < datos.fecha_inicio:
        raise ValidationError("La fecha de fin no puede ser anterior a la de inicio", field="fecha_fin")
    p = repository.crear_periodo(db, fecha_inicio=datos.fecha_inicio, fecha_fin=datos.fecha_fin, estado="abierto")
    registrar_cambio(db, actor=user.id, accion="crear", entidad="periodo_contable", entidad_id=p.id,
                     despues={"inicio": str(p.fecha_inicio), "fin": str(p.fecha_fin)})
    return PeriodoOut(id=p.id, fecha_inicio=p.fecha_inicio, fecha_fin=p.fecha_fin, estado=p.estado, cerrado_en=None)


def cerrar_periodo(db: Session, periodo_id: int, *, user: CurrentUser) -> PeriodoOut:
    """Gerencia General o Contador cierra un periodo (ACC011); tras cerrarlo, los
    asientos con fecha en su rango exigen `ajuste_de_asiento_id`."""
    if not puede_gestionar_contabilidad(user):
        raise NoAutorizadoError("Solo Gerencia General o Contador cierra un periodo contable")
    p = repository.periodo_por_id(db, periodo_id)
    if p is None:
        raise NotFoundError("Periodo no encontrado")
    if p.estado == "cerrado":
        raise ConflictError("El periodo ya está cerrado")
    p.estado = "cerrado"
    p.cerrado_por = user.id
    p.cerrado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="periodo_contable", entidad_id=periodo_id,
                     antes={"estado": "abierto"}, despues={"estado": "cerrado"})
    return PeriodoOut(id=p.id, fecha_inicio=p.fecha_inicio, fecha_fin=p.fecha_fin, estado=p.estado,
                      cerrado_en=p.cerrado_en)


# ============================================================ libro diario
def _asiento_out(db: Session, a: Asiento) -> AsientoOut:
    lineas = []
    td = th = Decimal("0")
    for ln in a.lineas:
        cta = repository.cuenta_por_id(db, ln.cuenta_contable_id)
        lineas.append(LineaAsientoOut(
            id=ln.id, cuenta_id=ln.cuenta_contable_id, cuenta_codigo=cta.codigo if cta else "?",
            cuenta_nombre=cta.nombre if cta else "?", debe=_q(ln.debe), haber=_q(ln.haber),
        ))
        td += _q(ln.debe)
        th += _q(ln.haber)
    return AsientoOut(
        id=a.id, fecha=a.fecha, glosa=a.glosa, origen=a.origen, origen_id=a.origen_id,
        ajuste_de_asiento_id=a.ajuste_de_asiento_id, lineas=lineas,
        total_debe=_q(td), total_haber=_q(th), creado_en=a.creado_en,
    )


def crear_asiento(
    db: Session, *, fecha: date, glosa: str, lineas: list[dict], origen: str = "manual",
    origen_id: int | None = None, ajuste_de_asiento_id: int | None = None, actor: int | None = None,
) -> Asiento:
    """`lineas` = [{"cuenta_id" | "cuenta_codigo", "debe", "haber"}, ...]. Núcleo
    reutilizado tanto por el endpoint manual como por el motor de asiento automático."""
    if len(lineas) < 2:
        raise ValidationError("Un asiento necesita al menos dos líneas", field="lineas")
    total_debe = _q(sum((Decimal(str(ln.get("debe", 0))) for ln in lineas), Decimal("0")))
    total_haber = _q(sum((Decimal(str(ln.get("haber", 0))) for ln in lineas), Decimal("0")))
    if total_debe != total_haber or total_debe == 0:
        raise ValidationError(
            f"El asiento no cuadra: Σ debe = {total_debe}, Σ haber = {total_haber}", field="lineas"
        )

    periodo = _periodo_activo_o_none(db, fecha)
    if periodo is not None and periodo.estado == "cerrado" and ajuste_de_asiento_id is None:
        raise ConflictError(
            f"El periodo que cubre {fecha} está cerrado; registra un asiento de ajuste "
            "(`ajuste_de_asiento_id`) en vez de editar/crear directo.",
        )
    if ajuste_de_asiento_id is not None and repository.obtener_asiento(db, ajuste_de_asiento_id) is None:
        raise ValidationError("El asiento a ajustar no existe", field="ajuste_de_asiento_id")

    a = repository.crear_asiento(
        db, fecha=fecha, glosa=glosa.strip(), origen=origen, origen_id=origen_id,
        ajuste_de_asiento_id=ajuste_de_asiento_id, creado_por=actor,
    )
    for ln in lineas:
        cuenta_id = ln.get("cuenta_id")
        if cuenta_id is None:
            cuenta_id = _cuenta_id(db, ln["cuenta_codigo"]).id
        repository.agregar_linea(
            db, asiento_id=a.id, cuenta_contable_id=cuenta_id,
            debe=_q(ln.get("debe", 0)), haber=_q(ln.get("haber", 0)),
        )
    db.flush()
    db.refresh(a)
    registrar_cambio(db, actor=actor, accion="crear", entidad="asiento", entidad_id=a.id,
                     despues={"fecha": str(fecha), "glosa": glosa, "total": str(total_debe), "origen": origen})
    return a


def crear_asiento_manual(db: Session, datos, *, user: CurrentUser) -> AsientoOut:
    lineas = [{"cuenta_codigo": ln.cuenta, "debe": ln.debe, "haber": ln.haber} for ln in datos.lineas]
    a = crear_asiento(
        db, fecha=datos.fecha, glosa=datos.glosa, lineas=lineas, origen="manual",
        ajuste_de_asiento_id=datos.ajuste_de_asiento_id, actor=user.id,
    )
    return _asiento_out(db, a)


def listar_asientos(db: Session, *, origen: str | None, desde: date | None, hasta: date | None,
                    offset: int, limit: int) -> tuple[list[AsientoOut], int]:
    filas, total = repository.buscar_asientos(db, origen=origen, desde=desde, hasta=hasta, offset=offset, limit=limit)
    return [_asiento_out(db, a) for a in filas], total


# ============================================================ mayor / balance / estado
def _rango_de_periodo(db: Session, periodo: str | None) -> tuple[date | None, date | None, str | None]:
    """`periodo` = id de `periodo_contable`, o `YYYY-MM` para un mes calendario."""
    if not periodo:
        return None, None, None
    if periodo.isdigit():
        p = repository.periodo_por_id(db, int(periodo))
        if p is None:
            raise NotFoundError("Periodo no encontrado")
        return p.fecha_inicio, p.fecha_fin, periodo
    try:
        anio, mes = (int(x) for x in periodo.split("-"))
        desde = date(anio, mes, 1)
        hasta = date(anio + (mes == 12), (mes % 12) + 1, 1)
        from datetime import timedelta

        hasta = hasta - timedelta(days=1)
        return desde, hasta, periodo
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("Periodo inválido: usa el id o 'YYYY-MM'", field="periodo") from exc


def mayor(db: Session, *, cuenta_codigo: str, periodo: str | None) -> MayorOut:
    cta = repository.cuenta_por_codigo(db, cuenta_codigo)
    if cta is None:
        raise NotFoundError("Cuenta contable no encontrada")
    desde, hasta, _ = _rango_de_periodo(db, periodo)
    filas = repository.lineas_de_cuenta(db, cta.id, desde=desde, hasta=hasta)
    movs = [
        MovimientoMayorOut(asiento_id=a.id, fecha=a.fecha, glosa=a.glosa, debe=_q(ln.debe), haber=_q(ln.haber))
        for ln, a in filas
    ]
    signo = 1 if cta.tipo in ("activo", "gasto") else -1
    saldo = _q(sum((signo * (_q(m.debe) - _q(m.haber)) for m in movs), Decimal("0")))
    return MayorOut(cuenta_codigo=cta.codigo, cuenta_nombre=cta.nombre, movimientos=movs, saldo=saldo)


def balance_comprobacion(db: Session, *, periodo: str | None) -> BalanceComprobacionOut:
    desde, hasta, etiqueta = _rango_de_periodo(db, periodo)
    filas = repository.lineas_en_rango(db, desde=desde, hasta=hasta)
    por_cuenta: dict[int, list[Decimal, Decimal]] = {}
    for ln, _a in filas:
        acc = por_cuenta.setdefault(ln.cuenta_contable_id, [Decimal("0"), Decimal("0")])
        acc[0] += _q(ln.debe)
        acc[1] += _q(ln.haber)
    salida = []
    total_debe = total_haber = Decimal("0")
    for cid, (d, h) in por_cuenta.items():
        cta = repository.cuenta_por_id(db, cid)
        salida.append(FilaBalanceOut(cuenta_codigo=cta.codigo, cuenta_nombre=cta.nombre, tipo=cta.tipo,
                                     debe=_q(d), haber=_q(h)))
        total_debe += _q(d)
        total_haber += _q(h)
    salida.sort(key=lambda f: f.cuenta_codigo)
    return BalanceComprobacionOut(
        periodo=etiqueta, filas=salida, total_debe=_q(total_debe), total_haber=_q(total_haber),
        cuadrado=(_q(total_debe) == _q(total_haber)),
    )


def estado_resultados(db: Session, *, periodo: str | None, sucursal_id: int | None = None) -> EstadoResultadosOut:
    bal = balance_comprobacion(db, periodo=periodo)
    ingresos = sum((f.haber - f.debe for f in bal.filas if f.tipo == "ingreso"), Decimal("0"))
    costos = sum((f.debe - f.haber for f in bal.filas if f.cuenta_codigo.startswith(("5",))), Decimal("0"))
    gastos = sum((f.debe - f.haber for f in bal.filas if f.cuenta_codigo.startswith(("6",))), Decimal("0"))
    return EstadoResultadosOut(
        periodo=bal.periodo, sucursal_id=sucursal_id, ingresos=_q(ingresos), costos=_q(costos),
        gastos=_q(gastos), utilidad_neta=_q(ingresos - costos - gastos),
        detalle=[f for f in bal.filas if f.tipo in ("ingreso", "gasto")],
    )


# ============================================================ cheques
def _cheque_out(c) -> dict:
    return {
        "id": c.id, "tipo": c.tipo, "banco": c.banco, "numero": c.numero, "monto": _q(c.monto),
        "fecha": c.fecha, "estado": c.estado, "cliente_id": c.cliente_id, "proveedor_id": c.proveedor_id,
        "beneficiario_id": c.beneficiario_id, "documento_origen_tipo": c.documento_origen_tipo,
        "documento_origen_id": c.documento_origen_id,
    }


def registrar_cheque(db: Session, datos, *, actor: int) -> dict:
    c = repository.crear_cheque(
        db, tipo=datos.tipo, banco=(datos.banco or "").strip() or None, numero=(datos.numero or "").strip() or None,
        monto=_q(datos.monto), fecha=datos.fecha, estado="en_cartera",
        cliente_id=datos.cliente_id, proveedor_id=datos.proveedor_id, beneficiario_id=datos.beneficiario_id,
        documento_origen_tipo=datos.documento_origen_tipo, documento_origen_id=datos.documento_origen_id,
        creado_por=actor,
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="cheque", entidad_id=c.id,
                     despues={"tipo": c.tipo, "monto": str(c.monto)})
    return _cheque_out(c)


def listar_cheques(db: Session, *, tipo: str | None, estado: str | None) -> list[dict]:
    return [_cheque_out(c) for c in repository.buscar_cheques(db, tipo=tipo, estado=estado)]


def protestar_cheque(db: Session, cheque_id: int, *, user: CurrentUser) -> dict:
    """FR-007 / ACC014: revierte el cobro asociado y reactiva la CxC, de forma
    atómica (misma transacción del request)."""
    c = repository.obtener_cheque(db, cheque_id, for_update=True)
    if c is None:
        raise NotFoundError("Cheque no encontrado")
    if c.tipo != "recibido":
        raise ValidationError("Solo se protesta un cheque recibido", field="tipo")
    if c.estado == "protestado":
        raise ConflictError("El cheque ya está protestado")
    c.estado = "protestado"
    db.flush()

    if c.documento_origen_tipo == "cobro_cxc" and c.documento_origen_id:
        _reactivar_cobro(db, cobro_id=c.documento_origen_id, actor=user.id)
    elif c.documento_origen_tipo in ("venta", "orden_trabajo") and c.documento_origen_id and c.cliente_id:
        from ventas import crear_cxc_externa

        crear_cxc_externa(
            db, origen_tipo=c.documento_origen_tipo, origen_id=c.documento_origen_id,
            cliente_id=c.cliente_id, monto=c.monto,
        )
    else:
        logger.warning("cheque %s protestado sin origen para reactivar la CxC automáticamente", cheque_id)

    registrar_cambio(db, actor=user.id, accion="protestar", entidad="cheque", entidad_id=cheque_id,
                     despues={"estado": "protestado"})
    return _cheque_out(c)


def _reactivar_cobro(db: Session, *, cobro_id: int, actor: int) -> None:
    """El cobro que hizo este cheque queda inválido: reactiva/crea la CxC por ese monto."""
    from contabilidad.models import CobroCxc
    from ventas import crear_cxc_externa, listar_cuentas_por_cobrar

    cobro = db.get(CobroCxc, cobro_id)
    if cobro is None:
        return
    original = next((c for c in listar_cuentas_por_cobrar(db) if c["id"] == cobro.cxc_id), None)
    if original is None:
        return
    crear_cxc_externa(
        db, origen_tipo=original["origen_tipo"], origen_id=original["origen_id"],
        cliente_id=original["cliente_id"], monto=cobro.monto,
    )


# ============================================================ CxC (cobros + aging)
def _dias(fecha_ref, fecha_corte: date) -> int:
    if hasattr(fecha_ref, "date"):
        fecha_ref = fecha_ref.date()
    return max(0, (fecha_corte - fecha_ref).days)


def _cliente_nombre(db: Session, cid: int) -> str | None:
    from clientes import cliente_mini

    c = cliente_mini(db, cid)
    return c.get("nombre") if c else None


def listar_cxc(db: Session, *, cliente_id: int | None, estado: str | None) -> list[CxcOut]:
    from ventas import listar_cuentas_por_cobrar

    hoy = date.today()
    salida = []
    for c in listar_cuentas_por_cobrar(db, cliente_id=cliente_id, estado=estado):
        salida.append(CxcOut(
            id=c["id"], origen_tipo=c["origen_tipo"], origen_id=c["origen_id"], cliente_id=c["cliente_id"],
            cliente_nombre=_cliente_nombre(db, c["cliente_id"]), monto_original=_q(c["monto_original"]),
            saldo=_q(c["saldo"]), estado=c["estado"], dias=_dias(c["creado_en"], hoy), creado_en=c["creado_en"],
        ))
    return salida


def registrar_cobro_cxc(db: Session, cxc_id: int, datos, *, user: CurrentUser) -> CxcOut:
    from shared.models import MedioPago
    from ventas import listar_cuentas_por_cobrar, marcar_cxc_saldada

    from sqlalchemy import select as _select

    fila = next((c for c in listar_cuentas_por_cobrar(db) if c["id"] == cxc_id), None)
    if fila is None:
        raise NotFoundError("Cuenta por cobrar no encontrada")
    if fila["estado"] != "pendiente":
        raise ConflictError("La cuenta por cobrar ya no está pendiente")
    if datos.monto > fila["saldo"]:
        raise ValidationError(f"El cobro ({datos.monto}) supera el saldo ({fila['saldo']})", field="monto")

    medio = db.scalars(_select(MedioPago).where(MedioPago.clave == datos.medio_pago.strip())).first()
    if medio is None:
        raise ValidationError(f"Medio de pago desconocido: {datos.medio_pago}", field="medio_pago")

    cheque_id = None
    if datos.cheque:
        ch = registrar_cheque(db, datos.cheque, actor=user.id)
        cheque_id = ch["id"]

    fecha = datos.fecha or date.today()
    cobro = repository.agregar_cobro(
        db, cxc_id=cxc_id, monto=_q(datos.monto), medio_pago_id=medio.id, fecha=fecha,
        cheque_id=cheque_id, creado_por=user.id,
    )
    marcar_cxc_saldada(db, cxc_id, monto=datos.monto)

    from contabilidad.asientos_auto import generar

    generar(db, evento="cobro_cxc", monto=datos.monto, glosa=f"Cobro CxC #{cxc_id}",
           origen="cobro", origen_id=cobro.id, actor=user.id)

    registrar_cambio(db, actor=user.id, accion="crear", entidad="cobro_cxc", entidad_id=cobro.id,
                     despues={"cxc_id": cxc_id, "monto": str(datos.monto)})
    actualizado = next(c for c in listar_cuentas_por_cobrar(db) if c["id"] == cxc_id)
    hoy = date.today()
    return CxcOut(
        id=actualizado["id"], origen_tipo=actualizado["origen_tipo"], origen_id=actualizado["origen_id"],
        cliente_id=actualizado["cliente_id"], cliente_nombre=_cliente_nombre(db, actualizado["cliente_id"]),
        monto_original=_q(actualizado["monto_original"]), saldo=_q(actualizado["saldo"]),
        estado=actualizado["estado"], dias=_dias(actualizado["creado_en"], hoy), creado_en=actualizado["creado_en"],
    )


def _tramos(items: list[tuple[int, Decimal]]) -> AgingOut:
    hoy = date.today()
    grupos = {etq: [0, Decimal("0")] for _, _, etq in _TRAMOS}
    total = Decimal("0")
    for dias, saldo in items:
        for lo, hi, etq in _TRAMOS:
            if dias >= lo and (hi is None or dias <= hi):
                grupos[etq][0] += 1
                grupos[etq][1] += saldo
                break
        total += saldo
    return AgingOut(
        fecha_corte=hoy,
        tramos=[TramoAgingOut(tramo=etq, cantidad=grupos[etq][0], saldo=_q(grupos[etq][1])) for _, _, etq in _TRAMOS],
        total=_q(total),
    )


def aging_cxc(db: Session, *, fecha_corte: date | None = None) -> AgingOut:
    from ventas import listar_cuentas_por_cobrar

    corte = fecha_corte or date.today()
    items = [
        (_dias(c["creado_en"], corte), _q(c["saldo"]))
        for c in listar_cuentas_por_cobrar(db, estado="pendiente")
    ]
    out = _tramos(items)
    out.fecha_corte = corte
    return out


def cxc_pendientes(db: Session) -> list[CxcOut]:
    return listar_cxc(db, cliente_id=None, estado="pendiente")


# ============================================================ rentabilidad
def rentabilidad_sucursal(db: Session, *, periodo: str | None, sucursal_id: int | None) -> list[RentabilidadSucursalOut]:
    """Ingresos − costo de ventas/servicios − gastos operativos, por sucursal
    (research D8, versión operativa construida directo sobre las ventas confirmadas
    y las OT entregadas del rango — no sobre el libro diario, que no distingue
    sucursal en esta fase)."""
    from shared.models import Sucursal
    from servicio_tecnico import resumen_periodo as _ot_resumen
    from ventas import resumen_periodo as _venta_resumen

    desde, hasta, _ = _rango_de_periodo(db, periodo)
    desde = desde or date(1970, 1, 1)
    hasta = hasta or date(2999, 12, 31)
    sucs = [sucursal_id] if sucursal_id else [s.id for s in db.query(Sucursal).all()]
    salida = []
    for sid in sucs:
        suc = db.get(Sucursal, sid)
        if suc is None:
            continue
        rv = _venta_resumen(db, sucursal_id=sid, desde=desde, hasta=hasta)
        ro = _ot_resumen(db, sucursal_id=sid, desde=desde, hasta=hasta)
        ingresos = _q(rv["ingresos"] + ro["ingresos"])
        costos = _q(rv["costos"] + ro["costos"])
        gastos_suc = sum(
            (_q(g.monto) for g in repository.gastos_confirmados_en_rango(db, sucursal_id=sid, desde=desde, hasta=hasta)),
            Decimal("0"),
        )
        salida.append(RentabilidadSucursalOut(
            sucursal_id=sid, sucursal_nombre=suc.nombre, ingresos=ingresos, costos=costos,
            gastos_operativos=_q(gastos_suc), utilidad_neta=_q(ingresos - costos - gastos_suc),
        ))
    return salida


# ============================================================ beneficiarios
def _beneficiario_out(b) -> dict:
    return {"id": b.id, "nombre": b.nombre, "identificacion": b.identificacion,
            "tipo_servicio": b.tipo_servicio, "activo": b.activo}


def listar_beneficiarios(db: Session, *, q: str | None) -> list[dict]:
    return [_beneficiario_out(b) for b in repository.buscar_beneficiarios(db, q=q)]


def crear_beneficiario(db: Session, datos, *, actor: int) -> dict:
    if repository.beneficiario_por_nombre(db, datos.nombre):
        raise ConflictError("Ya existe un beneficiario con ese nombre", field="nombre")
    b = repository.crear_beneficiario(
        db, nombre=datos.nombre.strip(), identificacion=(datos.identificacion or "").strip() or None,
        tipo_servicio=(datos.tipo_servicio or "").strip() or None,
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="beneficiario", entidad_id=b.id,
                     despues={"nombre": b.nombre})
    return _beneficiario_out(b)


# ============================================================ CxP (compras y gastos)
def _proveedor_nombre(db: Session, pid: int | None) -> str | None:
    if pid is None:
        return None
    from proveedores.public import proveedor_nombre

    return proveedor_nombre(db, pid)


def _cxp_out(db: Session, c) -> CxpOut:
    hoy = date.today()
    return CxpOut(
        id=c.id, origen_tipo=c.origen_tipo, orden_compra_id=c.orden_compra_id, gasto_id=c.gasto_id,
        proveedor_id=c.proveedor_id, proveedor_nombre=_proveedor_nombre(db, c.proveedor_id) if c.proveedor_id else None,
        beneficiario_id=c.beneficiario_id,
        beneficiario_nombre=repository.beneficiario_por_id(db, c.beneficiario_id).nombre if c.beneficiario_id else None,
        monto_original=_q(c.monto_original), saldo=_q(c.saldo), estado=c.estado,
        dias=_dias(c.creado_en, hoy), creado_en=c.creado_en,
    )


def listar_cxp(db: Session, *, proveedor_id: int | None, beneficiario_id: int | None,
              origen_tipo: str | None, estado: str | None) -> list[CxpOut]:
    return [
        _cxp_out(db, c) for c in repository.buscar_cxp(
            db, proveedor_id=proveedor_id, beneficiario_id=beneficiario_id,
            origen_tipo=origen_tipo, estado=estado,
        )
    ]


def registrar_pago_cxp(db: Session, cxp_id: int, datos, *, user: CurrentUser) -> CxpOut:
    if not puede_gestionar_contabilidad(user):
        raise NoAutorizadoError("Solo Gerencia General o Contador registra pagos de cuentas por pagar")
    c = repository.obtener_cxp(db, cxp_id, for_update=True)
    if c is None:
        raise NotFoundError("Cuenta por pagar no encontrada")
    if c.estado != "pendiente":
        raise ConflictError("La cuenta por pagar ya no está pendiente")
    if datos.monto > c.saldo:
        raise ValidationError(f"El pago ({datos.monto}) supera el saldo ({c.saldo})", field="monto")

    from shared.models import MedioPago
    from sqlalchemy import select as _select

    medio = db.scalars(_select(MedioPago).where(MedioPago.clave == datos.medio_pago.strip())).first()
    if medio is None:
        raise ValidationError(f"Medio de pago desconocido: {datos.medio_pago}", field="medio_pago")

    cheque_id = None
    if datos.cheque:
        ch = registrar_cheque(db, datos.cheque, actor=user.id)
        cheque_id = ch["id"]

    retencion = None
    if datos.retencion:
        retencion = {"porcentaje": float(datos.retencion.porcentaje) if datos.retencion.porcentaje is not None else None,
                    "monto": float(datos.retencion.monto), "comprobante": datos.retencion.comprobante}

    fecha = datos.fecha or date.today()
    pago = repository.agregar_pago_cxp(
        db, cxp_id=cxp_id, monto=_q(datos.monto), medio_pago_id=medio.id, fecha=fecha,
        cheque_id=cheque_id, retencion_fuente=retencion, creado_por=user.id,
    )
    c.saldo = _q(_q(c.saldo) - _q(datos.monto))
    if c.saldo <= 0:
        c.saldo = Decimal("0")
        c.estado = "saldada"
    db.flush()

    from contabilidad.asientos_auto import generar

    generar(db, evento="pago_cxp", monto=datos.monto, glosa=f"Pago CxP #{cxp_id}",
           origen="pago", origen_id=pago.id, condicion_ctx={"origen_tipo": c.origen_tipo}, actor=user.id)

    registrar_cambio(db, actor=user.id, accion="crear", entidad="pago_cxp", entidad_id=pago.id,
                     despues={"cxp_id": cxp_id, "monto": str(datos.monto), "retencion": retencion})
    db.refresh(c)
    return _cxp_out(db, c)


def aging_cxp(db: Session, *, fecha_corte: date | None = None) -> AgingOut:
    corte = fecha_corte or date.today()
    items = [
        (_dias(c.creado_en, corte), _q(c.saldo))
        for c in repository.buscar_cxp(db, proveedor_id=None, beneficiario_id=None, origen_tipo=None, estado="pendiente")
    ]
    out = _tramos(items)
    out.fecha_corte = corte
    return out


# ============================================================ receptor de compras (002)
def recibir_compra_cxp(db: Session, orden) -> None:
    """Registrado como receptor de `proveedores.registrar_receptor_cxp` (main.py):
    al completarse la recepción de una OC, crea la CxP por `importe_a_pagar` y su
    asiento automático."""
    if repository.cxp_de_orden_compra(db, orden.id) is not None:
        return  # idempotente (una orden no genera dos CxP)
    monto = _q(getattr(orden, "importe_a_pagar", None) or 0)
    if monto <= 0:
        return
    repository.crear_cxp(
        db, origen_tipo="orden_compra", orden_compra_id=orden.id, gasto_id=None,
        proveedor_id=orden.proveedor_id, beneficiario_id=None,
        monto_original=monto, saldo=monto, estado="pendiente",
    )
    from contabilidad.asientos_auto import generar

    generar(db, evento="compra", monto=monto, glosa=f"Recepción de compra OC #{orden.id}",
           origen="compra", origen_id=orden.id)
