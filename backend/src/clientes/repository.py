"""Acceso a datos del módulo `clientes`."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from clientes.models import (
    Cliente,
    ConsentimientoDatos,
    Cupon,
    Descuento,
    HistorialNivelCliente,
    NivelFidelizacion,
    ReglaNivel,
)


# ------------------------------------------------------------------- cliente
def obtener(db: Session, cid: int, *, for_update: bool = False) -> Cliente | None:
    stmt = select(Cliente).where(Cliente.id == cid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def por_identificacion(db: Session, ident: str) -> Cliente | None:
    return db.scalars(select(Cliente).where(Cliente.identificacion == ident)).first()


def consumidor_final(db: Session) -> Cliente | None:
    return db.scalars(select(Cliente).where(Cliente.es_consumidor_final.is_(True))).first()


def siguiente_afiliado(db: Session) -> str:
    n = db.scalar(select(func.nextval("cliente_afiliado_seq")))
    return f"AF-{int(n):06d}"


def crear(db: Session, **campos) -> Cliente:
    c = Cliente(**campos)
    db.add(c)
    db.flush()
    return c


def agregar_consentimiento(db: Session, *, cliente_id: int, aceptado: bool, version_texto: int) -> ConsentimientoDatos:
    cd = ConsentimientoDatos(cliente_id=cliente_id, aceptado=aceptado, version_texto=version_texto)
    db.add(cd)
    db.flush()
    return cd


def consentimiento_vigente(db: Session, cliente_id: int) -> ConsentimientoDatos | None:
    return db.scalars(
        select(ConsentimientoDatos)
        .where(ConsentimientoDatos.cliente_id == cliente_id)
        .order_by(ConsentimientoDatos.fecha.desc(), ConsentimientoDatos.id.desc())
    ).first()


def buscar(
    db: Session, *, q: str | None, nivel_id: int | None, solo_activos: bool,
    incluir_consumidor_final: bool, offset: int, limit: int,
) -> tuple[list[Cliente], int]:
    stmt = select(Cliente)
    if not incluir_consumidor_final:
        stmt = stmt.where(Cliente.es_consumidor_final.is_(False))
    if solo_activos:
        stmt = stmt.where(Cliente.estado == "activo")
    if nivel_id:
        stmt = stmt.where(Cliente.nivel_fidelizacion_id == nivel_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Cliente.nombre.ilike(like),
                Cliente.identificacion.ilike(like),
                Cliente.numero_afiliado.ilike(like),
                Cliente.email.ilike(like),
                Cliente.telefono.ilike(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Cliente.nombre).offset(offset).limit(limit)))
    return filas, int(total)


def todos_activos(db: Session) -> list[Cliente]:
    return list(
        db.scalars(
            select(Cliente).where(
                Cliente.estado == "activo", Cliente.es_consumidor_final.is_(False)
            )
        )
    )


# ------------------------------------------------------------- niveles
def nivel(db: Session, nid: int) -> NivelFidelizacion | None:
    return db.get(NivelFidelizacion, nid)


def nivel_base(db: Session) -> NivelFidelizacion | None:
    return db.scalars(select(NivelFidelizacion).where(NivelFidelizacion.es_base.is_(True))).first()


def niveles(db: Session, *, solo_activos: bool = True) -> list[NivelFidelizacion]:
    stmt = select(NivelFidelizacion).order_by(NivelFidelizacion.orden)
    if solo_activos:
        stmt = stmt.where(NivelFidelizacion.activo.is_(True))
    return list(db.scalars(stmt))


def crear_nivel(db: Session, **campos) -> NivelFidelizacion:
    n = NivelFidelizacion(**campos)
    db.add(n)
    db.flush()
    return n


def por_nombre_nivel(db: Session, nombre: str) -> NivelFidelizacion | None:
    return db.scalars(
        select(NivelFidelizacion).where(func.lower(NivelFidelizacion.nombre) == nombre.strip().lower())
    ).first()


def regla_vigente(db: Session, nivel_id: int, en_fecha: date | None = None) -> ReglaNivel | None:
    stmt = select(ReglaNivel).where(ReglaNivel.nivel_fidelizacion_id == nivel_id)
    if en_fecha is not None:
        stmt = stmt.where(ReglaNivel.vigente_desde <= en_fecha)
    return db.scalars(
        stmt.order_by(ReglaNivel.vigente_desde.desc(), ReglaNivel.id.desc())
    ).first()


def agregar_regla(db: Session, **campos) -> ReglaNivel:
    r = ReglaNivel(**campos)
    db.add(r)
    db.flush()
    return r


def contar_clientes_por_nivel(db: Session) -> dict[int | None, int]:
    filas = db.execute(
        select(Cliente.nivel_fidelizacion_id, func.count(Cliente.id))
        .where(Cliente.es_consumidor_final.is_(False))
        .group_by(Cliente.nivel_fidelizacion_id)
    ).all()
    return {nid: int(n) for nid, n in filas}


# ------------------------------------------------------------- historial nivel
def registrar_cambio_nivel(db: Session, **campos) -> HistorialNivelCliente:
    h = HistorialNivelCliente(**campos)
    db.add(h)
    db.flush()
    return h


def historial_nivel(db: Session, cliente_id: int) -> list[HistorialNivelCliente]:
    return list(
        db.scalars(
            select(HistorialNivelCliente)
            .where(HistorialNivelCliente.cliente_id == cliente_id)
            .order_by(HistorialNivelCliente.fecha.desc())
        )
    )


# ------------------------------------------------------------- descuentos
def crear_descuento(db: Session, **campos) -> Descuento:
    d = Descuento(**campos)
    db.add(d)
    db.flush()
    return d


def obtener_descuento(db: Session, did: int) -> Descuento | None:
    return db.get(Descuento, did)


def listar_descuentos(db: Session) -> list[Descuento]:
    return list(db.scalars(select(Descuento).order_by(Descuento.creado_en.desc())))


def descuentos_vigentes_para(
    db: Session, *, nivel_id: int | None, cliente_id: int | None, hoy: date,
) -> list[Descuento]:
    stmt = select(Descuento).where(Descuento.estado == "activo")
    filas = list(db.scalars(stmt))
    out: list[Descuento] = []
    for d in filas:
        if d.vigencia_inicio and hoy < d.vigencia_inicio:
            continue
        if d.vigencia_fin and hoy > d.vigencia_fin:
            continue
        if d.segmento == "nivel" and str(nivel_id) != str(d.segmento_ref):
            continue
        if d.segmento == "cliente" and str(cliente_id) != str(d.segmento_ref):
            continue
        out.append(d)
    return out


# ------------------------------------------------------------- cupones
def crear_cupon(db: Session, **campos) -> Cupon:
    c = Cupon(**campos)
    db.add(c)
    db.flush()
    return c


def cupon_por_codigo(db: Session, codigo: str, *, for_update: bool = False) -> Cupon | None:
    stmt = select(Cupon).where(Cupon.codigo == codigo)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def listar_cupones(db: Session, *, cliente_id: int | None, estado: str | None) -> list[Cupon]:
    stmt = select(Cupon).order_by(Cupon.creado_en.desc())
    if cliente_id:
        stmt = stmt.where(Cupon.cliente_id == cliente_id)
    if estado:
        stmt = stmt.where(Cupon.estado == estado)
    return list(db.scalars(stmt))


def cupones_activos_de(db: Session, cliente_id: int) -> list[Cupon]:
    return list(
        db.scalars(
            select(Cupon).where(Cupon.cliente_id == cliente_id, Cupon.estado == "activo")
        )
    )
