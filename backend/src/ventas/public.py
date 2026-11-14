"""API pública de `ventas` consumida por 010 (contabilidad — subledger de CxC).

`ventas` genera la obligación (`cuenta_por_cobrar`); 010 construye el aging y
registra los cobros. Estas funciones son el único punto de contacto.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ventas import repository
from ventas.models import CuentaPorCobrar

_CENT = Decimal("0.01")


def _cxc_dict(c) -> dict:
    return {
        "id": c.id, "origen_tipo": c.origen_tipo, "origen_id": c.origen_id,
        "cliente_id": c.cliente_id, "monto_original": Decimal(str(c.monto_original)),
        "saldo": Decimal(str(c.saldo)), "estado": c.estado, "creado_en": c.creado_en,
    }


def cuentas_por_cobrar_abiertas(db: Session, *, cliente_id: int | None = None) -> list[dict]:
    filas = repository.listar_cxc(db, cliente_id=cliente_id, estado="pendiente")
    return [_cxc_dict(c) for c in filas]


def listar_cuentas_por_cobrar(db: Session, *, cliente_id: int | None = None, estado: str | None = None) -> list[dict]:
    """Público (010): todas las CxC (cualquier estado) para el subledger y el aging."""
    return [_cxc_dict(c) for c in repository.listar_cxc(db, cliente_id=cliente_id, estado=estado)]


def resumen_periodo(db: Session, *, sucursal_id: int, desde, hasta) -> dict:
    """Público (010): ingresos y costos de las ventas confirmadas de una sucursal en
    un rango de fechas, para la rentabilidad neta por sucursal (versión operativa)."""
    from datetime import datetime as _dt

    from ventas.models import OrdenVenta

    ini = _dt(desde.year, desde.month, desde.day)
    fin = _dt(hasta.year, hasta.month, hasta.day, 23, 59, 59)
    from sqlalchemy import select as _select

    filas = db.scalars(
        _select(OrdenVenta).where(
            OrdenVenta.sucursal_id == sucursal_id, OrdenVenta.estado == "confirmada",
            OrdenVenta.fecha >= ini, OrdenVenta.fecha <= fin,
        )
    )
    ingresos = Decimal("0")
    costos = Decimal("0")
    for v in filas:
        # ingreso neto de IVA (el IVA no es ingreso del negocio); costo = base neta − margen
        base = Decimal(str(v.subtotal_sin_impuestos)) if v.subtotal_sin_impuestos is not None else Decimal(str(v.total or 0))
        margen = Decimal(str(v.margen_venta)) if v.margen_venta is not None else Decimal("0")
        ingresos += base
        costos += (base - margen)
    return {"ingresos": ingresos.quantize(_CENT), "costos": costos.quantize(_CENT)}


def propietario_de_reloj(db: Session, reloj_id: int) -> dict | None:
    """Público (008): cliente dueño de un reloj — la venta CONFIRMADA más reciente
    que lo incluye (una unidad anulada y revendida podría tener más de una línea de
    venta histórica; nos quedamos con la vigente). `None` si nunca se vendió aquí
    (unidad de alta manual sin venta registrada — la ruta de excepción de `crear_ot`)."""
    from ventas.models import LineaVenta, OrdenVenta

    v = db.scalars(
        select(OrdenVenta)
        .join(LineaVenta, LineaVenta.orden_venta_id == OrdenVenta.id)
        .where(LineaVenta.reloj_id == reloj_id, OrdenVenta.estado == "confirmada")
        .order_by(OrdenVenta.fecha.desc())
        .limit(1)
    ).first()
    return {"cliente_id": v.cliente_id} if v else None


def crear_cxc_externa(
    db: Session, *, origen_tipo: str, origen_id: int, cliente_id: int, monto: Decimal | float | str,
) -> dict:
    """Público (008): registra una CxC que no nace de una venta (entrega de una OT a
    crédito, autorizada por Gerencia General). `origen_tipo` debe ser `orden_trabajo`."""
    monto = Decimal(str(monto)).quantize(_CENT)
    c = repository.crear_cxc(
        db, origen_tipo=origen_tipo, origen_id=origen_id, cliente_id=cliente_id,
        monto_original=monto, saldo=monto, estado="pendiente",
    )
    return _cxc_dict(c)


def marcar_cxc_saldada(db: Session, cxc_id: int, *, monto: Decimal | None = None) -> bool:
    """010 la llama al aplicar un cobro. `monto` None = saldar por completo."""
    c = db.get(CuentaPorCobrar, cxc_id)
    if c is None or c.estado != "pendiente":
        return False
    if monto is None or Decimal(str(monto)) >= Decimal(str(c.saldo)):
        c.saldo = Decimal("0")
        c.estado = "saldada"
    else:
        c.saldo = (Decimal(str(c.saldo)) - Decimal(str(monto))).quantize(_CENT)
    db.flush()
    return True
