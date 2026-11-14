from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from inventario import service
from inventario.schemas import (
    AlertaStockOut,
    CalibreIn,
    CalibreOut,
    DisponibilidadGlobalOut,
    DocumentoRelojOut,
    EventoSerieOut,
    FotoOut,
    LineaRecepcionPendienteOut,
    RelojDetalle,
    RelojIn,
    RelojOut,
    RelojPatch,
    ValorInventarioOut,
)
from shared.database import get_db
from shared.exceptions import ValidationError
from shared.guard import CurrentUser, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["inventario"])

_leer = require_perm("inventario_relojes", "consultar")
_crear = require_perm("inventario_relojes", "crear")
_editar = require_perm("inventario_relojes", "editar")


# --------------------------------------------------------------- relojes
@router.get("/relojes", response_model=Page[RelojOut])
def listar_relojes(
    q: str | None = None,
    marca: str | None = None,
    sucursal_id: int | None = None,
    disponibilidad: str | None = None,
    calibre: str | None = None,
    tipo_cristal: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    items, total = service.listar_relojes(
        db, user=user, q=q, marca=marca, sucursal_id=sucursal_id, disponibilidad=disponibilidad,
        calibre=calibre, offset=pp.offset, limit=pp.limit, tipo_cristal=tipo_cristal,
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.get("/relojes/buscar-global", response_model=list[DisponibilidadGlobalOut])
def buscar_disponibilidad_global(
    q: str | None = None, marca: str | None = None, calibre: str | None = None, tipo_cristal: str | None = None,
    db: Session = Depends(get_db), _: CurrentUser = Depends(_leer),
):
    """Esp. §4.1/§4.4: el vendedor puede «consultar el inventario completo» —
    todas las sucursales, no solo la suya — para saber si un modelo que no
    tiene localmente existe en otra (y de ahí ofrecer un traslado, 004)."""
    return service.buscar_disponibilidad_global(db, q=q, marca=marca, calibre=calibre, tipo_cristal=tipo_cristal)


@router.post("/relojes", response_model=RelojDetalle, status_code=status.HTTP_201_CREATED)
async def crear_reloj(
    data: str = Form(..., description="JSON de la ficha (RelojIn)"),
    foto: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_crear),
):
    try:
        datos = RelojIn.model_validate_json(data)
    except ValueError as exc:
        raise ValidationError(f"Ficha inválida: {exc}", field="data") from exc
    contenido = await foto.read() if foto is not None else None
    return service.crear_reloj(
        db, datos, foto=contenido, foto_nombre=foto.filename if foto else None, actor=user.id
    )


@router.get("/relojes/pendientes-recepcion", response_model=list[LineaRecepcionPendienteOut])
def pendientes_recepcion(db: Session = Depends(get_db), _: CurrentUser = Depends(_crear)):
    return service.lineas_recepcion_pendientes(db)


@router.get("/relojes/{serie}", response_model=RelojDetalle)
def obtener_reloj(serie: str, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.obtener_por_serie(db, serie, user=user)


@router.get("/relojes/{serie}/historial", response_model=list[EventoSerieOut])
def historial(serie: str, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.historial_serie(db, serie)


@router.patch("/relojes/{rid}", response_model=RelojDetalle)
def corregir_reloj(rid: int, datos: RelojPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.corregir_reloj(db, rid, datos, user=user)


@router.post("/relojes/{rid}/fotos", response_model=FotoOut, status_code=status.HTTP_201_CREATED)
async def agregar_foto(
    rid: int, foto: UploadFile = File(...), db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)
):
    data = await foto.read()
    return service.agregar_foto(db, rid, data=data, nombre=foto.filename, actor=user.id)


@router.post("/relojes/{rid}/documentos", response_model=DocumentoRelojOut, status_code=status.HTTP_201_CREATED)
async def agregar_documento(
    rid: int,
    tipo: str = Form(default="otro"),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_editar),
):
    data = await archivo.read()
    return service.agregar_documento(
        db, rid, tipo=tipo, nombre=archivo.filename or "documento", data=data, actor=user.id
    )


# --------------------------------------------------------------- calibres
@router.get("/calibres", response_model=list[CalibreOut])
def listar_calibres(q: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_calibres(db, q=q)


@router.post("/calibres", response_model=CalibreOut, status_code=status.HTTP_201_CREATED)
def crear_calibre(datos: CalibreIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_calibre(db, datos, actor=user.id)


# --------------------------------------------------------------- alertas / valor
@router.get("/alertas-stock", response_model=list[AlertaStockOut])
def alertas_stock(
    tipo: str | None = None,
    sucursal_id: int | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.listar_alertas(db, tipo=tipo, sucursal_id=sucursal_id)


@router.get("/valor-inventario", response_model=ValorInventarioOut)
def valor_inventario(
    sucursal_id: int | None = None, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)
):
    return service.valor_inventario(db, user=user, sucursal_id=sucursal_id)
