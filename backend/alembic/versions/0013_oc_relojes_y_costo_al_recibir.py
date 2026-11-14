"""Órdenes de compra (feedback del usuario 2026-09-10):

- El pedido de un reloj se especifica con marca / referencia / calibre / año, no
  con un solo texto "referencia". `descripcion` pasa a ser especificaciones/notas.
- El costo lo fija el proveedor: `linea_orden_compra.costo_unitario` pasa a
  nullable ("estimado"); el costo real por línea se registra en la recepción
  (`recepcion_linea.costo_unitario`).
- "Distribuidor autorizado" se ata a marcas concretas: `proveedor_marca_autorizada`.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- línea de orden: campos estructurados del reloj + costo estimado opcional ---
    op.add_column("linea_orden_compra", sa.Column("marca", sa.String(length=120), nullable=True))
    op.add_column("linea_orden_compra", sa.Column("calibre_codigo", sa.String(length=60), nullable=True))
    op.add_column("linea_orden_compra", sa.Column("anio", sa.Integer(), nullable=True))
    op.alter_column("linea_orden_compra", "costo_unitario", existing_type=sa.Numeric(14, 2), nullable=True)

    # --- costo real por línea en la recepción ---
    op.add_column("recepcion_linea", sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=True))

    # --- proveedor: marcas para las que es distribuidor autorizado ---
    op.create_table(
        "proveedor_marca_autorizada",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=False),
        sa.Column("marca_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["proveedor_id"], ["proveedor.id"], name="fk_prov_marca_aut_proveedor", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["marca_id"], ["marca_reloj.id"], name="fk_prov_marca_aut_marca", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("proveedor_id", "marca_id", name="uq_proveedor_marca_autorizada"),
    )


def downgrade() -> None:
    op.drop_table("proveedor_marca_autorizada")
    op.drop_column("recepcion_linea", "costo_unitario")
    op.alter_column("linea_orden_compra", "costo_unitario", existing_type=sa.Numeric(14, 2), nullable=False)
    op.drop_column("linea_orden_compra", "anio")
    op.drop_column("linea_orden_compra", "calibre_codigo")
    op.drop_column("linea_orden_compra", "marca")
