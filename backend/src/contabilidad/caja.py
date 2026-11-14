"""Caja y bancos por sucursal (feature 010, research D3).

Una `caja` por sucursal; `sesion_caja` = apertura → movimientos → cierre con
arqueo (`efectivo_contado` vs. `efectivo_esperado`, `diferencia`). Un movimiento
solo se registra sobre la sesión **abierta** de la caja (`SELECT ... FOR UPDATE`);
no hay "fecha de sesión cerrada" separada del estado — cerrada la sesión, los
movimientos posteriores abren una nueva (ACC013).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from contabilidad import repository
from contabilidad.schemas import MovimientoCajaOut, SesionCajaOut
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser

_CENT = Decimal("0.01")


def _q(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _caja_de(db: Session, sucursal_id: int):
    from shared.models import Sucursal

    if db.get(Sucursal, sucursal_id) is None:
        raise ValidationError("Sucursal inexistente", field="sucursal_id")
    c = repository.caja_de_sucursal(db, sucursal_id)
    if c is None:
        c = repository.crear_caja(db, sucursal_id=sucursal_id)
    return c


def _medio_nombre(db: Session, mid: int | None) -> str | None:
    if mid is None:
        return None
    from shared.models import MedioPago

    m = db.get(MedioPago, mid)
    return m.nombre if m else None


def _mov_out(db: Session, m) -> MovimientoCajaOut:
    return MovimientoCajaOut(
        id=m.id, tipo=m.tipo, monto=_q(m.monto), medio_pago=_medio_nombre(db, m.medio_pago_id),
        documento_tipo=m.documento_tipo, documento_id=m.documento_id, nota=m.nota, creado_en=m.creado_en,
    )


def _sesion_out(db: Session, s, *, sucursal_id: int, sucursal_nombre: str | None) -> SesionCajaOut:
    return SesionCajaOut(
        id=s.id, sucursal_id=sucursal_id, sucursal_nombre=sucursal_nombre, saldo_inicial=_q(s.saldo_inicial),
        abierta_en=s.abierta_en, estado=s.estado,
        efectivo_contado=_q(s.efectivo_contado) if s.efectivo_contado is not None else None,
        efectivo_esperado=_q(s.efectivo_esperado) if s.efectivo_esperado is not None else None,
        diferencia=_q(s.diferencia) if s.diferencia is not None else None,
        cerrada_en=s.cerrada_en,
        movimientos=[_mov_out(db, m) for m in repository.movimientos_de_sesion(db, s.id)],
    )


def abrir_sesion(db: Session, sucursal_id: int, *, saldo_inicial: Decimal, user: CurrentUser) -> SesionCajaOut:
    from shared.models import Sucursal

    caja = _caja_de(db, sucursal_id)
    if repository.sesion_abierta(db, caja.id) is not None:
        raise ConflictError("Ya hay una sesión de caja abierta para esta sucursal")
    s = repository.crear_sesion(db, caja_id=caja.id, abierta_por=user.id, saldo_inicial=_q(saldo_inicial), estado="abierta")
    registrar_cambio(db, actor=user.id, accion="crear", entidad="sesion_caja", entidad_id=s.id,
                     despues={"sucursal_id": sucursal_id, "saldo_inicial": str(saldo_inicial)})
    suc = db.get(Sucursal, sucursal_id)
    return _sesion_out(db, s, sucursal_id=sucursal_id, sucursal_nombre=suc.nombre if suc else None)


def registrar_movimiento(db: Session, sucursal_id: int, datos, *, user: CurrentUser) -> MovimientoCajaOut:
    caja = _caja_de(db, sucursal_id)
    sesion = repository.sesion_abierta(db, caja.id, for_update=True)
    if sesion is None:
        raise ConflictError("No hay una sesión de caja abierta para esta sucursal; ábrela primero")

    medio_id = None
    if datos.medio_pago:
        from shared.models import MedioPago

        medio = db.query(MedioPago).filter_by(clave=datos.medio_pago.strip()).first()
        if medio is None:
            raise ValidationError(f"Medio de pago desconocido: {datos.medio_pago}", field="medio_pago")
        medio_id = medio.id

    m = repository.agregar_movimiento_caja(
        db, sesion_caja_id=sesion.id, tipo=datos.tipo, monto=_q(datos.monto), medio_pago_id=medio_id,
        documento_tipo=datos.documento_tipo, documento_id=datos.documento_id,
        nota=(datos.nota or "").strip() or None, creado_por=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="crear", entidad="movimiento_caja", entidad_id=m.id,
                     despues={"tipo": m.tipo, "monto": str(datos.monto)})
    return _mov_out(db, m)


def cerrar_sesion(db: Session, sucursal_id: int, datos, *, user: CurrentUser) -> SesionCajaOut:
    from shared.models import Sucursal

    caja = _caja_de(db, sucursal_id)
    sesion = repository.sesion_abierta(db, caja.id, for_update=True)
    if sesion is None:
        raise ConflictError("No hay una sesión de caja abierta para cerrar")

    movs = repository.movimientos_de_sesion(db, sesion.id)
    entradas = sum((_q(m.monto) for m in movs if m.tipo == "entrada"), Decimal("0"))
    salidas = sum((_q(m.monto) for m in movs if m.tipo == "salida"), Decimal("0"))
    esperado = _q(sesion.saldo_inicial) + entradas - salidas

    sesion.efectivo_contado = _q(datos.efectivo_contado)
    sesion.efectivo_esperado = esperado
    sesion.diferencia = _q(sesion.efectivo_contado - esperado)
    sesion.estado = "cerrada"
    sesion.cerrada_por = user.id
    sesion.cerrada_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="sesion_caja", entidad_id=sesion.id,
                     despues={"efectivo_contado": str(sesion.efectivo_contado), "diferencia": str(sesion.diferencia)})
    suc = db.get(Sucursal, sucursal_id)
    return _sesion_out(db, sesion, sucursal_id=sucursal_id, sucursal_nombre=suc.nombre if suc else None)


def sesion_actual(db: Session, sucursal_id: int) -> SesionCajaOut | None:
    from shared.models import Sucursal

    caja = repository.caja_de_sucursal(db, sucursal_id)
    if caja is None:
        return None
    sesion = repository.sesion_abierta(db, caja.id)
    if sesion is None:
        return None
    suc = db.get(Sucursal, sucursal_id)
    return _sesion_out(db, sesion, sucursal_id=sucursal_id, sucursal_nombre=suc.nombre if suc else None)
