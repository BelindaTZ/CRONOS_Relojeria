"""Acceso a datos del módulo `inventario`."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from inventario.models import AlertaStock, Calibre, DocumentoReloj, EventoSerie, FotoReloj, Reloj


# ------------------------------------------------------------------- calibre
def listar_calibres(db: Session, *, q: str | None = None) -> list[tuple[Calibre, int]]:
    conteo = (
        select(Reloj.calibre_id, func.count(Reloj.id).label("n"))
        .group_by(Reloj.calibre_id)
        .subquery()
    )
    stmt = (
        select(Calibre, func.coalesce(conteo.c.n, 0))
        .outerjoin(conteo, conteo.c.calibre_id == Calibre.id)
        .order_by(Calibre.codigo)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Calibre.codigo.ilike(like), Calibre.marca.ilike(like)))
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def calibre_por_codigo(db: Session, codigo: str) -> Calibre | None:
    return db.scalars(select(Calibre).where(Calibre.codigo == codigo)).first()


def calibre_por_id(db: Session, cid: int) -> Calibre | None:
    return db.get(Calibre, cid)


def crear_calibre(db: Session, *, codigo: str, marca: str | None, descripcion: str | None) -> Calibre:
    c = Calibre(codigo=codigo, marca=marca, descripcion=descripcion)
    db.add(c)
    db.flush()
    return c


# --------------------------------------------------------------------- reloj
def buscar_relojes(
    db: Session,
    *,
    q: str | None,
    marca: str | None,
    sucursal_id: int | None,
    disponibilidad: str | None,
    calibre: str | None,
    offset: int,
    limit: int,
    sucursales: list[int] | None = None,
    tipo_cristal: str | None = None,
) -> tuple[list[Reloj], int]:
    stmt = select(Reloj).outerjoin(Calibre, Calibre.id == Reloj.calibre_id)
    if sucursales is not None:
        stmt = stmt.where(Reloj.sucursal_actual_id.in_(sucursales))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Reloj.numero_serie.ilike(like),
                Reloj.marca.ilike(like),
                Reloj.referencia.ilike(like),
                Calibre.codigo.ilike(like),
            )
        )
    if marca:
        stmt = stmt.where(Reloj.marca.ilike(f"%{marca.strip()}%"))
    if sucursal_id:
        stmt = stmt.where(Reloj.sucursal_actual_id == sucursal_id)
    if disponibilidad:
        stmt = stmt.where(Reloj.disponibilidad == disponibilidad)
    if calibre:
        stmt = stmt.where(Calibre.codigo.ilike(f"%{calibre.strip()}%"))
    if tipo_cristal:
        stmt = stmt.where(Reloj.tipo_cristal.ilike(f"%{tipo_cristal.strip()}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(
        db.scalars(stmt.order_by(Reloj.creado_en.desc()).offset(offset).limit(limit))
    )
    return filas, total


def buscar_disponibilidad_global(
    db: Session, *, q: str | None, marca: str | None, calibre: str | None, tipo_cristal: str | None, limit: int = 50,
) -> list[tuple[Reloj, str]]:
    """Búsqueda de disponibilidad SIN scoping por sucursal (Esp. §4.1/§4.4: el
    vendedor "también debe poder consultar el inventario completo" para saber si
    un modelo que no tiene en su sucursal existe en otra — 004 lo deriva a
    traslado). Deliberadamente distinta de `buscar_relojes`, que sí respeta el
    scoping normal de 004 para el resto de pantallas de inventario."""
    from shared.models import Sucursal

    stmt = (
        select(Reloj, Sucursal.nombre)
        .join(Sucursal, Sucursal.id == Reloj.sucursal_actual_id)
        .outerjoin(Calibre, Calibre.id == Reloj.calibre_id)
        .where(Reloj.disponibilidad == "disponible")
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Reloj.numero_serie.ilike(like), Reloj.marca.ilike(like), Reloj.referencia.ilike(like))
        )
    if marca:
        stmt = stmt.where(Reloj.marca.ilike(f"%{marca.strip()}%"))
    if calibre:
        stmt = stmt.where(Calibre.codigo.ilike(f"%{calibre.strip()}%"))
    if tipo_cristal:
        stmt = stmt.where(Reloj.tipo_cristal.ilike(f"%{tipo_cristal.strip()}%"))
    return list(db.execute(stmt.order_by(Reloj.marca, Reloj.referencia).limit(limit)).all())


def buscar_relojes_elegibles_ot(db: Session, *, q: str | None, limit: int = 50) -> list[Reloj]:
    """Público (008): unidades que pueden entrar a una orden de trabajo — `vendido`
    (caso normal, con dueño real) o `disponible` (alta manual sin venta registrada
    todavía, ruta de excepción de `crear_ot`). Nunca `en_transito`/`en_servicio`
    (ya en otra OT)/`dado_de_baja`.

    Pensada para búsqueda en vivo (el frontend manda `q` en cada tecleo, no carga
    todo de una vez): con cientos de unidades, un `limit` bajo + filtro en el
    SERVIDOR es lo único que de verdad cubre "todas" — un límite alto sin filtro
    seguía dejando fuera unidades vendidas más allá del corte (bug encontrado
    2026-09-11: con 241 unidades elegibles y límite 200, una unidad vendida real
    quedaba invisible en el selector). `vendido` ordena antes que `disponible`
    (el caso normal es más frecuente que la excepción)."""
    stmt = select(Reloj).where(Reloj.disponibilidad.in_(("vendido", "disponible")))
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Reloj.numero_serie.ilike(like), Reloj.marca.ilike(like), Reloj.referencia.ilike(like))
        )
    return list(
        db.scalars(stmt.order_by(Reloj.disponibilidad.desc(), Reloj.marca, Reloj.referencia).limit(limit))
    )


def obtener_reloj(db: Session, rid: int) -> Reloj | None:
    return db.get(Reloj, rid)


def reloj_por_serie(db: Session, serie: str) -> Reloj | None:
    return db.scalars(select(Reloj).where(Reloj.numero_serie == serie)).first()


def codigos_calibre(db: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {
        cid: cod
        for cid, cod in db.execute(
            select(Calibre.id, Calibre.codigo).where(Calibre.id.in_(ids))
        ).all()
    }


def valor_inventario(
    db: Session, *, sucursal_id: int | None, sucursales: list[int] | None = None
) -> list[tuple[int | None, int, float, float]]:
    stmt = (
        select(
            Reloj.sucursal_actual_id,
            func.count(Reloj.id),
            func.coalesce(func.sum(Reloj.precio_venta), 0),
            func.coalesce(func.sum(Reloj.costo_adquisicion), 0),
        )
        .where(Reloj.disponibilidad.in_(("disponible", "reservado", "en_transito", "en_servicio")))
        .group_by(Reloj.sucursal_actual_id)
    )
    if sucursal_id:
        stmt = stmt.where(Reloj.sucursal_actual_id == sucursal_id)
    if sucursales is not None:
        stmt = stmt.where(Reloj.sucursal_actual_id.in_(sucursales))
    return [tuple(r) for r in db.execute(stmt).all()]


# --------------------------------------------------------------------- fotos / docs
def fotos_de(db: Session, reloj_id: int) -> list[FotoReloj]:
    return list(
        db.scalars(
            select(FotoReloj).where(FotoReloj.reloj_id == reloj_id).order_by(FotoReloj.orden, FotoReloj.id)
        )
    )


def agregar_foto(db: Session, *, reloj_id: int, objeto: str, orden: int) -> FotoReloj:
    f = FotoReloj(reloj_id=reloj_id, objeto=objeto, orden=orden)
    db.add(f)
    db.flush()
    return f


def agregar_documento(
    db: Session, *, reloj_id: int, objeto: str, tipo: str, nombre: str | None, subido_por: int | None
) -> DocumentoReloj:
    d = DocumentoReloj(reloj_id=reloj_id, objeto=objeto, tipo=tipo, nombre=nombre, subido_por=subido_por)
    db.add(d)
    db.flush()
    return d


def documentos_de(db: Session, reloj_id: int) -> list[DocumentoReloj]:
    return list(db.scalars(select(DocumentoReloj).where(DocumentoReloj.reloj_id == reloj_id)))


# --------------------------------------------------------------------- historial
def eventos_de_serie(db: Session, serie: str, *, reloj_id: int | None = None) -> list[EventoSerie]:
    """Historial de una unidad. Si se conoce el `reloj_id`, incluye TODOS sus
    eventos aunque el número de serie haya sido corregido (el historial es
    inalterable: los eventos previos conservan su serie anterior)."""
    cond = EventoSerie.numero_serie == serie
    if reloj_id is not None:
        cond = or_(cond, EventoSerie.reloj_id == reloj_id)
    return list(
        db.scalars(select(EventoSerie).where(cond).order_by(EventoSerie.fecha, EventoSerie.id))
    )


def registrar_evento(
    db: Session,
    *,
    numero_serie: str,
    reloj_id: int | None,
    tipo: str,
    documento_tipo: str | None = None,
    documento_id: int | None = None,
    detalle: dict | None = None,
    actor: int | None = None,
) -> EventoSerie:
    e = EventoSerie(
        numero_serie=numero_serie,
        reloj_id=reloj_id,
        tipo=tipo,
        documento_tipo=documento_tipo,
        documento_id=documento_id,
        detalle=detalle,
        actor_usuario_id=actor,
    )
    db.add(e)
    db.flush()
    return e


def relojes_por_recepcion_linea(db: Session, linea_id: int) -> int:
    return db.scalar(
        select(func.count(Reloj.id)).where(Reloj.recepcion_linea_id == linea_id)
    ) or 0


# --------------------------------------------------------------------- alertas
def alertas_abiertas(db: Session, *, tipo: str | None, sucursal_id: int | None) -> list[AlertaStock]:
    stmt = select(AlertaStock).where(AlertaStock.estado == "abierta")
    if tipo:
        stmt = stmt.where(AlertaStock.tipo == tipo)
    if sucursal_id:
        stmt = stmt.where(AlertaStock.sucursal_id == sucursal_id)
    return list(db.scalars(stmt.order_by(AlertaStock.creado_en.desc())))


def alerta_abierta(
    db: Session, *, ambito: str, ref: str, sucursal_id: int | None, tipo: str
) -> AlertaStock | None:
    return db.scalars(
        select(AlertaStock).where(
            AlertaStock.estado == "abierta",
            AlertaStock.ambito == ambito,
            AlertaStock.ref == ref,
            AlertaStock.sucursal_id.is_(sucursal_id) if sucursal_id is None else AlertaStock.sucursal_id == sucursal_id,
            AlertaStock.tipo == tipo,
        )
    ).first()


def abrir_alerta(
    db: Session, *, ambito: str, ref: str, sucursal_id: int | None, tipo: str, detalle: dict
) -> AlertaStock:
    a = AlertaStock(ambito=ambito, ref=ref, sucursal_id=sucursal_id, tipo=tipo, detalle=detalle)
    db.add(a)
    db.flush()
    return a


def resolver_alertas(
    db: Session, *, ambito: str, ref: str, sucursal_id: int | None, tipos: list[str]
) -> None:
    from datetime import datetime, timezone

    stmt = select(AlertaStock).where(
        AlertaStock.estado == "abierta",
        AlertaStock.ambito == ambito,
        AlertaStock.ref == ref,
        AlertaStock.tipo.in_(tipos),
    )
    if sucursal_id is not None:
        stmt = stmt.where(AlertaStock.sucursal_id == sucursal_id)
    for a in db.scalars(stmt):
        a.estado = "resuelta"
        a.resuelto_en = datetime.now(timezone.utc)
    db.flush()


def modelos_distintos(db: Session) -> list[tuple[str, str, int | None]]:
    """(marca, referencia, sucursal_actual_id) de relojes en stock activo."""
    return [
        tuple(r)
        for r in db.execute(
            select(Reloj.marca, Reloj.referencia, Reloj.sucursal_actual_id).where(
                Reloj.disponibilidad.in_(("disponible", "reservado"))
            )
        ).all()
    ]


def contar_modelo(db: Session, *, marca: str, referencia: str, sucursal_id: int | None) -> int:
    stmt = select(func.count(Reloj.id)).where(
        Reloj.marca == marca,
        Reloj.referencia == referencia,
        Reloj.disponibilidad.in_(("disponible", "reservado")),
    )
    if sucursal_id is not None:
        stmt = stmt.where(Reloj.sucursal_actual_id == sucursal_id)
    return db.scalar(stmt) or 0


def proveedor_habitual_modelo(db: Session, *, marca: str, referencia: str) -> int | None:
    return db.scalar(
        select(Reloj.proveedor_id)
        .where(Reloj.marca == marca, Reloj.referencia == referencia, Reloj.proveedor_id.isnot(None))
        .order_by(Reloj.creado_en.desc())
        .limit(1)
    )
