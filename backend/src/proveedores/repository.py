from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from proveedores.models import (
    CalificacionProveedor,
    CompraProgramada,
    LineaOrdenCompra,
    OrdenCompra,
    Proveedor,
    ProveedorDocumento,
    ProveedorTipo,
    RecepcionCompra,
    RecepcionLinea,
)


# ------------------------------------------------------------------ proveedor
def obtener(db: Session, pid: int) -> Proveedor | None:
    return db.get(Proveedor, pid)


def por_ruc(db: Session, ruc: str) -> Proveedor | None:
    return db.scalars(select(Proveedor).where(Proveedor.ruc_nit == ruc)).first()


def buscar(
    db: Session, *, q: str | None, tipo: str | None, estado: str | None, offset: int, limit: int
) -> tuple[list[Proveedor], int]:
    filtros = []
    if q:
        like = f"%{q}%"
        filtros.append(
            or_(
                Proveedor.razon_social.ilike(like),
                Proveedor.nombre_comercial.ilike(like),
                Proveedor.ruc_nit.ilike(like),
                Proveedor.email.ilike(like),
                Proveedor.telefono.ilike(like),
            )
        )
    if estado:
        filtros.append(Proveedor.estado == estado)
    stmt = select(Proveedor).where(*filtros)
    if tipo:
        stmt = stmt.where(
            Proveedor.id.in_(select(ProveedorTipo.proveedor_id).where(ProveedorTipo.tipo == tipo))
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Proveedor.razon_social).offset(offset).limit(limit)))
    return filas, int(total)


def set_tipos(db: Session, proveedor_id: int, tipos: list[str]) -> None:
    from sqlalchemy import delete

    db.execute(delete(ProveedorTipo).where(ProveedorTipo.proveedor_id == proveedor_id))
    db.add_all(ProveedorTipo(proveedor_id=proveedor_id, tipo=t) for t in dict.fromkeys(tipos))
    db.flush()


def tipos_de(db: Session, proveedor_id: int) -> list[str]:
    return list(
        db.scalars(select(ProveedorTipo.tipo).where(ProveedorTipo.proveedor_id == proveedor_id))
    )


def agregar_documento(db: Session, **campos) -> ProveedorDocumento:
    d = ProveedorDocumento(**campos)
    db.add(d)
    db.flush()
    return d


def documentos_de(db: Session, proveedor_id: int) -> list[ProveedorDocumento]:
    return list(
        db.scalars(
            select(ProveedorDocumento)
            .where(ProveedorDocumento.proveedor_id == proveedor_id)
            .order_by(ProveedorDocumento.creado_en.desc())
        )
    )


# ------------------------------------------------------------------ calificación
def calificacion_vigente(db: Session, proveedor_id: int) -> CalificacionProveedor | None:
    return db.scalars(
        select(CalificacionProveedor)
        .where(CalificacionProveedor.proveedor_id == proveedor_id)
        .order_by(CalificacionProveedor.creado_en.desc())
    ).first()


def agregar_calificacion(db: Session, **campos) -> CalificacionProveedor:
    c = CalificacionProveedor(**campos)
    db.add(c)
    db.flush()
    return c


# ------------------------------------------------------------------ órdenes
def obtener_orden(db: Session, oid: int) -> OrdenCompra | None:
    return db.get(OrdenCompra, oid)


def crear_orden(db: Session, **campos) -> OrdenCompra:
    o = OrdenCompra(**campos)
    db.add(o)
    db.flush()
    return o


def buscar_ordenes(
    db: Session, *, proveedor_id: int | None, tipo: str | None, estado: str | None, offset: int, limit: int
) -> tuple[list[OrdenCompra], int]:
    filtros = []
    if proveedor_id:
        filtros.append(OrdenCompra.proveedor_id == proveedor_id)
    if tipo:
        filtros.append(OrdenCompra.tipo == tipo)
    if estado:
        filtros.append(OrdenCompra.estado == estado)
    stmt = select(OrdenCompra).where(*filtros)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(OrdenCompra.creado_en.desc()).offset(offset).limit(limit)))
    return filas, int(total)


def ordenes_de_proveedor(db: Session, proveedor_id: int) -> list[OrdenCompra]:
    return list(
        db.scalars(
            select(OrdenCompra)
            .where(OrdenCompra.proveedor_id == proveedor_id)
            .order_by(OrdenCompra.creado_en.desc())
        )
    )


def recibido_por_linea(db: Session, orden_id: int) -> dict[int, int]:
    filas = db.execute(
        select(RecepcionLinea.linea_orden_compra_id, func.sum(RecepcionLinea.cantidad_recibida))
        .join(RecepcionCompra, RecepcionCompra.id == RecepcionLinea.recepcion_compra_id)
        .where(RecepcionCompra.orden_compra_id == orden_id)
        .group_by(RecepcionLinea.linea_orden_compra_id)
    ).all()
    return {lid: int(total or 0) for lid, total in filas}


