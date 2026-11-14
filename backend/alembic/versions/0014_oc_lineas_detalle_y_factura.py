"""Detalle completo de las líneas de la orden de compra + datos de la factura del
proveedor en la recepción (feedback del usuario 2026-09-10, 3ª ronda).

- `linea_orden_compra`: `numero_serie` (reloj, opcional en la orden), `pieza_id`
  (elegir del catálogo), y para piezas nuevas `pieza_tipo`, `unidad_medida`,
  `marca_compatible`.
- `pieza`: `unidad_medida` (unidad, ml, g…) y `marca_compatible`.
- `recepcion_compra`: `numero_factura`, `numero_guia` del proveedor.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pieza", sa.Column("unidad_medida", sa.String(length=16), nullable=False, server_default="unidad"))
    op.add_column("pieza", sa.Column("marca_compatible", sa.String(length=255), nullable=True))

    op.add_column("linea_orden_compra", sa.Column("numero_serie", sa.String(length=80), nullable=True))
    op.add_column("linea_orden_compra", sa.Column("pieza_id", sa.BigInteger(), nullable=True))
    op.add_column("linea_orden_compra", sa.Column("pieza_tipo", sa.String(length=24), nullable=True))
    op.add_column("linea_orden_compra", sa.Column("unidad_medida", sa.String(length=16), nullable=True))
    op.add_column("linea_orden_compra", sa.Column("marca_compatible", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_linea_orden_pieza", "linea_orden_compra", "pieza", ["pieza_id"], ["id"], ondelete="SET NULL"
    )

    op.add_column("recepcion_compra", sa.Column("numero_factura", sa.String(length=60), nullable=True))
    op.add_column("recepcion_compra", sa.Column("numero_guia", sa.String(length=60), nullable=True))


def downgrade() -> None:
    op.drop_column("recepcion_compra", "numero_guia")
    op.drop_column("recepcion_compra", "numero_factura")
    op.drop_constraint("fk_linea_orden_pieza", "linea_orden_compra", type_="foreignkey")
    op.drop_column("linea_orden_compra", "marca_compatible")
    op.drop_column("linea_orden_compra", "unidad_medida")
    op.drop_column("linea_orden_compra", "pieza_tipo")
    op.drop_column("linea_orden_compra", "pieza_id")
    op.drop_column("linea_orden_compra", "numero_serie")
    op.drop_column("pieza", "marca_compatible")
    op.drop_column("pieza", "unidad_medida")
