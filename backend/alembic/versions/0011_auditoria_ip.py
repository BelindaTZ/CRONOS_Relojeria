"""Auditoría: columna `ip_origen` (feedback del usuario — registrar desde qué IP
se hizo cada acción / ingreso).

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("registro_auditoria", sa.Column("ip_origen", sa.String(length=45), nullable=True))


def downgrade() -> None:
    op.drop_column("registro_auditoria", "ip_origen")
