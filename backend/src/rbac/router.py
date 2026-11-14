"""Router del módulo RBAC. Solo HTTP; la lógica vive en el service (Principio X)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from rbac import service
from rbac.schemas import ModuloOut, PermisoModuloIn, PermisoModuloOut, RolIn, RolOut
from shared.database import get_db
from shared.guard import CurrentUser, require_perm

router = APIRouter(tags=["rbac"])

_leer = require_perm("configuracion", "consultar")
_crear = require_perm("configuracion", "crear")
_editar = require_perm("configuracion", "editar")


@router.get("/roles", response_model=list[RolOut])
def listar_roles(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_roles(db)


@router.post("/roles", response_model=RolOut, status_code=status.HTTP_201_CREATED)
def crear_rol(datos: RolIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_rol(db, datos, actor=user.id)


@router.get("/modulos", response_model=list[ModuloOut])
def listar_modulos(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_modulos(db)


@router.get("/roles/{rol_id}/permisos", response_model=list[PermisoModuloOut])
def get_permisos(rol_id: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.get_permisos_rol(db, rol_id)


@router.put("/roles/{rol_id}/permisos", response_model=list[PermisoModuloOut])
def set_permisos(
    rol_id: int,
    entradas: list[PermisoModuloIn],
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_editar),
):
    return service.set_permisos_rol(db, rol_id, entradas, actor=user.id)
