"""API pública del módulo `proveedores` para otros módulos de negocio (Principio X).

Solo lecturas puntuales que necesita Inventario (003): datos de una línea de
recepción de compra para heredar en la ficha de un reloj, y el listado de líneas
recibidas de un tipo de ítem. El registro del receptor de recepción → inventario
lo cablea `main.py` (infra) vía `service.registrar_receptor_inventario`.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from proveedores.models import LineaOrdenCompra, OrdenCompra, Proveedor, RecepcionCompra, RecepcionLinea


def proveedor_nombre(db: Session, proveedor_id: int) -> str | None:
    """Público (010): razón social de un proveedor, para el subledger de CxP."""
    p = db.get(Proveedor, proveedor_id)
    return p.razon_social if p else None


@dataclass(frozen=True)
class LineaCompraInfo:
    linea_id: int
    orden_compra_id: int
    proveedor_id: int
    sucursal_destino_id: int
    item_tipo: str
    item_ref: str
    descripcion: str | None
    costo_unitario: float
    recibidas: int
    marca: str | None = None
    calibre_codigo: str | None = None
    anio: int | None = None
    numero_serie: str | None = None


def _recibidas_por_linea(db: Session, linea_ids: list[int]) -> dict[int, int]:
    if not linea_ids:
        return {}
    filas = db.execute(
        select(RecepcionLinea.linea_orden_compra_id, func.sum(RecepcionLinea.cantidad_recibida))
        .where(RecepcionLinea.linea_orden_compra_id.in_(linea_ids))
        .group_by(RecepcionLinea.linea_orden_compra_id)
    ).all()
    return {lid: int(total or 0) for lid, total in filas}


def linea_compra_info(db: Session, linea_id: int) -> LineaCompraInfo | None:
    row = db.execute(
        select(LineaOrdenCompra, OrdenCompra)
        .join(OrdenCompra, OrdenCompra.id == LineaOrdenCompra.orden_compra_id)
        .where(LineaOrdenCompra.id == linea_id)
    ).first()
    if row is None:
        return None
    linea, orden = row
    recibidas = _recibidas_por_linea(db, [linea.id]).get(linea.id, 0)
    costo_real = db.scalar(
        select(RecepcionLinea.costo_unitario)
        .where(RecepcionLinea.linea_orden_compra_id == linea.id, RecepcionLinea.costo_unitario.isnot(None))
        .order_by(RecepcionLinea.id.desc())
        .limit(1)
    )
    return LineaCompraInfo(
        linea_id=linea.id,
        orden_compra_id=orden.id,
        proveedor_id=orden.proveedor_id,
        sucursal_destino_id=orden.sucursal_destino_id,
        item_tipo=linea.item_tipo,
        item_ref=linea.item_ref,
        descripcion=linea.descripcion,
        costo_unitario=float(costo_real if costo_real is not None else (linea.costo_unitario or 0)),
        recibidas=recibidas,
        marca=linea.marca,
        numero_serie=linea.numero_serie,
        calibre_codigo=linea.calibre_codigo,
        anio=linea.anio,
    )


def lineas_compra_recibidas(db: Session, *, item_tipo: str) -> list[LineaCompraInfo]:
    """Líneas de compra de `item_tipo` con al menos una recepción registrada."""
    filas = db.execute(
        select(LineaOrdenCompra, OrdenCompra)
        .join(OrdenCompra, OrdenCompra.id == LineaOrdenCompra.orden_compra_id)
        .join(RecepcionCompra, RecepcionCompra.orden_compra_id == OrdenCompra.id)
        .where(LineaOrdenCompra.item_tipo == item_tipo)
        .distinct()
    ).all()
    ids = [l.id for l, _ in filas]
    recibidas = _recibidas_por_linea(db, ids)
    salida = []
    for linea, orden in filas:
        salida.append(
            LineaCompraInfo(
                linea_id=linea.id,
                orden_compra_id=orden.id,
                proveedor_id=orden.proveedor_id,
                sucursal_destino_id=orden.sucursal_destino_id,
                item_tipo=linea.item_tipo,
                item_ref=linea.item_ref,
                descripcion=linea.descripcion,
                costo_unitario=float(linea.costo_unitario or 0),
                recibidas=recibidas.get(linea.id, 0),
                marca=linea.marca,
                numero_serie=linea.numero_serie,
                calibre_codigo=linea.calibre_codigo,
                anio=linea.anio,
            )
        )
    return salida
