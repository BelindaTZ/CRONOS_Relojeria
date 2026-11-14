"""Prueba de contrato (SC-002 / FR-009): todo endpoint de negocio pasa por el guard.

Recorre las rutas montadas y verifica que el árbol de dependencias de cada una
incluye un guard (`require_perm` -> `_dep`, `require_gerencia_o_delegado`, o un
guard de identidad para el autoservicio).
"""

from __future__ import annotations

from main import create_app

PUBLICOS = {
    ("GET", "/health"),
    ("GET", "/openapi.json"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
    ("POST", "/auth/login"),
    ("POST", "/auth/refresh"),
    ("POST", "/auth/olvide-contrasena"),
    # feature 014: webhook de eventos de entrega de SendGrid — lo llama el
    # proveedor externo, nunca un usuario con sesión (contrato "security: []").
    ("POST", "/webhooks/email"),
}
AUTENTICADOS_SIN_PERM = {
    ("POST", "/auth/logout"),
    ("POST", "/auth/cambiar-contrasena"),
    ("GET", "/perfil"),
    ("PATCH", "/perfil"),
}

_GUARD_NAMES = {
    "_dep",  # el que devuelve require_perm(...)
    "require_gerencia_o_delegado",
    "get_current_user",
    "get_current_user_full_scope",
}


def _nombres_dependencias(dependant, vistos=None) -> set[str]:
    vistos = vistos if vistos is not None else set()
    for sub in dependant.dependencies:
        nombre = getattr(sub.call, "__name__", "")
        if nombre and nombre not in vistos:
            vistos.add(nombre)
            _nombres_dependencias(sub, vistos)
    return vistos


def test_todo_endpoint_de_negocio_declara_permiso():
    app = create_app()
    sin_guard: list[str] = []
    for route in app.routes:
        methods = getattr(route, "methods", None)
        dependant = getattr(route, "dependant", None)
        path = getattr(route, "path", "")
        if not methods or dependant is None:
            continue
        nombres = _nombres_dependencias(dependant)
        for m in methods:
            if m in ("HEAD", "OPTIONS"):
                continue
            key = (m, path)
            if key in PUBLICOS or key in AUTENTICADOS_SIN_PERM:
                continue
            if not (nombres & _GUARD_NAMES):
                sin_guard.append(f"{m} {path}")

    assert not sin_guard, "Endpoints sin guard RBAC: " + ", ".join(sorted(sin_guard))
