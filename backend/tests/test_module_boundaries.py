"""Frontera de módulos del backend (Constitución, Principio X — NON-NEGOTIABLE).

Ningún módulo de negocio importa los internos de otro: solo `shared` y la API
pública (`<modulo>` / `<modulo>.public`). Añadir un módulo nuevo no obliga a
tocar otro.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
INFRA = {"shared", "main"}
PUBLIC_SUFFIXES = {"", "public", "routes", "schemas"}


def _module_of(path: Path) -> str:
    return path.relative_to(SRC).parts[0].removesuffix(".py")


def _iter_imports(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def test_ningun_modulo_importa_internos_de_otro():
    violations: list[str] = []

    for py in SRC.rglob("*.py"):
        owner = _module_of(py)
        if owner in INFRA:
            continue

        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for mod in _iter_imports(tree):
            parts = mod.split(".")
            target = parts[0]
            if target in INFRA or target == owner:
                continue
            # ¿es un paquete de otro módulo de src/?
            if not (SRC / target).is_dir():
                continue
            suffix = parts[1] if len(parts) > 1 else ""
            if suffix not in PUBLIC_SUFFIXES:
                violations.append(f"{py.relative_to(SRC)} → {mod}")

    assert not violations, "Imports cruzados de internos:\n" + "\n".join(violations)


def test_existe_shared_y_modulo_plantilla_con_capas():
    assert (SRC / "shared").is_dir()
    for capa in ("config.py", "database.py", "storage.py", "exceptions.py", "schemas.py"):
        assert (SRC / "shared" / capa).is_file(), f"falta shared/{capa}"

    health = SRC / "health"
    for capa in ("router.py", "service.py", "repository.py", "schemas.py"):
        assert (health / capa).is_file(), f"el módulo plantilla debe tener {capa}"
