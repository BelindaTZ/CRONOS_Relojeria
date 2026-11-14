"""Traslados de inventario entre sucursales (feature 004).

- `transferencia` — máquina de estados en_preparacion → en_transito → recibida
  (o parcial); en_preparacion|en_transito → cancelada.
- `linea_transferencia` — unidad de reloj (por id) o pieza + cantidad.
- `discrepancia_transferencia` — faltante en recepción, derivable a merma (011).

Reutiliza `sucursal`, `usuario` (001); `reloj`, `pieza` (003).

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transferencia",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("sucursal_origen_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_destino_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="en_preparacion"),
        sa.Column("motivo", sa.String(length=500), nullable=False),
        sa.Column("fecha_envio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_recepcion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsable_envio_id", sa.BigInteger(), nullable=True),
        sa.Column("responsable_recepcion_id", sa.BigInteger(), nullable=True),
        sa.Column("motivo_cancelacion", sa.String(length=500), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sucursal_origen_id <> sucursal_destino_id", name="ck_transferencia_origen_destino"),
        sa.CheckConstraint(
            "estado in ('en_preparacion','en_transito','recibida','parcial','cancelada')",
            name="ck_transferencia_estado",
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_origen_id"], ["sucursal.id"], name="fk_transferencia_origen", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_destino_id"], ["sucursal.id"], name="fk_transferencia_destino", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["responsable_envio_id"], ["usuario.id"], name="fk_transferencia_resp_envio", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["responsable_recepcion_id"], ["usuario.id"], name="fk_transferencia_resp_recep", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["creado_por"], ["usuario.id"], name="fk_transferencia_creado_por", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_transferencia_origen", "transferencia", ["sucursal_origen_id", "estado"])
    op.create_index("ix_transferencia_destino", "transferencia", ["sucursal_destino_id", "estado"])

    op.create_table(
        "linea_transferencia",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("transferencia_id", sa.BigInteger(), nullable=False),
        sa.Column("item_tipo", sa.String(length=8), nullable=False),
        sa.Column("reloj_id", sa.BigInteger(), nullable=True),
        sa.Column("pieza_id", sa.BigInteger(), nullable=True),
        sa.Column("cantidad_enviada", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cantidad_recibida", sa.Integer(), nullable=True),
        sa.CheckConstraint("item_tipo in ('reloj','pieza')", name="ck_linea_transferencia_item_tipo"),
        sa.CheckConstraint("cantidad_enviada > 0", name="ck_linea_transferencia_cantidad"),
        sa.CheckConstraint(
            "(item_tipo = 'reloj' and reloj_id is not null and pieza_id is null) or "
            "(item_tipo = 'pieza' and pieza_id is not null and reloj_id is null)",
            name="ck_linea_transferencia_item_ref",
        ),
        sa.ForeignKeyConstraint(
            ["transferencia_id"], ["transferencia.id"], name="fk_linea_transferencia_transferencia", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reloj_id"], ["reloj.id"], name="fk_linea_transferencia_reloj", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pieza_id"], ["pieza.id"], name="fk_linea_transferencia_pieza", ondelete="RESTRICT"),
    )
    op.create_index("ix_linea_transferencia_transferencia", "linea_transferencia", ["transferencia_id"])
    op.create_index("ix_linea_transferencia_reloj", "linea_transferencia", ["reloj_id"])

    op.create_table(
        "discrepancia_transferencia",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("linea_transferencia_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad_faltante", sa.Integer(), nullable=False),
        sa.Column("merma_id", sa.BigInteger(), nullable=True),
        sa.Column("resuelta", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("cantidad_faltante > 0", name="ck_discrepancia_cantidad"),
        sa.ForeignKeyConstraint(
            ["linea_transferencia_id"], ["linea_transferencia.id"],
            name="fk_discrepancia_linea", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_discrepancia_linea", "discrepancia_transferencia", ["linea_transferencia_id"])


def downgrade() -> None:
    op.drop_table("discrepancia_transferencia")
    op.drop_table("linea_transferencia")
    op.drop_table("transferencia")
