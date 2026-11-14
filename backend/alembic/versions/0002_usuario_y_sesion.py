"""usuario, usuario_rol, refresh_token, solicitud_restablecimiento (feature 001).

`usuario_sucursal` se crea en 0004 junto a `sucursal` (evita la inversión de
dependencia: `usuario_sucursal` referencia a `sucursal`, que no existe hasta 0004).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("identificacion", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("foto_perfil_objeto", sa.String(length=255), nullable=True),
        sa.Column("estado", sa.String(length=12), nullable=False, server_default="activo"),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado in ('activo','inactivo')", name="ck_usuario_estado"),
        sa.UniqueConstraint("identificacion", name="uq_usuario_identificacion"),
        sa.UniqueConstraint("email", name="uq_usuario_email"),
    )

    op.create_table(
        "usuario_rol",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("rol_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name="fk_usuario_rol_usuario", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rol_id"], ["rol.id"], name="fk_usuario_rol_rol", ondelete="CASCADE"),
        sa.UniqueConstraint("usuario_id", "rol_id", name="uq_usuario_rol"),
    )

    op.create_table(
        "refresh_token",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name="fk_refresh_token_usuario", ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_token_hash"),
    )
    op.create_index("ix_refresh_token_usuario", "refresh_token", ["usuario_id"])

    op.create_table(
        "solicitud_restablecimiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("password_temporal_hash", sa.String(length=255), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name="fk_solicitud_restablecimiento_usuario", ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_solicitud_restablecimiento_usuario", "solicitud_restablecimiento", ["usuario_id"]
    )


def downgrade() -> None:
    op.drop_table("solicitud_restablecimiento")
    op.drop_table("refresh_token")
    op.drop_table("usuario_rol")
    op.drop_table("usuario")
