"""Ajustes al flujo principal del negocio (feedback del usuario, 2026-09-11):

- `canal_cita` gana 3 canales de redes sociales (Instagram, TikTok, Facebook) —
  Esp. §4.1 solo contemplaba correo electrónico y presencial.
- `horario_sucursal`: horario de atención por sucursal y día de semana — no
  existía ningún campo de horario; lo necesita el correo de "listo para
  retiro" del flujo de servicio técnico.
- `orden_compra.urgente`: marca una orden puntual como urgente (p. ej. una
  pieza faltante detectada durante una reparación en curso).
- Parámetro `costo_traslado_venta`: costo interno estimado de un traslado
  entre sucursales solicitado específicamente para una venta (vs. un traslado
  rutinario de balanceo de stock) — ver recomendación de negocio en
  CONVENCIONES.md §24.

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-11
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANALES_REDES = [
    ("instagram", "Instagram"),
    ("tiktok", "TikTok"),
    ("facebook", "Facebook"),
]


def upgrade() -> None:
    canal_cita = sa.table("canal_cita", sa.column("clave", sa.String), sa.column("nombre", sa.String))
    op.bulk_insert(canal_cita, [{"clave": c, "nombre": n} for c, n in _CANALES_REDES])

    op.create_table(
        "horario_sucursal",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("cerrado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("hora_apertura", sa.Time(), nullable=True),
        sa.Column("hora_cierre", sa.Time(), nullable=True),
        sa.CheckConstraint("dia_semana between 0 and 6", name="ck_horario_sucursal_dia"),
        sa.UniqueConstraint("sucursal_id", "dia_semana", name="uq_horario_sucursal_dia"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_horario_sucursal_sucursal", ondelete="CASCADE"),
    )

    op.add_column("orden_compra", sa.Column("urgente", sa.Boolean(), nullable=False, server_default="false"))

    op.get_bind().execute(
        sa.text(
            "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
            "VALUES ('costo_traslado_venta', 'monto', CAST(:v AS jsonb), 'global')"
        ),
        {"v": json.dumps(15)},
    )


def downgrade() -> None:
    op.execute("DELETE FROM parametro_configuracion WHERE clave = 'costo_traslado_venta'")
    op.drop_column("orden_compra", "urgente")
    op.drop_table("horario_sucursal")
    op.execute(
        "DELETE FROM canal_cita WHERE clave IN (" + ",".join(f"'{c}'" for c, _ in _CANALES_REDES) + ")"
    )
