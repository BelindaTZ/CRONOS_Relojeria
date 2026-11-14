from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from lubricacion import service
from lubricacion.schemas import (
    DesviacionOut,
    FichaIn,
    FichaOut,
    ProductoMoebiusIn,
    ProductoMoebiusOut,
)
from shared.database import get_db
from shared.guard import CurrentUser, require_perm

router = APIRouter(tags=["lubricacion"])

_leer = require_perm("lubricacion", "consultar")
_crear = require_perm("lubricacion", "crear")
_editar = require_perm("lubricacion", "editar")


@router.get("/productos-moebius", response_model=list[ProductoMoebiusOut])
def listar_productos(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_productos(db)


@router.post("/productos-moebius", response_model=ProductoMoebiusOut, status_code=status.HTTP_201_CREATED)
def crear_producto(datos: ProductoMoebiusIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_producto(db, datos, user=user)


@router.get("/calibres/{calibre_id}/ficha-lubricacion", response_model=FichaOut)
def get_ficha(calibre_id: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.get_ficha(db, calibre_id)


@router.put("/calibres/{calibre_id}/ficha-lubricacion", response_model=FichaOut)
def set_ficha(calibre_id: int, datos: FichaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_ficha(db, calibre_id, datos, user=user)


@router.get("/reportes/desviacion-lubricacion", response_model=list[DesviacionOut])
def desviacion(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.desviacion_lubricacion(db, desde=desde, hasta=hasta)
