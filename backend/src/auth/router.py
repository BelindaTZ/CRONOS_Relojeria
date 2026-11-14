from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from auth import service
from auth.schemas import (
    AccessOut,
    CambiarContrasenaIn,
    LoginIn,
    OlvideContrasenaIn,
    RefreshIn,
    TokenOut,
)
from shared.database import get_db
from shared.guard import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, request: Request, db: Session = Depends(get_db)):
    return service.login(db, identificacion=datos.identificacion, password=datos.password, ip=_ip(request))


@router.post("/refresh", response_model=AccessOut)
def refresh(datos: RefreshIn, db: Session = Depends(get_db)):
    return service.refresh(db, refresh_token=datos.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    datos: RefreshIn | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service.logout(db, refresh_token=datos.refresh_token if datos else None, usuario_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cambiar-contrasena", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_contrasena(
    datos: CambiarContrasenaIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service.cambiar_contrasena(db, usuario_id=user.id, actual=datos.actual, nueva=datos.nueva)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/olvide-contrasena", status_code=status.HTTP_202_ACCEPTED)
def olvide_contrasena(datos: OlvideContrasenaIn, request: Request, db: Session = Depends(get_db)):
    service.solicitar_restablecimiento(db, identificacion=datos.identificacion, ip=_ip(request))
    return {"detail": "Si el usuario existe, se envió un correo con instrucciones."}
