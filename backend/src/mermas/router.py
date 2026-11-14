from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from mermas import service
from mermas.schemas import (
    AutorizarBajaIn,
    EstadoIn,
    MermaIn,
    MermaOut,
    ReclamoIn,
    ReclamoOut,
    ReclamoPatch,
    ReporteMermaItem,
)
from shared.database import get_db
from shared.guard import CurrentUser, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["mermas"])

_leer = require_perm("mermas", "consultar")
_crear = require_perm("mermas", "crear")
_editar = require_perm("mermas", "editar")
_autorizar = require_perm("mermas", "eliminar")  # FR-015: solo Gerencia General tiene "eliminar" en mermas


@router.get("/mermas", response_model=Page[MermaOut])
def listar(
    causa: str | None = None,
    estado: str | None = None,
    sucursal_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    items, total = service.listar(
        db, user=user, causa=causa, estado=estado, sucursal_id=sucursal_id, desde=desde, hasta=hasta,
        offset=pp.offset, limit=pp.limit,
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("/mermas", response_model=MermaOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: MermaIn,
    discrepancia_id: int | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_crear),
):
    return service.crear_merma(db, datos, user=user, discrepancia_id=discrepancia_id)


@router.get("/mermas/{mid}", response_model=MermaOut)
def obtener(mid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.obtener(db, mid, user=user)


@router.post("/mermas/{mid}/documentos", status_code=status.HTTP_201_CREATED)
async def subir_documento(
    mid: int,
    tipo: str = Form(default="otro"),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_editar),
):
    data = await archivo.read()
    return service.subir_documento(db, mid, tipo=tipo, nombre=archivo.filename or "documento", data=data, actor=user.id)


@router.post("/mermas/{mid}/autorizar-baja", response_model=MermaOut, status_code=status.HTTP_201_CREATED)
def autorizar_baja(mid: int, datos: AutorizarBajaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_autorizar)):
    return service.autorizar_baja(db, mid, datos, user=user)


@router.post("/mermas/{mid}/estado", response_model=MermaOut)
def cambiar_estado(mid: int, datos: EstadoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.cambiar_estado(db, mid, datos, user=user)


@router.post("/mermas/{mid}/reclamo", response_model=MermaOut, status_code=status.HTTP_201_CREATED)
def crear_reclamo(mid: int, datos: ReclamoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.crear_reclamo(db, mid, datos, user=user)


@router.patch("/mermas/{mid}/reclamo", response_model=ReclamoOut)
def actualizar_reclamo(mid: int, datos: ReclamoPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.actualizar_reclamo(db, mid, datos, actor=user.id)


@router.get("/reportes/mermas", response_model=list[ReporteMermaItem])
def reporte(
    causa: str | None = None,
    sucursal_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    return service.reporte_mermas(db, user=user, causa=causa, sucursal_id=sucursal_id, desde=desde, hasta=hasta)
