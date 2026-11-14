from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.guard import CurrentUser, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page
from traslados import service
from traslados.schemas import (
    CancelarIn,
    CostoReferencialOut,
    DiscrepanciaOut,
    EnviarIn,
    ItemDisponibleOut,
    RecibirIn,
    SucursalMiniOut,
    TransferenciaIn,
    TransferenciaOut,
)

router = APIRouter(tags=["traslados"])

_leer = require_perm("multisucursal", "consultar")
_crear = require_perm("multisucursal", "crear")
_editar = require_perm("multisucursal", "editar")


@router.get("/transferencias", response_model=Page[TransferenciaOut])
def listar(
    sucursal_id: int | None = None,
    estado: str | None = None,
    numero_serie: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    items, total = service.listar(
        db, user=user, sucursal_id=sucursal_id, estado=estado, numero_serie=numero_serie,
        offset=pp.offset, limit=pp.limit,
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.get("/transferencias/sucursales-activas", response_model=list[SucursalMiniOut])
def sucursales_activas(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.sucursales_activas(db)


@router.get("/transferencias/costo-referencial", response_model=CostoReferencialOut)
def costo_referencial(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    """Costo sugerido a informar cuando el traslado lo pide el cliente en una venta."""
    return service.costo_referencial_venta(db)


@router.get("/transferencias/items-disponibles", response_model=list[ItemDisponibleOut])
def items_disponibles(
    sucursal_id: int,
    item_tipo: str,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_crear),
):
    return service.items_disponibles(db, sucursal_id=sucursal_id, item_tipo=item_tipo, q=q)


@router.post("/transferencias", response_model=TransferenciaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: TransferenciaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear(db, datos, actor=user.id)


@router.get("/transferencias/{tid}", response_model=TransferenciaOut)
def detalle(tid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.obtener_detalle(db, tid, user=user)


@router.post("/transferencias/{tid}/enviar", response_model=TransferenciaOut)
def enviar(tid: int, datos: EnviarIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.enviar(db, tid, responsable_envio_id=datos.responsable_envio_id, actor=user.id)


@router.post("/transferencias/{tid}/recibir", response_model=TransferenciaOut)
def recibir(tid: int, datos: RecibirIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.recibir(db, tid, datos, actor=user.id)


@router.post("/transferencias/{tid}/cancelar", response_model=TransferenciaOut)
def cancelar(tid: int, datos: CancelarIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.cancelar(db, tid, motivo=datos.motivo, actor=user.id)


@router.get("/transferencias/{tid}/discrepancias", response_model=list[DiscrepanciaOut])
def discrepancias(tid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.discrepancias(db, tid)