def costo_real_por_linea(db: Session, orden_id: int) -> dict[int, float]:
    """Último costo unitario real informado en una recepción, por línea."""
    filas = db.execute(
        select(RecepcionLinea.linea_orden_compra_id, RecepcionLinea.costo_unitario, RecepcionLinea.id)
        .join(RecepcionCompra, RecepcionCompra.id == RecepcionLinea.recepcion_compra_id)
        .where(RecepcionCompra.orden_compra_id == orden_id, RecepcionLinea.costo_unitario.isnot(None))
        .order_by(RecepcionLinea.id)
    ).all()
    out: dict[int, float] = {}
    for lid, costo, _ in filas:
        out[lid] = float(costo)
    return out


def marcas_autorizadas_de(db: Session, proveedor_id: int) -> list[int]:
    from proveedores.models import ProveedorMarcaAutorizada

    return list(
        db.scalars(
            select(ProveedorMarcaAutorizada.marca_id).where(
                ProveedorMarcaAutorizada.proveedor_id == proveedor_id
            )
        )
    )


def set_marcas_autorizadas(db: Session, proveedor_id: int, marca_ids: list[int]) -> None:
    from sqlalchemy import delete

    from proveedores.models import ProveedorMarcaAutorizada

    db.execute(delete(ProveedorMarcaAutorizada).where(ProveedorMarcaAutorizada.proveedor_id == proveedor_id))
    db.add_all(
        ProveedorMarcaAutorizada(proveedor_id=proveedor_id, marca_id=m) for m in dict.fromkeys(marca_ids)
    )
    db.flush()


def nombres_marca(db: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    from shared.models import MarcaReloj

    return {i: n for i, n in db.execute(select(MarcaReloj.id, MarcaReloj.nombre).where(MarcaReloj.id.in_(ids))).all()}


def crear_recepcion(db: Session, **campos) -> RecepcionCompra:
    r = RecepcionCompra(**campos)
    db.add(r)
    db.flush()
    return r


def ultima_factura(db: Session, orden_id: int) -> dict:
    row = db.execute(
        select(RecepcionCompra.numero_factura, RecepcionCompra.numero_guia)
        .where(RecepcionCompra.orden_compra_id == orden_id)
        .order_by(RecepcionCompra.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return {}
    return {"numero_factura": row[0], "numero_guia": row[1]}


def ultimo_precio_item(
    db: Session, *, item_tipo: str, marca: str | None = None, referencia: str | None = None,
    pieza_id: int | None = None,
) -> dict | None:
    """Último costo pagado por un ítem: primero la recepción real, si no el estimado de la orden."""
    filtros = [LineaOrdenCompra.item_tipo == item_tipo]
    if item_tipo == "reloj":
        if marca:
            filtros.append(func.lower(LineaOrdenCompra.marca) == marca.strip().lower())
        if referencia:
            filtros.append(func.lower(LineaOrdenCompra.item_ref) == referencia.strip().lower())
    else:
        if pieza_id:
            filtros.append(LineaOrdenCompra.pieza_id == pieza_id)
        elif referencia:
            filtros.append(func.lower(LineaOrdenCompra.item_ref) == referencia.strip().lower())

    real = db.execute(
        select(RecepcionLinea.costo_unitario, RecepcionCompra.fecha_real)
        .join(RecepcionCompra, RecepcionCompra.id == RecepcionLinea.recepcion_compra_id)
        .join(LineaOrdenCompra, LineaOrdenCompra.id == RecepcionLinea.linea_orden_compra_id)
        .where(RecepcionLinea.costo_unitario.isnot(None), *filtros)
        .order_by(RecepcionLinea.id.desc())
        .limit(1)
    ).first()
    if real:
        return {"costo": float(real[0]), "fecha": real[1], "fuente": "recepcion"}

    est = db.execute(
        select(LineaOrdenCompra.costo_unitario, OrdenCompra.creado_en)
        .join(OrdenCompra, OrdenCompra.id == LineaOrdenCompra.orden_compra_id)
        .where(LineaOrdenCompra.costo_unitario.isnot(None), *filtros)
        .order_by(LineaOrdenCompra.id.desc())
        .limit(1)
    ).first()
    if est:
        return {"costo": float(est[0]), "fecha": est[1].date() if est[1] else None, "fuente": "orden"}
    return None


def desfases_recientes(db: Session, proveedor_id: int, n: int) -> list[int]:
    filas = db.scalars(
        select(RecepcionCompra.desfase_dias)
        .join(OrdenCompra, OrdenCompra.id == RecepcionCompra.orden_compra_id)
        .where(OrdenCompra.proveedor_id == proveedor_id, RecepcionCompra.desfase_dias.is_not(None))
        .order_by(RecepcionCompra.creado_en.desc())
        .limit(n)
    )
    return [int(x) for x in filas]


# ------------------------------------------------------------------ programadas
def obtener_programada(db: Session, pid: int) -> CompraProgramada | None:
    return db.get(CompraProgramada, pid)


def crear_programada(db: Session, **campos) -> CompraProgramada:
    p = CompraProgramada(**campos)
    db.add(p)
    db.flush()
    return p


def listar_programadas(db: Session) -> list[CompraProgramada]:
    return list(db.scalars(select(CompraProgramada).order_by(CompraProgramada.id.desc())))


def programadas_vencidas(db: Session) -> list[CompraProgramada]:
    return list(
        db.scalars(
            select(CompraProgramada).where(
                CompraProgramada.estado == "activa",
                CompraProgramada.proxima_generacion <= datetime.now(timezone.utc),
            )
        )
    )
