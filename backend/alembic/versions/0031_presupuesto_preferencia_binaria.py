"""Feature 008 — la preferencia de piezas por línea de presupuesto es binaria.

Feedback del usuario (2026-09-11): "el cliente [confirma] si usa las originales
o no... es o originales o no originales, no ambas". El CHECK (y el esquema) de
`presupuesto_linea_pieza.preferencia_cliente` admitía además `'mixto'` como
valor POR LÍNEA — no tiene sentido: una sola pieza no puede ser a la vez
original y no original. `mixto` en la especificación (FR-003c) describe el
presupuesto EN CONJUNTO cuando sus líneas difieren entre sí (algunas originales,
otras no), nunca la elección de una línea individual.

Revision ID: 0031
Revises: 0030
Create Date: 2026-09-11
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_presu_linea_preferencia", "presupuesto_linea_pieza", type_="check")
    op.create_check_constraint(
        "ck_presu_linea_preferencia",
        "presupuesto_linea_pieza",
        "preferencia_cliente is null or preferencia_cliente in ('original','no_original')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_presu_linea_preferencia", "presupuesto_linea_pieza", type_="check")
    op.create_check_constraint(
        "ck_presu_linea_preferencia",
        "presupuesto_linea_pieza",
        "preferencia_cliente is null or preferencia_cliente in ('original','no_original','mixto')",
    )
