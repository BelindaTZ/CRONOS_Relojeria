"""Parámetros de paginación reutilizables por los routers de todos los módulos."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageParams:
    """Parámetros de paginación normalizados."""

    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def page_params(
    page: int = Query(default=1, ge=1, description="página (1-indexada)"),
    size: int = Query(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"tamaño de página (máx. {MAX_PAGE_SIZE})",
    ),
) -> PageParams:
    """Dependencia FastAPI para inyectar paginación en un endpoint de listado."""
    return PageParams(page=page, size=size)
