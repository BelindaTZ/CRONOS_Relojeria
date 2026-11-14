"""Nota libre por línea de la orden de compra, independiente de la descripción.

Para piezas nuevas el usuario quiere capturar por separado la *descripción de la
pieza* (que pasa a ser su nombre en el catálogo al recibir) y *observaciones*
libres del pedido ("urgente", "para cliente X", "traer certificado"…).
`descripcion` ya cumple ese doble rol para relojes; esta columna lo separa.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "linea_orden_compra",
        sa.Column("observaciones", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("linea_orden_compra", "observaciones")
