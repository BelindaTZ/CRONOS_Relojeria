"""Migraciones idempotentes y esquema base de RBAC (US3 / FR-011).

Requiere una PostgreSQL accesible vía DATABASE_URL. Si no hay, se omite
(en CI se ejecuta dentro de `docker compose`, con la base disponible).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import sqlalchemy as sa

BACKEND_DIR = Path(__file__).resolve().parents[1]
RBAC_TABLES = {"rol", "modulo", "operacion", "permiso_modulo", "permiso_operacion"}


def _db_url() -> str:
    return os.environ["DATABASE_URL"]


def _db_available() -> bool:
    try:
        engine = sa.create_engine(_db_url())
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL no disponible (DATABASE_URL)")


@pytest.fixture
def alembic_cfg():
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", _db_url())
    return cfg


@pytest.fixture(autouse=True)
def _clean(alembic_cfg):
    from alembic import command

    command.downgrade(alembic_cfg, "base")
    yield
    # Deja la base migrada al terminar para no romper el stack en ejecución.
    command.upgrade(alembic_cfg, "head")


def _inspector():
    return sa.inspect(sa.create_engine(_db_url()))


def test_upgrade_crea_las_cinco_tablas_rbac(alembic_cfg):
    from alembic import command

    command.upgrade(alembic_cfg, "head")

    tablas = set(_inspector().get_table_names())
    assert RBAC_TABLES <= tablas


def test_operacion_sembrada_con_cuatro_filas_resto_vacio(alembic_cfg):
    from alembic import command

    command.upgrade(alembic_cfg, "head")

    engine = sa.create_engine(_db_url())
    with engine.connect() as conn:
        claves = {r[0] for r in conn.execute(sa.text("SELECT clave FROM operacion"))}
        assert claves == {"crear", "consultar", "editar", "eliminar"}
        # `modulo` lo siembra 001 (0003); `rol`/`permiso_modulo`/`permiso_operacion`
        # nacían vacías hasta 0024, que siembra los 5 roles de negocio de la
        # Constitución §3 (Gerencia General la crea aparte `scripts/seed_gerencia.py`,
        # sigue sin nacer de una migración).
        roles = {r[0] for r in conn.execute(sa.text("SELECT nombre FROM rol"))}
        assert roles == {"Gerente de Sucursal", "Vendedor", "Técnico", "Técnico Jefe", "Contador"}
        for tabla in ("permiso_modulo", "permiso_operacion"):
            n = conn.execute(sa.text(f"SELECT count(*) FROM {tabla}")).scalar_one()
            assert n > 0, f"{tabla} debería tener la matriz de los roles sembrados"


def test_segundo_upgrade_no_aplica_migraciones(alembic_cfg):
    from alembic import command
    from alembic.runtime.migration import MigrationContext

    command.upgrade(alembic_cfg, "head")
    engine = sa.create_engine(_db_url())
    with engine.connect() as conn:
        rev_antes = MigrationContext.configure(conn).get_current_revision()

    command.upgrade(alembic_cfg, "head")  # no debe fallar ni cambiar nada
    with engine.connect() as conn:
        rev_despues = MigrationContext.configure(conn).get_current_revision()

    assert rev_antes == rev_despues
    assert rev_antes is not None


def test_downgrade_base_elimina_las_tablas(alembic_cfg):
    from alembic import command

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")

    tablas = set(_inspector().get_table_names())
    assert not (RBAC_TABLES & tablas)


def test_unicidad_y_fks_declaradas(alembic_cfg):
    from alembic import command

    command.upgrade(alembic_cfg, "head")
    insp = _inspector()

    uniques = {uc["name"] for uc in insp.get_unique_constraints("rol")}
    assert "uq_rol_nombre" in uniques
    assert "uq_modulo_clave" in {uc["name"] for uc in insp.get_unique_constraints("modulo")}
    assert "uq_operacion_clave" in {uc["name"] for uc in insp.get_unique_constraints("operacion")}

    pm_uniques = {tuple(uc["column_names"]) for uc in insp.get_unique_constraints("permiso_modulo")}
    assert ("rol_id", "modulo_id") in pm_uniques
    po_uniques = {tuple(uc["column_names"]) for uc in insp.get_unique_constraints("permiso_operacion")}
    assert ("rol_id", "modulo_id", "operacion_id") in po_uniques

    fk_targets = {fk["referred_table"] for fk in insp.get_foreign_keys("permiso_operacion")}
    assert {"rol", "modulo", "operacion"} <= fk_targets
