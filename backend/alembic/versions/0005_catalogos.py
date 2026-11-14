"""Catálogos de configuración: medio_pago, categoria_gasto, canal_cita (feature 001).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MEDIOS_PAGO = [
    ("efectivo", "Efectivo"),
    ("transferencia", "Transferencia bancaria"),
    ("cheque", "Cheque"),
    ("tarjeta", "Tarjeta vía datáfono"),
]
_CANALES_CITA = [("correo_electronico", "Correo electrónico"), ("presencial", "Presencial")]


def upgrade() -> None:
    op.create_table(
        "medio_pago",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("clave", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "clave in ('efectivo','transferencia','cheque','tarjeta')", name="ck_medio_pago_clave"
        ),
        sa.UniqueConstraint("clave", name="uq_medio_pago_clave"),
    )

    op.create_table(
        "categoria_gasto",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("tipo", sa.String(length=24), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "tipo in ('local_operativos','personal','otros','mermas_perdidas')",
            name="ck_categoria_gasto_tipo",
        ),
        sa.UniqueConstraint("nombre", name="uq_categoria_gasto_nombre"),
    )

    op.create_table(
        "canal_cita",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("clave", sa.String(length=40), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("clave", name="uq_canal_cita_clave"),
    )

    op.bulk_insert(
        sa.table("medio_pago", sa.column("clave", sa.String), sa.column("nombre", sa.String)),
        [{"clave": c, "nombre": n} for c, n in _MEDIOS_PAGO],
    )
    op.bulk_insert(
        sa.table("canal_cita", sa.column("clave", sa.String), sa.column("nombre", sa.String)),
        [{"clave": c, "nombre": n} for c, n in _CANALES_CITA],
    )


def downgrade() -> None:
    op.drop_table("canal_cita")
    op.drop_table("categoria_gasto")
    op.drop_table("medio_pago")
