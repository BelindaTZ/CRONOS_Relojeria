"""Jerarquía de excepciones de dominio + handlers FastAPI.

Los módulos de negocio lanzan estas excepciones; los handlers las traducen al
formato único de error (`shared.schemas.ErrorResponse`). Los routers no arman
respuestas de error a mano (Constitución, Principio X).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.schemas import ErrorDetail, ErrorResponse


class DomainError(Exception):
    """Base de todos los errores de negocio esperables."""

    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"


class PermissionDeniedError(DomainError):
    status_code = 403
    code = "permission_denied"


class DependencyUnavailableError(DomainError):
    """Una dependencia crítica (DB, almacenamiento) no responde."""

    status_code = 503
    code = "dependency_unavailable"


def _error_payload(code: str, message: str, field: str | None = None) -> dict:
    return ErrorResponse(error=ErrorDetail(code=code, message=message, field=field)).model_dump(
        exclude_none=True
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los handlers en la app FastAPI."""

    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.code, exc.message, exc.field),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = first.get("loc", [])
        field = ".".join(str(p) for p in loc if p != "body") or None
        return JSONResponse(
            status_code=422,
            content=_error_payload("validation_error", first.get("msg", "entrada inválida"), field),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=500,
            content=_error_payload("internal_error", "Error interno del servidor"),
        )
