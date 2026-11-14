"""RBAC base: rol, modulo, operacion, permiso_modulo, permiso_operacion.

Feature 000 — crea el esquema base de RBAC VACÍO de datos de negocio. Solo se
siembra `operacion` (enum de dominio fijo: crear/consultar/editar/eliminar).
La carga de roles, módulos, permisos y la tabla `usuario` son de la feature 001.

Revision ID: 0001
Revises:
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OPERACIONES = [
    {"clave": "crear", "nombre": "Crear"},
    {"clave": "consultar", "nombre": "Consultar"},
    {"clave": "editar", "nombre": "Editar"},
    {"clave": "eliminar", "nombre": "Eliminar"},
]


def upgrade() -> None:
    op.create_table(
        "rol",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("nombre", name="uq_rol_nombre"),
    )

    op.create_table(
        "modulo",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("clave", sa.String(length=60), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("clave", name="uq_modulo_clave"),
    )

    op.create_table(
        "operacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("clave", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=40), nullable=False),
        sa.UniqueConstraint("clave", name="uq_operacion_clave"),
    )

    op.create_table(
        "permiso_modulo",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("rol_id", sa.BigInteger(), nullable=False),
        sa.Column("modulo_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["rol_id"], ["rol.id"], name="fk_permiso_modulo_rol", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["modulo_id"], ["modulo.id"], name="fk_permiso_modulo_modulo", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("rol_id", "modulo_id", name="uq_permiso_modulo_rol_modulo"),
    )

    op.create_table(
        "permiso_operacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("rol_id", sa.BigInteger(), nullable=False),
        sa.Column("modulo_id", sa.BigInteger(), nullable=False),
        sa.Column("operacion_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rol_id"], ["rol.id"], name="fk_permiso_operacion_rol", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["modulo_id"], ["modulo.id"], name="fk_permiso_operacion_modulo", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["operacion_id"],
            ["operacion.id"],
            name="fk_permiso_operacion_operacion",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "rol_id", "modulo_id", "operacion_id", name="uq_permiso_operacion_rol_modulo_operacion"
        ),
    )

    # Siembra del enum de dominio fijo (no es dato de negocio).
    operacion = sa.table(
        "operacion",
        sa.column("clave", sa.String),
        sa.column("nombre", sa.String),
    )
    op.bulk_insert(operacion, _OPERACIONES)


def downgrade() -> None:
    op.drop_table("permiso_operacion")
    op.drop_table("permiso_modulo")
    op.drop_table("operacion")
    op.drop_table("modulo")
    op.drop_table("rol")
