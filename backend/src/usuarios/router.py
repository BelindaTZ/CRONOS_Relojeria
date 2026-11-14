from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.guard import CurrentUser, get_current_user_full_scope, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page
from usuarios import service
from usuarios.schemas import ExcepcionIn, IdsIn, PerfilOut, UsuarioIn, UsuarioOut, UsuarioPatch

# --- Autoservicio: cualquier usuario autenticado sobre SUS datos ---
perfil_router = APIRouter(tags=["perfil"])


@perfil_router.get("/perfil", response_model=PerfilOut)
def get_perfil(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user_full_scope)):
    return service.get_perfil(db, user)


@perfil_router.patch("/perfil", response_model=PerfilOut)
async def update_perfil(
    email: str | None = Form(default=None),
    foto: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_full_scope),
):
    archivo = (await foto.read(), foto.content_type or "application/octet-stream") if foto else None
    return service.update_perfil(db, user, email=email, foto=archivo)


# --- Administración: módulo `configuracion` ---
router = APIRouter(prefix="/usuarios", tags=["usuarios"])

_leer = require_perm("configuracion", "consultar")
_crear = require_perm("configuracion", "crear")
_editar = require_perm("configuracion", "editar")


@router.get("", response_model=Page[UsuarioOut])
def listar(
    q: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    items, total = service.listar(db, q=q, offset=pp.offset, limit=pp.limit)
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear(datos: UsuarioIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear(db, datos, actor=user.id)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def actualizar(
    usuario_id: int, datos: UsuarioPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)
):
    return service.actualizar(db, usuario_id, datos, actor=user.id)


@router.put("/{usuario_id}/roles", response_model=UsuarioOut)
def set_roles(
    usuario_id: int, cuerpo: IdsIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)
):
    return service.set_roles(db, usuario_id, cuerpo.ids, actor=user.id)


@router.put("/{usuario_id}/sucursales", response_model=UsuarioOut)
def set_sucursales(
    usuario_id: int, cuerpo: IdsIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)
):
    return service.set_sucursales(db, usuario_id, cuerpo.ids, actor=user.id)


@router.put("/{usuario_id}/excepciones", status_code=status.HTTP_200_OK)
def set_excepciones(
    usuario_id: int,
    entradas: list[ExcepcionIn],
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_editar),
):
    service.set_excepciones(db, usuario_id, [e.model_dump() for e in entradas], actor=user.id)
    return {"detail": "Excepciones guardadas"}
