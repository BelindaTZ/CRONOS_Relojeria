"""Schemas base compartidos por todos los módulos.

`Page[T]` y `ErrorResponse` fijan la forma de las respuestas paginadas y de error
en toda la API (Constitución, Principios V y XI).
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Formato único de error de la API."""

    code: str = Field(description="código estable legible por máquina, p. ej. 'not_found'")
    message: str = Field(description="mensaje legible por humanos")
    field: str | None = Field(default=None, description="campo asociado, si aplica")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Page(BaseModel, Generic[T]):
    """Envoltura estándar de listados paginados (Constitución, Principio XI)."""

    items: list[T]
    total: int = Field(description="total de registros que cumplen el filtro")
    page: int = Field(ge=1, description="página actual (1-indexada)")
    size: int = Field(ge=1, description="tamaño de página solicitado")

    @property
    def pages(self) -> int:
        if self.size == 0:
            return 0
        return (self.total + self.size - 1) // self.size
