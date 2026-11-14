from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.guard import CurrentUser, get_current_user_full_scope, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page
from sucursales import service
from sucursales.schemas import HorarioSucursalIn, HorarioSucursalOut, InactivarIn, SucursalIn, SucursalOut

router = APIRouter(prefix="/sucursales", tags=["sucursales"])

# Listar sucursales es dato de referencia (como `categoria_gasto`/`medio_pago`,
# CONVENCIONES §4.1): CUALQUIER usuario autenticado lo necesita para pantallas
# con selector de sucursal (ventas, caja, mermas...) — bug real encontrado
# 2026-09-11: antes exigía `configuracion:consultar` y por eso ningún rol de
# negocio (0024) podía listar sucursales, solo pasaba desapercibido porque la
# mayoría tiene una sola sucursal y el frontend la auto-selecciona sin listar.
_leer_ref = get_current_user_full_scope
_crear = require_perm("configuracion", "crear")
_editar = require_perm("configuracion", "editar")


@router.get("", response_model=Page[SucursalOut])
def listar(
    q: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer_ref),
):
    items, total = service.listar(db, q=q, offset=pp.offset, limit=pp.limit)
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("", response_model=SucursalOut, status_code=status.HTTP_201_CREATED)
def crear(datos: SucursalIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear(db, datos, actor=user.id)


@router.post("/{sucursal_id}/inactivar", response_model=SucursalOut)
def inactivar(
    sucursal_id: int,
    datos: InactivarIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_editar),
):
    return service.inactivar(db, sucursal_id, motivo=datos.motivo, actor=user.id)


@router.get("/{sucursal_id}/horario", response_model=list[HorarioSucursalOut])
def horario(sucursal_id: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer_ref)):
    return service.horario_de(db, sucursal_id)


@router.put("/{sucursal_id}/horario", response_model=list[HorarioSucursalOut])
def set_horario(
    sucursal_id: int, dias: list[HorarioSucursalIn], db: Session = Depends(get_db), user: CurrentUser = Depends(_editar),
):
    return service.set_horario(db, sucursal_id, dias, actor=user.id)
