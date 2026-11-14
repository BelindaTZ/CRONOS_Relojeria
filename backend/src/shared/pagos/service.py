"""Registro de pagos multimedios contra un documento facturable (feature 008).

Capacidad compartida: la introduce 008 (orden de trabajo) y la reutiliza 009
(venta). Un pago es **append-only**; el saldo de un documento es
`total − Σ montos_registrados`. Sin lógica de negocio propia (cheques protestados,
cuentas por cobrar…) — eso vive en 010.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.exceptions import NotFoundError, ValidationError
from shared.models import MedioPago
from shared.pagos.models import Pago

_CENT = Decimal("0.01")
_TIPOS = ("orden_trabajo", "venta")


@dataclass(frozen=True)
class PagoRegistrado:
    id: int
    documento_tipo: str
    documento_id: int
    medio_pago_id: int
    medio_pago_nombre: str | None
    monto: Decimal
    referencia: str | None


def _q(v) -> Decimal:
    return Decimal(str(v)).quantize(_CENT, rounding=ROUND_HALF_UP)


def registrar_pago(
    db: Session,
    *,
    documento_tipo: str,
    documento_id: int,
    medio_pago_id: int,
    monto: Decimal | float | str,
    referencia: str | None = None,
    actor: int | None = None,
) -> PagoRegistrado:
    if documento_tipo not in _TIPOS:
        raise ValidationError(f"documento_tipo inválido: {documento_tipo}", field="documento_tipo")
    monto = _q(monto)
    if monto <= 0:
        raise ValidationError("El monto del pago debe ser mayor que cero", field="monto")
    medio = db.get(MedioPago, medio_pago_id)
    if medio is None or not getattr(medio, "activo", True):
        raise ValidationError("Medio de pago inválido o inactivo", field="medio_pago_id")

    p = Pago(
        documento_tipo=documento_tipo, documento_id=documento_id, medio_pago_id=medio_pago_id,
        monto=monto, referencia=(referencia or "").strip() or None, creado_por=actor,
    )
    db.add(p)
    db.flush()
    return PagoRegistrado(
        id=p.id, documento_tipo=documento_tipo, documento_id=documento_id,
        medio_pago_id=medio_pago_id, medio_pago_nombre=getattr(medio, "nombre", None),
        monto=monto, referencia=p.referencia,
    )


def pagado(db: Session, *, documento_tipo: str, documento_id: int) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(Pago.monto), 0)).where(
            Pago.documento_tipo == documento_tipo, Pago.documento_id == documento_id
        )
    )
    return _q(total or 0)


def saldo(db: Session, *, documento_tipo: str, documento_id: int, total: Decimal | float | str) -> Decimal:
    return _q(_q(total) - pagado(db, documento_tipo=documento_tipo, documento_id=documento_id))


def pagos_de(db: Session, *, documento_tipo: str, documento_id: int) -> list[PagoRegistrado]:
    filas = db.scalars(
        select(Pago).where(
            Pago.documento_tipo == documento_tipo, Pago.documento_id == documento_id
        ).order_by(Pago.creado_en, Pago.id)
    )
    salida: list[PagoRegistrado] = []
    for p in filas:
        medio = db.get(MedioPago, p.medio_pago_id)
        salida.append(PagoRegistrado(
            id=p.id, documento_tipo=p.documento_tipo, documento_id=p.documento_id,
            medio_pago_id=p.medio_pago_id, medio_pago_nombre=getattr(medio, "nombre", None),
            monto=_q(p.monto), referencia=p.referencia,
        ))
    return salida
