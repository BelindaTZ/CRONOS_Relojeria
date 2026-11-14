"""Gestión de citas (feature 007).

- `cita` — registro manual por el personal (§4.1): cliente (ficha de 006),
  sucursal, canal de origen (catálogo de 001), motivo, fecha preferida/confirmada,
  estado (pendiente → confirmada → cancelada|atendida), vínculo opcional a la
  venta (009) o la orden de trabajo (008) generada.
- `historial_estado_cita` — bitácora append-only de cambios de estado.

Reutiliza `cliente` (006), `sucursal`, `canal_cita`, `usuario` (001). El módulo
RBAC `citas` ya se sembró en `0003`.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-10
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cita",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("canal_cita_id", sa.BigInteger(), nullable=False),
        sa.Column("motivo", sa.String(length=16), nullable=False),
        sa.Column("fecha_preferida", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_confirmada", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(length=12), nullable=False, server_default="pendiente"),
        sa.Column("motivo_cancelacion", sa.String(length=255), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("venta_id", sa.BigInteger(), nullable=True),           # 009 (aún no existe)
        sa.Column("orden_trabajo_id", sa.BigInteger(), nullable=True),   # 008 (aún no existe)
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("motivo in ('compra','servicio_tecnico','consulta')", name="ck_cita_motivo"),
        sa.CheckConstraint(
            "estado in ('pendiente','confirmada','cancelada','atendida')", name="ck_cita_estado"
        ),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_cita_cliente", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_cita_sucursal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["canal_cita_id"], ["canal_cita.id"], name="fk_cita_canal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_cita_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_cita_sucursal_fecha", "cita", ["sucursal_id", "fecha_preferida"])
    op.create_index("ix_cita_estado", "cita", ["estado"])
    op.create_index("ix_cita_cliente", "cita", ["cliente_id"])

    op.create_table(
        "historial_estado_cita",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("cita_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=12), nullable=False),
        sa.Column("actor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["cita_id"], ["cita.id"], name="fk_hist_cita_cita", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_usuario_id"], ["usuario.id"], name="fk_hist_cita_actor", ondelete="SET NULL"),
    )
    op.create_index("ix_hist_estado_cita", "historial_estado_cita", ["cita_id", "timestamp"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION cronos_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% es append-only (solo INSERT)', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_historial_estado_cita_append_only
        BEFORE UPDATE OR DELETE ON historial_estado_cita
        FOR EACH ROW EXECUTE FUNCTION cronos_append_only();
        """
    )

    op.get_bind().execute(
        sa.text(
            "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
            "VALUES ('citas_ventana_solape_min', 'numero', CAST(:v AS jsonb), 'global')"
        ),
        {"v": json.dumps(30)},
    )


def downgrade() -> None:
    op.execute("DELETE FROM parametro_configuracion WHERE clave = 'citas_ventana_solape_min'")
    op.execute("DROP TRIGGER IF EXISTS trg_historial_estado_cita_append_only ON historial_estado_cita")
    op.drop_table("historial_estado_cita")
    op.drop_table("cita")
