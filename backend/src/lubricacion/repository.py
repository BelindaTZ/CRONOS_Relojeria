"""Acceso a datos del módulo `lubricacion`."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lubricacion.models import FichaLubricacionCalibre, ProductoMoebius, PuntoLubricacion


# ------------------------------------------------------------ productos moebius
def listar_productos(db: Session, *, solo_activos: bool = False) -> list[ProductoMoebius]:
    stmt = select(ProductoMoebius).order_by(ProductoMoebius.codigo)
    if solo_activos:
        stmt = stmt.where(ProductoMoebius.activo.is_(True))
    return list(db.scalars(stmt))


def producto_por_codigo(db: Session, codigo: str) -> ProductoMoebius | None:
    return db.scalars(
        select(ProductoMoebius).where(func.lower(ProductoMoebius.codigo) == codigo.strip().lower())
    ).first()


def producto(db: Session, pid: int) -> ProductoMoebius | None:
    return db.get(ProductoMoebius, pid)


def crear_producto(db: Session, **campos) -> ProductoMoebius:
    p = ProductoMoebius(**campos)
    db.add(p)
    db.flush()
    return p


# ------------------------------------------------------------ fichas
def ficha_por_calibre(db: Session, calibre_id: int) -> FichaLubricacionCalibre | None:
    return db.scalars(
        select(FichaLubricacionCalibre).where(FichaLubricacionCalibre.calibre_id == calibre_id)
    ).first()


def crear_ficha(db: Session, **campos) -> FichaLubricacionCalibre:
    f = FichaLubricacionCalibre(**campos)
    db.add(f)
    db.flush()
    return f


def borrar_puntos(db: Session, ficha_id: int) -> None:
    db.query(PuntoLubricacion).filter_by(ficha_lubricacion_calibre_id=ficha_id).delete()
    db.flush()


def agregar_punto(db: Session, **campos) -> PuntoLubricacion:
    p = PuntoLubricacion(**campos)
    db.add(p)
    db.flush()
    return p


def punto(db: Session, punto_id: int) -> PuntoLubricacion | None:
    return db.get(PuntoLubricacion, punto_id)
