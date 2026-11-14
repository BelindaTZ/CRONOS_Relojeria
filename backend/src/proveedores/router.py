from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from proveedores import service
from proveedores.schemas import (
    CalificacionIn,
    CalificacionOut,
    CancelarIn,
    CompraProgramadaIn,
    CompraProgramadaOut,
    CorreccionIn,
    DocumentoOut,
    EstadoIn,
    OrdenCompraIn,
    OrdenCompraOut,
    PrellenarIn,
    PrellenarOut,
    ProveedorDetalle,
    UltimoPrecioOut,
    ProveedorIn,
    ProveedorOut,
    ProveedorPatch,
    RecepcionIn,
)
from shared.database import get_db
from shared.guard import CurrentUser, get_current_user_full_scope, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["proveedores"])

_leer = require_perm("proveedores", "consultar")
_crear = require_perm("proveedores", "crear")
_editar = require_perm("proveedores", "editar")


# --------------------------------------------------------------------- proveedor
@router.get("/proveedores", response_model=Page[ProveedorOut])
def listar(
    q: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    items, total = service.listar(db, q=q, tipo=tipo, estado=estado, offset=pp.offset, limit=pp.limit)
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("/proveedores", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear(datos: ProveedorIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear(db, datos, actor=user.id)


@router.get("/proveedores/{pid}", response_model=ProveedorDetalle)
def detalle(pid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.obtener_detalle(db, pid)


@router.patch("/proveedores/{pid}", response_model=ProveedorOut)
def actualizar(pid: int, datos: ProveedorPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.actualizar(db, pid, datos, user=user)


@router.post("/proveedores/{pid}/inactivar", response_model=ProveedorOut)
def inactivar(pid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.inactivar(db, pid, actor=user.id)


@router.post("/proveedores/{pid}/documentos", response_model=DocumentoOut, status_code=status.HTTP_201_CREATED)
async def subir_documento(
    pid: int,
    tipo: str = Form(default="otro"),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_editar),
):
    data = await archivo.read()
    return service.subir_documento(
        db, pid, tipo=tipo, nombre=archivo.filename or "documento", data=data, actor=user.id
    )


@router.get("/proveedores/{pid}/documentos", response_model=list[DocumentoOut])
def listar_documentos(pid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_documentos(db, pid)


@router.post("/proveedores/{pid}/calificaciones", response_model=CalificacionOut, status_code=status.HTTP_201_CREATED)
def calificar(pid: int, datos: CalificacionIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.calificar(db, pid, nota_calidad=datos.nota_calidad, nota_soporte=datos.nota_soporte, actor=user.id)


# --------------------------------------------------------------- órdenes de compra
@router.get("/ordenes-compra", response_model=Page[OrdenCompraOut])
def listar_ordenes(
    proveedor_id: int | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    items, total = service.listar_ordenes(
        db, proveedor_id=proveedor_id, tipo=tipo, estado=estado, offset=pp.offset, limit=pp.limit
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("/ordenes-compra", response_model=OrdenCompraOut, status_code=status.HTTP_201_CREATED)
def crear_orden(datos: OrdenCompraIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_orden(db, datos, actor=user.id)


@router.post("/ordenes-compra/prellenar", response_model=PrellenarOut)
def prellenar(datos: PrellenarIn, db: Session = Depends(get_db), _: CurrentUser = Depends(_crear)):
    return service.prellenar_orden(db, datos)


@router.get("/ordenes-compra/ultimo-precio", response_model=UltimoPrecioOut)
def ultimo_precio(
    item_tipo: str,
    marca: str | None = None,
    referencia: str | None = None,
    pieza_id: int | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_crear),
):
    return service.ultimo_precio(db, item_tipo=item_tipo, marca=marca, referencia=referencia, pieza_id=pieza_id)


@router.post("/ordenes-compra/{oid}/emitir", response_model=OrdenCompraOut)
def emitir(oid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.emitir_orden(db, oid, actor=user.id)


@router.post("/ordenes-compra/{oid}/confirmar", response_model=OrdenCompraOut)
def confirmar(oid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    """El proveedor aceptó el pedido (rol elevado lo registra)."""
    return service.confirmar_orden(db, oid, user=user)


@router.post("/ordenes-compra/{oid}/cancelar", response_model=OrdenCompraOut)
def cancelar(oid: int, datos: CancelarIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.cancelar_orden(db, oid, motivo=datos.motivo, actor=user.id)


@router.post("/ordenes-compra/{oid}/recepciones", response_model=OrdenCompraOut, status_code=status.HTTP_201_CREATED)
def recepcion(oid: int, datos: RecepcionIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_recepcion(db, oid, datos, actor=user.id)


@router.patch("/ordenes-compra/{oid}", response_model=OrdenCompraOut)
def corregir(oid: int, datos: CorreccionIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.corregir_orden(db, oid, datos, user=user)


# --------------------------------------------------------------- compras programadas
@router.get("/compras-programadas", response_model=list[CompraProgramadaOut])
def listar_programadas(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_programadas(db)


@router.post("/compras-programadas", response_model=CompraProgramadaOut, status_code=status.HTTP_201_CREATED)
def crear_programada(datos: CompraProgramadaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_programada(db, datos, actor=user.id)


@router.put("/compras-programadas/{pid}/estado", response_model=CompraProgramadaOut)
def set_estado(pid: int, datos: EstadoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_estado_programada(db, pid, datos.estado, actor=user.id)


# --------------------------------------------------------------- interno (pruebas)
internal_router = APIRouter(prefix="/_internal", tags=["_internal"])


@internal_router.post("/scheduler/tick")
def scheduler_tick(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user_full_scope)):
    """Fuerza una corrida del generador de compras programadas (pruebas / operación)."""
    generadas = service.generar_programadas_vencidas(db, actor=user.id)
    return {"ordenes_generadas": generadas}
