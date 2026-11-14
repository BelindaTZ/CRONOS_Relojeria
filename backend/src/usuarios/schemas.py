from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class PerfilOut(BaseModel):
    id: int
    identificacion: str
    nombre: str
    roles: list[str]
    sucursales: list[str]
    sucursal_ids: list[int] = Field(default_factory=list)
    email: str
    foto_perfil_url: str | None = None
    permisos: dict[str, list[str]] = Field(default_factory=dict)


class PerfilPatch(BaseModel):
    email: EmailStr | None = None
    # la foto llega como archivo multipart, no en el body JSON


class UsuarioIn(BaseModel):
    identificacion: str = Field(min_length=5, max_length=20)
    nombre: str = Field(min_length=2, max_length=160)
    email: EmailStr
    # El sistema genera la contraseña temporal; el gerente no la escribe (FR-013).
    rol_ids: list[int] = Field(default_factory=list)
    sucursal_ids: list[int] = Field(default_factory=list)


class UsuarioPatch(BaseModel):
    nombre: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    estado: str | None = Field(default=None, pattern="^(activo|inactivo)$")


class UsuarioOut(BaseModel):
    id: int
    identificacion: str
    nombre: str
    email: str
    estado: str
    roles: list[str]
    sucursales: list[str]
    # solo se rellena al CREAR el usuario — mostrar una vez, no se vuelve a exponer
    password_temporal: str | None = None


class IdsIn(BaseModel):
    ids: list[int] = Field(default_factory=list)


class ExcepcionIn(BaseModel):
    modulo: str
    operacion: str | None = None
    efecto: str = Field(pattern="^(conceder|revocar)$")
