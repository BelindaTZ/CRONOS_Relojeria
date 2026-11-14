from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from citas import service
from citas.schemas import (
    AtenderIn,
    AtenderOut,
    CancelarIn,
    CitaIn,
    CitaOut,
    CitaPatch,
    ConfirmarIn,
    ConfirmarOut,
    ConversionOut,
    VincularIn,
)
from citas.schemas import AgendaItemOut
from shared.database import get_db
from shared.guard import CurrentUser, get_current_user_full_scope, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["citas"])

_leer = require_perm("citas", "consultar")
_crear = require_perm("citas", "crear")
_editar = require_perm("citas", "editar")


@router.get("/citas", response_model=Page[CitaOut])
def listar(
    q: str | None = None,
    estado: str | None = None,
    canal_cita_id: int | None = None,
    sucursal_id: int | None = None,
    cliente_id: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    items, total = service.listar(
        db, user=user, q=q, estado=estado, canal_cita_id=canal_cita_id, sucursal_id=sucursal_id,
        cliente_id=cliente_id, desde=desde, hasta=hasta, offset=pp.offset, limit=pp.limit,
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.get("/citas/conversion", response_model=ConversionOut)
def conversion(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.conversion(db, desde=desde, hasta=hasta)


@router.get("/agenda", response_model=list[AgendaItemOut])
def agenda(
    rango: str,
    fecha: date,
    sucursal_id: int | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    return service.agenda(
        db, user=user, rango=rango,
        fecha=datetime(fecha.year, fecha.month, fecha.day),
        sucursal_id=sucursal_id,
    )


@router.post("/citas", response_model=CitaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: CitaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear(db, datos, actor=user.id)


@router.get("/citas/{cid}", response_model=CitaOut)
def detalle(cid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.obtener_detalle(db, cid)


@router.patch("/citas/{cid}", response_model=CitaOut)
def actualizar(cid: int, datos: CitaPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.actualizar(db, cid, datos, actor=user.id)


@router.get("/citas/{cid}/historial")
def historial(cid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.historial_estados(db, cid)


@router.post("/citas/{cid}/confirmar", response_model=ConfirmarOut)
def confirmar(cid: int, datos: ConfirmarIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.confirmar(db, cid, fecha_confirmada=datos.fecha_confirmada, actor=user.id)


@router.post("/citas/{cid}/cancelar", response_model=CitaOut)
def cancelar(cid: int, datos: CancelarIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.cancelar(db, cid, motivo=datos.motivo, actor=user.id)


@router.post("/citas/{cid}/atender", response_model=AtenderOut)
def atender(cid: int, datos: AtenderIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.atender(
        db, cid, venta_id=datos.venta_id, orden_trabajo_id=datos.orden_trabajo_id, actor=user.id
    )


# --------------------------------------------------------------- interno (008/009/014)
internal_router = APIRouter(prefix="/_internal", tags=["_internal"])


@internal_router.put("/citas/{cid}/vincular", response_model=CitaOut)
def vincular(
    cid: int,
    datos: VincularIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_full_scope),
):
    return service.vincular(
        db, cid, venta_id=datos.venta_id, orden_trabajo_id=datos.orden_trabajo_id, actor=user.id
    )


@internal_router.get("/citas/confirmadas-pendientes-recordatorio")
def para_recordatorio(
    antelacion: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user_full_scope),
):
    return service.citas_para_recordatorio(db, antelacion=antelacion)
