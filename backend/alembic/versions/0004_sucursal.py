"""sucursal + usuario_sucursal (feature 001).

Se crea aquí (no en 0002) porque `usuario_sucursal` referencia a `sucursal`.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sucursal",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("direccion", sa.String(length=255), nullable=True),
        sa.Column("responsable_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("estado", sa.String(length=12), nullable=False, server_default="activa"),
        sa.Column("motivo_inactivacion", sa.String(length=500), nullable=True),
        sa.Column("inactivada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado in ('activa','inactiva')", name="ck_sucursal_estado"),
        sa.CheckConstraint(
            "estado <> 'inactiva' OR motivo_inactivacion IS NOT NULL",
            name="ck_sucursal_motivo_si_inactiva",
        ),
        sa.ForeignKeyConstraint(
            ["responsable_usuario_id"], ["usuario.id"], name="fk_sucursal_responsable", ondelete="SET NULL"
        ),
        sa.UniqueConstraint("nombre", name="uq_sucursal_nombre"),
    )

    op.create_table(
        "usuario_sucursal",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name="fk_usuario_sucursal_usuario", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_id"], ["sucursal.id"], name="fk_usuario_sucursal_sucursal", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("usuario_id", "sucursal_id", name="uq_usuario_sucursal"),
    )


def downgrade() -> None:
    op.drop_table("usuario_sucursal")
    op.drop_table("sucursal")
