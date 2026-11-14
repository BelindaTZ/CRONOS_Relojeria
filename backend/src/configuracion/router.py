from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from configuracion import service
from configuracion.schemas import (
    ActivoIn,
    AuditoriaItem,
    CatalogoItem,
    CategoriaGastoIn,
    CategoriaMermaIn,
    CanalCitaIn,
    ColorIn,
    CondicionPagoIn,
    MarcaRelojIn,
    MaterialIn,
    MedioPagoIn,
    ParametroIn,
    ParametroOut,
    SetParametroOut,
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

router = APIRouter(tags=["configuracion"])

_leer = require_perm("configuracion", "consultar")
_crear = require_perm("configuracion", "crear")
_editar = require_perm("configuracion", "editar")
# Los catálogos son datos de referencia consumidos por varios módulos: leerlos solo
# exige autenticación; escribirlos sigue restringido a `configuracion`.
_leer_ref = get_current_user_full_scope


# --- catálogos ---
@router.get("/catalogos/medio-pago", response_model=list[CatalogoItem])
def medios_pago(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)):
    return service.listar_medios_pago(db)


@router.post("/catalogos/medio-pago", response_model=CatalogoItem, status_code=status.HTTP_201_CREATED)
def crear_medio_pago(datos: MedioPagoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_medio_pago(db, datos, actor=user.id)


@router.put("/catalogos/medio-pago/{mid}/activo", response_model=CatalogoItem)
def activo_medio_pago(mid: int, datos: ActivoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_activo_medio_pago(db, mid, datos.activo, actor=user.id)


@router.get("/catalogos/condicion-pago", response_model=list[CatalogoItem])
def condiciones_pago(
    solo_activas: bool = False, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)
):
    return service.listar_condiciones_pago(db, solo_activas=solo_activas)


@router.post("/catalogos/condicion-pago", response_model=CatalogoItem, status_code=status.HTTP_201_CREATED)
def crear_condicion_pago(datos: CondicionPagoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_condicion_pago(db, datos, actor=user.id)


@router.put("/catalogos/condicion-pago/{cid}/activo", response_model=CatalogoItem)
def activo_condicion_pago(cid: int, datos: ActivoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_activo_condicion_pago(db, cid, datos.activo, actor=user.id)


@router.get("/catalogos/categoria-gasto", response_model=list[CatalogoItem])
def categorias_gasto(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)):
    return service.listar_categorias_gasto(db)


@router.post("/catalogos/categoria-gasto", response_model=CatalogoItem, status_code=status.HTTP_201_CREATED)
def crear_categoria_gasto(
    datos: CategoriaGastoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)
):
    return service.crear_categoria_gasto(db, datos, actor=user.id)


@router.get("/catalogos/categoria-merma", response_model=list[CatalogoItem])
def categorias_merma(causa: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)):
    return service.listar_categorias_merma(db, causa=causa)


@router.post("/catalogos/categoria-merma", response_model=CatalogoItem, status_code=status.HTTP_201_CREATED)
def crear_categoria_merma(
    datos: CategoriaMermaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)
):
    return service.crear_categoria_merma(db, datos, actor=user.id)


@router.get("/catalogos/canal-cita", response_model=list[CatalogoItem])
def canales_cita(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)):
    return service.listar_canales_cita(db)


# --- catálogos de la ficha de reloj (marca / material / color) ---
@router.get("/catalogos/marca-reloj", response_model=list[CatalogoItem])
def marcas_reloj(solo_activas: bool = False, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)):
    return service.listar_marcas_reloj(db, solo_activas=solo_activas)


@router.post("/catalogos/marca-reloj", response_model=CatalogoItem, status_code=status.HTTP_201_CREATED)
def crear_marca_reloj(datos: MarcaRelojIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_marca_reloj(db, datos, actor=user.id)


@router.patch("/catalogos/marca-reloj/{mid}", response_model=CatalogoItem)
def actualizar_marca_reloj(mid: int, datos: MarcaRelojIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.actualizar_marca_reloj(db, mid, datos, actor=user.id)


@router.put("/catalogos/marca-reloj/{mid}/activo", response_model=CatalogoItem)
def activo_marca_reloj(mid: int, datos: ActivoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_activo_marca_reloj(db, mid, datos.activo, actor=user.id)


@router.get("/catalogos/material", response_model=list[CatalogoItem])
def materiales(solo_activas: bool = False, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)):
    return service.listar_materiales(db, solo_activas=solo_activas)


@router.post("/catalogos/material", response_model=CatalogoItem, status_code=status.HTTP_201_CREATED)
def crear_material(datos: MaterialIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_material(db, datos, actor=user.id)


@router.put("/catalogos/material/{mid}/activo", response_model=CatalogoItem)
def activo_material(mid: int, datos: ActivoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_activo_material(db, mid, datos.activo, actor=user.id)


@router.get("/catalogos/color", response_model=list[CatalogoItem])
def colores(solo_activas: bool = False, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)):
    return service.listar_colores(db, solo_activas=solo_activas)


@router.post("/catalogos/color", response_model=CatalogoItem, status_code=status.HTTP_201_CREATED)
def crear_color(datos: ColorIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_color(db, datos, actor=user.id)


@router.put("/catalogos/color/{cid}/activo", response_model=CatalogoItem)
def activo_color(cid: int, datos: ActivoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_activo_color(db, cid, datos.activo, actor=user.id)


@router.put("/catalogos/canal-cita", response_model=list[CatalogoItem])
def set_canales_cita(
    entradas: list[CanalCitaIn], db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)
):
    return service.set_canales_cita(db, entradas, actor=user.id)


# --- parámetros (solo Gerencia General / delegado) ---
@router.get("/parametros/{clave}", response_model=ParametroOut)
def get_parametro(
    clave: str,
    ambito_tipo: str = "global",
    ambito_ref: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_gerencia_o_delegado),
):
    return service.get_parametro_out(db, clave, ambito_tipo=ambito_tipo, ambito_ref=ambito_ref)


@router.put("/parametros/{clave}", response_model=SetParametroOut)
def set_parametro(
    clave: str,
    datos: ParametroIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_gerencia_o_delegado),
):
    return service.set_parametro_cmd(db, clave, datos, actor=user.id)


# --- auditoría ---
@router.get("/auditoria", response_model=Page[AuditoriaItem])
def listar_auditoria(
    entidad: str | None = None,
    actor: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_gerencia_o_delegado),
):
    items, total = service.listar_auditoria(
        db, entidad=entidad, actor=actor, desde=desde, hasta=hasta, offset=pp.offset, limit=pp.limit
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)
