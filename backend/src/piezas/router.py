from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from piezas import service
from piezas.schemas import (
    LoteCaducidadOut,
    LoteOut,
    MovimientoIn,
    MovimientoOut,
    PiezaDetalle,
    PiezaIn,
    PiezaOut,
    PiezaPatch,
    ValorPiezasOut,
)
from shared.database import get_db
from shared.guard import CurrentUser, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["piezas"])

_leer = require_perm("piezas", "consultar")
_crear = require_perm("piezas", "crear")
_editar = require_perm("piezas", "editar")


@router.get("/piezas", response_model=Page[PiezaOut])
def listar(
    q: str | None = None,
    calibre_id: int | None = None,
    bajo_minimo: bool = False,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    items, total = service.listar(
        db, user=user, q=q, calibre_id=calibre_id, bajo_minimo=bajo_minimo, offset=pp.offset, limit=pp.limit
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("/piezas", response_model=PiezaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: PiezaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear(db, datos, actor=user.id)


@router.get("/piezas/lotes", response_model=list[LoteCaducidadOut])
def lotes_caducidad(
    estado: str | None = None,
    sucursal_id: int | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    return service.listar_lotes_caducidad(db, user=user, estado=estado, sucursal_id=sucursal_id)


@router.get("/piezas/valor", response_model=ValorPiezasOut)
def valor(db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.valor_piezas(db, user=user)


@router.get("/piezas/{pid}", response_model=PiezaDetalle)
def detalle(pid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.obtener_detalle(db, pid, user=user)


@router.patch("/piezas/{pid}", response_model=PiezaOut)
def actualizar(pid: int, datos: PiezaPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.actualizar(db, pid, datos, actor=user.id)


@router.post("/piezas/{pid}/inactivar", response_model=PiezaOut)
def inactivar(pid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.inactivar(db, pid, actor=user.id)


@router.get("/piezas/{pid}/movimientos", response_model=Page[MovimientoOut])
def movimientos(
    pid: int,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    items, total = service.movimientos(db, pid, offset=pp.offset, limit=pp.limit)
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("/piezas/{pid}/movimientos", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
def registrar_movimiento(
    pid: int, datos: MovimientoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)
):
    return service.registrar_movimiento(db, pid, datos, actor=user.id)


@router.get("/piezas/{pid}/lotes", response_model=list[LoteOut])
def lotes(pid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.lotes(db, pid)
