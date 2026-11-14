from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from clientes import service
from clientes.schemas import (
    AplicarDescuentoIn,
    AplicarDescuentoOut,
    AutorizarMargenIn,
    ClienteEnRiesgoOut,
    CuponReactivacionIn,
    ClienteDetalle,
    ClienteIn,
    ClienteOut,
    ClientePatch,
    ClientesPorNivelOut,
    ConsumirCuponIn,
    CuponIn,
    CuponOut,
    DescuentoIn,
    DescuentoOut,
    DescuentoPatch,
    EstadoClienteIn,
    HistorialClienteOut,
    MargenMinimoIn,
    MargenMinimoOut,
    MejorClienteOut,
    NivelIn,
    NivelOut,
    RecalcularNivelIn,
    RecalcularNivelOut,
    ReglaNivelIn,
    TextoConsentimientoOut,
)
from shared.database import get_db
from shared.guard import (
    CurrentUser,
    get_current_user_full_scope,
    require_gerencia_o_delegado,
    require_perm,
)
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["clientes"])

_leer = require_perm("clientes_fidelizacion", "consultar")
_crear = require_perm("clientes_fidelizacion", "crear")
_editar = require_perm("clientes_fidelizacion", "editar")


# --------------------------------------------------------------------- clientes
@router.get("/clientes", response_model=Page[ClienteOut])
def listar(
    q: str | None = None,
    nivel_id: int | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    items, total = service.listar(db, q=q, nivel_id=nivel_id, offset=pp.offset, limit=pp.limit)
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.get("/clientes/texto-consentimiento", response_model=TextoConsentimientoOut)
def texto_consentimiento(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.texto_consentimiento(db)


@router.post("/clientes", response_model=ClienteDetalle, status_code=status.HTTP_201_CREATED)
def crear(datos: ClienteIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear(db, datos, actor=user.id)


@router.get("/clientes/{cid}", response_model=ClienteDetalle)
def detalle(cid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.obtener_detalle(db, cid)


@router.patch("/clientes/{cid}", response_model=ClienteDetalle)
def actualizar(cid: int, datos: ClientePatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.actualizar(db, cid, datos, user=user)


@router.put("/clientes/{cid}/estado", response_model=ClienteOut)
def set_estado(cid: int, datos: EstadoClienteIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_estado(db, cid, datos.estado, actor=user.id)


@router.get("/clientes/{cid}/historial", response_model=HistorialClienteOut)
def historial(cid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.historial_cliente(db, cid)


# --------------------------------------------------------------------- niveles
@router.get("/niveles", response_model=list[NivelOut])
def listar_niveles(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_niveles(db)


@router.post("/niveles", response_model=NivelOut, status_code=status.HTTP_201_CREATED)
def crear_nivel(datos: NivelIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)):
    return service.crear_nivel(db, datos, actor=user.id)


@router.put("/niveles/{nid}/regla", response_model=NivelOut)
def set_regla_nivel(nid: int, datos: ReglaNivelIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)):
    return service.set_regla_nivel(db, nid, datos, actor=user.id)


# --------------------------------------------------------------------- descuentos
@router.get("/descuentos", response_model=list[DescuentoOut])
def listar_descuentos(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_descuentos(db)


@router.post("/descuentos", response_model=DescuentoOut, status_code=status.HTTP_201_CREATED)
def crear_descuento(datos: DescuentoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)):
    return service.crear_descuento(db, datos, actor=user.id)


@router.patch("/descuentos/{did}", response_model=DescuentoOut)
def actualizar_descuento(did: int, datos: DescuentoPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)):
    return service.actualizar_descuento(db, did, datos, actor=user.id)


# --------------------------------------------------------------------- cupones
@router.get("/cupones", response_model=list[CuponOut])
def listar_cupones(
    cliente_id: int | None = None,
    estado: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.listar_cupones(db, cliente_id=cliente_id, estado=estado)


@router.post("/cupones", response_model=CuponOut, status_code=status.HTTP_201_CREATED)
def crear_cupon(datos: CuponIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)):
    return service.crear_cupon(db, datos, actor=user.id)


# --------------------------------------------------------------------- margen mínimo
@router.get("/margen-minimo", response_model=MargenMinimoOut)
def get_margen_minimo(
    ambito: str = "global",
    ref: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.get_margen_minimo(db, ambito=ambito, ref=ref)


@router.put("/margen-minimo", response_model=MargenMinimoOut)
def set_margen_minimo(datos: MargenMinimoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)):
    return service.set_margen_minimo(db, datos, actor=user.id)


# --------------------------------------------------------------------- reportes
@router.get("/reportes/clientes-por-nivel", response_model=list[ClientesPorNivelOut])
def reporte_clientes_por_nivel(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.clientes_por_nivel(db)


@router.get("/reportes/mejores-clientes", response_model=list[MejorClienteOut])
def reporte_mejores_clientes(
    top: int = 20,
    desde: date | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.mejores_clientes(db, top=top, desde=desde)


@router.get("/reportes/clientes-en-riesgo", response_model=list[ClienteEnRiesgoOut])
def reporte_clientes_en_riesgo(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.clientes_en_riesgo(db)


@router.post("/cupones/reactivacion", response_model=CuponOut, status_code=status.HTTP_201_CREATED)
def emitir_cupon_reactivacion(
    datos: CuponReactivacionIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)
):
    return service.emitir_cupon_reactivacion(db, datos, actor=user.id)


# --------------------------------------------------------------- interno (008/009)
internal_router = APIRouter(prefix="/_internal", tags=["_internal"])


@internal_router.post("/fidelizacion/recalcular", response_model=RecalcularNivelOut)
def recalcular_nivel(
    datos: RecalcularNivelIn,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user_full_scope),
):
    return service.recalcular_nivel(
        db, cliente_id=datos.cliente_id, hecho=datos.hecho, documento_id=datos.documento_id
    )


@internal_router.post("/descuentos/aplicar", response_model=AplicarDescuentoOut)
def aplicar_descuento(
    datos: AplicarDescuentoIn,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user_full_scope),
):
    return service.aplicar_descuento(db, datos)


@internal_router.post("/descuentos/autorizar", status_code=status.HTTP_201_CREATED)
def autorizar_margen(
    datos: AutorizarMargenIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_full_scope),
):
    return service.autorizar_margen_minimo(db, datos, user=user)


@internal_router.post("/cupones/consumir", response_model=CuponOut)
def consumir_cupon(
    datos: ConsumirCuponIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_full_scope),
):
    return service.consumir_cupon(
        db, codigo=datos.codigo, documento_tipo=datos.documento_tipo,
        documento_id=datos.documento_id, actor=user.id,
    )
