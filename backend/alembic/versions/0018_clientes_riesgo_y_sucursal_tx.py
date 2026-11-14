"""Análisis de riesgo de abandono de clientes + parámetros (feature 006, ampliación).

Solo semilla de parámetros configurables (§9): umbrales del análisis de riesgo de
abandono. No crea tablas — el reporte se calcula sobre las transacciones que
aportan 008/009. La sucursal de cada transacción viaja en el DTO
`clientes.TransaccionCliente` (la poblan 008/009), no requiere columna aquí.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-10
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARAMETROS = [
    ("churn_piso_dias", "numero", 90),
    ("churn_factor_cadencia", "numero", 2),
    ("churn_min_transacciones", "numero", 3),
    ("churn_ventana_analisis_meses", "numero", 24),
]


def upgrade() -> None:
    bind = op.get_bind()
    for clave, tipo, valor in _PARAMETROS:
        bind.execute(
            sa.text(
                "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
                "VALUES (:clave, :tipo, CAST(:valor AS jsonb), 'global')"
            ),
            {"clave": clave, "tipo": tipo, "valor": json.dumps(valor)},
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM parametro_configuracion WHERE clave IN "
        "('churn_piso_dias','churn_factor_cadencia','churn_min_transacciones','churn_ventana_analisis_meses')"
    )
