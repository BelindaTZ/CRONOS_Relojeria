"""Rol de PostgreSQL de SOLO LECTURA, exclusivo del pipeline ELT (feature 012).

Const. Ppio III (separación de motores) y checklist `data-pipeline.md` DP002:
"¿el pipeline usa credenciales/rol de solo lectura y no el usuario de la app?" — sí,
desde esta migración. El DAG (`data/lib/extract.py`) se conecta con este rol, nunca
con `POSTGRES_USER`/el usuario de la app.

`GRANT SELECT` sobre todas las tablas actuales del esquema `public` + `ALTER DEFAULT
PRIVILEGES` para que las tablas de features futuras también queden legibles sin
migraciones adicionales (FR-018 — el pipeline tolera dominios/tablas nuevas).

Nota técnica: los identificadores (nombre de rol) NUNCA se pueden parametrizar en
SQL — ni con bind params de SQLAlchemy ni dentro de un bloque `DO $$ ... $$` (los
bloques PL/pgSQL anónimos no reciben parámetros externos). Se arma el SQL con el
nombre de rol validado contra un patrón estricto (viene de `.env`, no de un
usuario final) y la contraseña vía `sql.Literal` de psycopg (escapada, nunca
concatenada a mano) — Ppio IX: credenciales solo vía `.env`, nunca hardcodeadas.

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-11
"""
from __future__ import annotations

import os
import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from psycopg import sql

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROL = os.environ.get("ELT_PG_RO_USER", "cronos_elt_ro")
_PASSWORD = os.environ.get("ELT_PG_RO_PASSWORD", "changeme-elt-ro")

if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", _ROL):
    raise ValueError(f"ELT_PG_RO_USER inválido como identificador SQL: {_ROL!r}")


def _raw(compuesto: sql.Composed) -> str:
    """Renderiza un `sql.Composed` de psycopg a texto SQL plano (sin conexión —
    basta un escape estático porque el rol ya está validado y el password se
    escapa con `sql.Literal`, que no depende del server)."""
    return compuesto.as_string(None)


def upgrade() -> None:
    bind = op.get_bind()
    rol_id = sql.Identifier(_ROL)

    existe = bind.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :rol"), {"rol": _ROL}).first()
    if not existe:
        crear = sql.SQL("CREATE ROLE {rol} LOGIN PASSWORD {pwd}").format(rol=rol_id, pwd=sql.Literal(_PASSWORD))
        bind.execute(sa.text(_raw(crear)))

    db_actual = bind.execute(sa.text("SELECT current_database()")).scalar()
    for stmt in [
        sql.SQL("GRANT CONNECT ON DATABASE {db} TO {rol}").format(db=sql.Identifier(db_actual), rol=rol_id),
        sql.SQL("GRANT USAGE ON SCHEMA public TO {rol}").format(rol=rol_id),
        sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {rol}").format(rol=rol_id),
        sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {rol}").format(rol=rol_id),
    ]:
        bind.execute(sa.text(_raw(stmt)))
    # Nunca escritura: sin GRANT INSERT/UPDATE/DELETE. Redundante por diseño (el
    # rol nace sin esos privilegios) pero lo dejamos explícito como documentación viva.


def downgrade() -> None:
    """Revoca solo lo que `upgrade()` concedió EN ESTA base de datos. El rol en
    sí NO se elimina: es un objeto global del clúster de PostgreSQL, compartido
    entre `cronos` y `cronos_test` (la suite de tests corre downgrade/upgrade
    repetidos sobre `cronos_test` — un `DROP ROLE` ahí fallaría con
    `DependentObjectsStillExist` mientras el rol siga teniendo privilegios
    concedidos en `cronos`, o directamente rompería esos privilegios si se
    forzara). `upgrade()` ya es idempotente (`CREATE ROLE` solo si falta)."""
    bind = op.get_bind()
    rol_id = sql.Identifier(_ROL)
    db_actual = bind.execute(sa.text("SELECT current_database()")).scalar()
    for stmt in [
        sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM {rol}").format(rol=rol_id),
        sql.SQL("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {rol}").format(rol=rol_id),
        sql.SQL("REVOKE USAGE ON SCHEMA public FROM {rol}").format(rol=rol_id),
        sql.SQL("REVOKE CONNECT ON DATABASE {db} FROM {rol}").format(db=sql.Identifier(db_actual), rol=rol_id),
    ]:
        bind.execute(sa.text(_raw(stmt)))
