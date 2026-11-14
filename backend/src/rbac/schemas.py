"""Schemas del módulo RBAC (roles, catálogo de módulos, matriz de permisos)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Operacion = Literal["crear", "consultar", "editar", "eliminar"]


class RolIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)


class RolOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None


class ModuloOut(BaseModel):
    id: int
    clave: str
    nombre: str


class PermisoModuloIn(BaseModel):
    modulo: str
    acceso: bool
    operaciones: list[Operacion] = Field(default_factory=list)


class PermisoModuloOut(BaseModel):
    modulo: str
    acceso: bool
    operaciones: list[Operacion]
