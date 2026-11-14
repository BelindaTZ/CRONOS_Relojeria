"""Acceso a datos del módulo `contabilidad`."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from contabilidad.models import (
    Asiento,
    Beneficiario,
    Caja,
    Cheque,
    CobroCxc,
    CuentaContable,
    CuentaPorPagar,
    Gasto,
    GastoRecurrente,
    LineaAsiento,
    MovimientoCaja,
    PagoCxp,
    PeriodoContable,
    ReglaAsientoAutomatico,
    SesionCaja,
)


# ------------------------------------------------------------ plan de cuentas
def cuenta_por_codigo(db: Session, codigo: str) -> CuentaContable | None:
    return db.scalars(select(CuentaContable).where(CuentaContable.codigo == codigo)).first()


def cuenta_por_id(db: Session, cid: int) -> CuentaContable | None:
    return db.get(CuentaContable, cid)


def listar_cuentas(db: Session) -> list[CuentaContable]:
    return list(db.scalars(select(CuentaContable).order_by(CuentaContable.codigo)))


def crear_cuenta(db: Session, **campos) -> CuentaContable:
    c = CuentaContable(**campos)
    db.add(c)
    db.flush()
    return c


# ------------------------------------------------------------ periodo contable
def periodo_de_fecha(db: Session, fecha: date) -> PeriodoContable | None:
    return db.scalars(
        select(PeriodoContable).where(
            PeriodoContable.fecha_inicio <= fecha, PeriodoContable.fecha_fin >= fecha
        )
    ).first()


def periodo_por_id(db: Session, pid: int) -> PeriodoContable | None:
    return db.get(PeriodoContable, pid)


def listar_periodos(db: Session) -> list[PeriodoContable]:
    return list(db.scalars(select(PeriodoContable).order_by(PeriodoContable.fecha_inicio.desc())))


def crear_periodo(db: Session, **campos) -> PeriodoContable:
    p = PeriodoContable(**campos)
    db.add(p)
    db.flush()
    return p


# ------------------------------------------------------------ asientos
def crear_asiento(db: Session, **campos) -> Asiento:
    a = Asiento(**campos)
    db.add(a)
    db.flush()
    return a


def agregar_linea(db: Session, **campos) -> LineaAsiento:
    ln = LineaAsiento(**campos)
    db.add(ln)
    db.flush()
    return ln


def obtener_asiento(db: Session, aid: int) -> Asiento | None:
    return db.get(Asiento, aid)


def buscar_asientos(
    db: Session, *, origen: str | None, desde: date | None, hasta: date | None, offset: int, limit: int,
) -> tuple[list[Asiento], int]:
    stmt = select(Asiento)
    if origen:
        stmt = stmt.where(Asiento.origen == origen)
    if desde:
        stmt = stmt.where(Asiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(Asiento.fecha <= hasta)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Asiento.fecha.desc(), Asiento.id.desc()).offset(offset).limit(limit)))
    return filas, int(total)


def lineas_de_cuenta(
    db: Session, cuenta_id: int, *, desde: date | None, hasta: date | None,
) -> list[tuple[LineaAsiento, Asiento]]:
    stmt = (
        select(LineaAsiento, Asiento)
        .join(Asiento, Asiento.id == LineaAsiento.asiento_id)
        .where(LineaAsiento.cuenta_contable_id == cuenta_id)
    )
    if desde:
        stmt = stmt.where(Asiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(Asiento.fecha <= hasta)
    return list(db.execute(stmt.order_by(Asiento.fecha, Asiento.id)).all())


def lineas_en_rango(db: Session, *, desde: date | None, hasta: date | None) -> list[tuple[LineaAsiento, Asiento]]:
    stmt = select(LineaAsiento, Asiento).join(Asiento, Asiento.id == LineaAsiento.asiento_id)
    if desde:
        stmt = stmt.where(Asiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(Asiento.fecha <= hasta)
    return list(db.execute(stmt).all())


# ------------------------------------------------------------ caja
def caja_de_sucursal(db: Session, sucursal_id: int) -> Caja | None:
    return db.scalars(select(Caja).where(Caja.sucursal_id == sucursal_id)).first()


def crear_caja(db: Session, **campos) -> Caja:
    c = Caja(**campos)
    db.add(c)
    db.flush()
    return c


def sesion_abierta(db: Session, caja_id: int, *, for_update: bool = False) -> SesionCaja | None:
    stmt = select(SesionCaja).where(SesionCaja.caja_id == caja_id, SesionCaja.estado == "abierta")
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def crear_sesion(db: Session, **campos) -> SesionCaja:
    s = SesionCaja(**campos)
    db.add(s)
    db.flush()
    return s


def obtener_sesion(db: Session, sid: int) -> SesionCaja | None:
    return db.get(SesionCaja, sid)


def agregar_movimiento_caja(db: Session, **campos) -> MovimientoCaja:
    m = MovimientoCaja(**campos)
    db.add(m)
    db.flush()
    return m


def movimientos_de_sesion(db: Session, sesion_id: int) -> list[MovimientoCaja]:
    return list(db.scalars(
        select(MovimientoCaja).where(MovimientoCaja.sesion_caja_id == sesion_id).order_by(MovimientoCaja.creado_en)
    ))


# ------------------------------------------------------------ cheques
def crear_cheque(db: Session, **campos) -> Cheque:
    c = Cheque(**campos)
    db.add(c)
    db.flush()
    return c


def obtener_cheque(db: Session, cid: int, *, for_update: bool = False) -> Cheque | None:
    stmt = select(Cheque).where(Cheque.id == cid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def buscar_cheques(db: Session, *, tipo: str | None, estado: str | None) -> list[Cheque]:
    stmt = select(Cheque)
    if tipo:
        stmt = stmt.where(Cheque.tipo == tipo)
    if estado:
        stmt = stmt.where(Cheque.estado == estado)
    return list(db.scalars(stmt.order_by(Cheque.fecha.desc())))


# ------------------------------------------------------------ CxC (cobros)
def agregar_cobro(db: Session, **campos) -> CobroCxc:
    c = CobroCxc(**campos)
    db.add(c)
    db.flush()
    return c


def cobros_de_cxc(db: Session, cxc_id: int) -> list[CobroCxc]:
    return list(db.scalars(select(CobroCxc).where(CobroCxc.cxc_id == cxc_id).order_by(CobroCxc.fecha)))


# ------------------------------------------------------------ beneficiarios
def beneficiario_por_id(db: Session, bid: int) -> Beneficiario | None:
    return db.get(Beneficiario, bid)


def beneficiario_por_nombre(db: Session, nombre: str) -> Beneficiario | None:
    return db.scalars(
        select(Beneficiario).where(func.lower(Beneficiario.nombre) == nombre.strip().lower())
    ).first()


def crear_beneficiario(db: Session, **campos) -> Beneficiario:
    b = Beneficiario(**campos)
    db.add(b)
    db.flush()
    return b


def buscar_beneficiarios(db: Session, *, q: str | None) -> list[Beneficiario]:
    stmt = select(Beneficiario).where(Beneficiario.activo.is_(True))
    if q:
        stmt = stmt.where(Beneficiario.nombre.ilike(f"%{q.strip()}%"))
    return list(db.scalars(stmt.order_by(Beneficiario.nombre)))


# ------------------------------------------------------------ CxP
def crear_cxp(db: Session, **campos) -> CuentaPorPagar:
    c = CuentaPorPagar(**campos)
    db.add(c)
    db.flush()
    return c


def obtener_cxp(db: Session, cid: int, *, for_update: bool = False) -> CuentaPorPagar | None:
    stmt = select(CuentaPorPagar).where(CuentaPorPagar.id == cid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def buscar_cxp(
    db: Session, *, proveedor_id: int | None, beneficiario_id: int | None,
    origen_tipo: str | None, estado: str | None,
) -> list[CuentaPorPagar]:
    stmt = select(CuentaPorPagar)
    if proveedor_id:
        stmt = stmt.where(CuentaPorPagar.proveedor_id == proveedor_id)
    if beneficiario_id:
        stmt = stmt.where(CuentaPorPagar.beneficiario_id == beneficiario_id)
    if origen_tipo:
        stmt = stmt.where(CuentaPorPagar.origen_tipo == origen_tipo)
    if estado:
        stmt = stmt.where(CuentaPorPagar.estado == estado)
    return list(db.scalars(stmt.order_by(CuentaPorPagar.creado_en.desc())))


def cxp_de_orden_compra(db: Session, oc_id: int) -> CuentaPorPagar | None:
    return db.scalars(select(CuentaPorPagar).where(CuentaPorPagar.orden_compra_id == oc_id)).first()


def agregar_pago_cxp(db: Session, **campos) -> PagoCxp:
    p = PagoCxp(**campos)
    db.add(p)
    db.flush()
    return p


def pagos_de_cxp(db: Session, cxp_id: int) -> list[PagoCxp]:
    return list(db.scalars(select(PagoCxp).where(PagoCxp.cxp_id == cxp_id).order_by(PagoCxp.fecha)))


# ------------------------------------------------------------ gastos
def crear_gasto(db: Session, **campos) -> Gasto:
    g = Gasto(**campos)
    db.add(g)
    db.flush()
    return g


def obtener_gasto(db: Session, gid: int, *, for_update: bool = False) -> Gasto | None:
    stmt = select(Gasto).where(Gasto.id == gid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def buscar_gastos(
    db: Session, *, sucursales: list[int] | None, sucursal_id: int | None, categoria_gasto_id: int | None,
    estado_pago: str | None, estado: str | None, desde: date | None, hasta: date | None,
    offset: int, limit: int,
) -> tuple[list[Gasto], int]:
    stmt = select(Gasto)
    if sucursales is not None:
        stmt = stmt.where(Gasto.sucursal_id.in_(sucursales or [-1]))
    if sucursal_id:
        stmt = stmt.where(Gasto.sucursal_id == sucursal_id)
    if categoria_gasto_id:
        stmt = stmt.where(Gasto.categoria_gasto_id == categoria_gasto_id)
    if estado_pago:
        stmt = stmt.where(Gasto.estado_pago == estado_pago)
    if estado:
        stmt = stmt.where(Gasto.estado == estado)
    if desde:
        stmt = stmt.where(Gasto.fecha >= desde)
    if hasta:
        stmt = stmt.where(Gasto.fecha <= hasta)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Gasto.fecha.desc()).offset(offset).limit(limit)))
    return filas, int(total)


def gastos_confirmados_en_rango(db: Session, *, sucursal_id: int | None, desde: date, hasta: date) -> list[Gasto]:
    stmt = select(Gasto).where(Gasto.estado == "confirmado", Gasto.fecha >= desde, Gasto.fecha <= hasta)
    if sucursal_id:
        stmt = stmt.where(Gasto.sucursal_id == sucursal_id)
    return list(db.scalars(stmt))


# ------------------------------------------------------------ gastos recurrentes
def crear_gasto_recurrente(db: Session, **campos) -> GastoRecurrente:
    g = GastoRecurrente(**campos)
    db.add(g)
    db.flush()
    return g


def obtener_gasto_recurrente(db: Session, gid: int) -> GastoRecurrente | None:
    return db.get(GastoRecurrente, gid)


def listar_gastos_recurrentes(db: Session) -> list[GastoRecurrente]:
    return list(db.scalars(select(GastoRecurrente).order_by(GastoRecurrente.descripcion)))


def recurrentes_vencidos(db: Session, *, hoy: date) -> list[GastoRecurrente]:
    return list(db.scalars(
        select(GastoRecurrente).where(
            GastoRecurrente.estado == "activo", GastoRecurrente.proxima_generacion <= hoy
        )
    ))


# ------------------------------------------------------------ reglas de asiento
def listar_reglas(db: Session, *, evento: str | None = None) -> list[ReglaAsientoAutomatico]:
    stmt = select(ReglaAsientoAutomatico).where(ReglaAsientoAutomatico.activa.is_(True))
    if evento:
        stmt = stmt.where(ReglaAsientoAutomatico.evento == evento)
    return list(db.scalars(stmt))


def crear_regla(db: Session, **campos) -> ReglaAsientoAutomatico:
    r = ReglaAsientoAutomatico(**campos)
    db.add(r)
    db.flush()
    return r
