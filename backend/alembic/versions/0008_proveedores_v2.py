"""Feature 002 v2 (decisiones del usuario 2026-09-10):

- `orden_compra`: nuevo estado `confirmada` (rol alto marca que el proveedor
  aceptó el pedido según lo acordado por otro canal) entre `emitida` y la recepción.
- `condicion_pago`: catálogo maestro editable; `proveedor.condicion_pago_id` FK.
  Se conserva `proveedor.condiciones_pago` (texto) como campo legado, ya no se usa.
- `medio_pago`: se retira el CHECK de claves fijas (se pueden agregar/inactivar,
  nunca borrar los que estén en uso).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONDICIONES = [
    ("Contado", 0),
    ("15 días", 15),
    ("30 días", 30),
    ("45 días", 45),
    ("60 días", 60),
    ("50% anticipo, 50% contra entrega", 0),
]


def upgrade() -> None:
    # --- orden_compra: añadir 'confirmada' al CHECK de estado ---
    op.drop_constraint("ck_orden_compra_estado", "orden_compra", type_="check")
    op.create_check_constraint(
        "ck_orden_compra_estado",
        "orden_compra",
        "estado in ('borrador','emitida','confirmada','parcial','recibida','cancelada')",
    )
    op.add_column(
        "orden_compra",
        sa.Column("fecha_confirmacion", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orden_compra",
        sa.Column("confirmada_por", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orden_compra_confirmada_por", "orden_compra", "usuario", ["confirmada_por"], ["id"], ondelete="SET NULL"
    )

    # --- condicion_pago (catálogo maestro) ---
    op.create_table(
        "condicion_pago",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("dias_credito", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("nombre", name="uq_condicion_pago_nombre"),
    )
    op.bulk_insert(
        sa.table(
            "condicion_pago",
            sa.column("nombre", sa.String),
            sa.column("dias_credito", sa.Integer),
        ),
        [{"nombre": n, "dias_credito": d} for n, d in _CONDICIONES],
    )
    op.add_column("proveedor", sa.Column("condicion_pago_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_proveedor_condicion_pago", "proveedor", "condicion_pago", ["condicion_pago_id"], ["id"], ondelete="SET NULL"
    )

    # --- medio_pago: quitar el CHECK de claves fijas ---
    op.drop_constraint("ck_medio_pago_clave", "medio_pago", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_medio_pago_clave",
        "medio_pago",
        "clave in ('efectivo','transferencia','cheque','tarjeta')",
    )
    op.drop_constraint("fk_proveedor_condicion_pago", "proveedor", type_="foreignkey")
    op.drop_column("proveedor", "condicion_pago_id")
    op.drop_table("condicion_pago")

    op.drop_constraint("fk_orden_compra_confirmada_por", "orden_compra", type_="foreignkey")
    op.drop_column("orden_compra", "confirmada_por")
    op.drop_column("orden_compra", "fecha_confirmacion")
    op.drop_constraint("ck_orden_compra_estado", "orden_compra", type_="check")
    op.create_check_constraint(
        "ck_orden_compra_estado",
        "orden_compra",
        "estado in ('borrador','emitida','parcial','recibida','cancelada')",
    )
