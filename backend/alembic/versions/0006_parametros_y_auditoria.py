"""parametro_configuracion (historial por inserción) + registro_auditoria (feature 001).

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parametro_configuracion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("clave", sa.String(length=80), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("valor", postgresql.JSONB(), nullable=False),
        sa.Column("ambito_tipo", sa.String(length=16), nullable=False, server_default="global"),
        sa.Column("ambito_ref", sa.String(length=80), nullable=True),
        sa.Column("vigente_desde", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tipo in ('numero','porcentaje','monto','json','texto')", name="ck_parametro_tipo"
        ),
        sa.CheckConstraint(
            "ambito_tipo in ('global','sucursal','marca','producto','tipo_servicio')",
            name="ck_parametro_ambito_tipo",
        ),
        sa.CheckConstraint(
            "(ambito_tipo = 'global') = (ambito_ref IS NULL)", name="ck_parametro_ambito_ref"
        ),
        sa.ForeignKeyConstraint(
            ["creado_por"], ["usuario.id"], name="fk_parametro_creado_por", ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_parametro_clave_ambito",
        "parametro_configuracion",
        ["clave", "ambito_tipo", "ambito_ref", "vigente_desde"],
    )

    op.create_table(
        "registro_auditoria",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("actor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("accion", sa.String(length=40), nullable=False),
        sa.Column("entidad", sa.String(length=60), nullable=False),
        sa.Column("entidad_id", sa.String(length=40), nullable=True),
        sa.Column("antes", postgresql.JSONB(), nullable=True),
        sa.Column("despues", postgresql.JSONB(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_usuario_id"], ["usuario.id"], name="fk_auditoria_actor", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_auditoria_entidad", "registro_auditoria", ["entidad", "entidad_id"])
    op.create_index("ix_auditoria_actor", "registro_auditoria", ["actor_usuario_id"])
    op.create_index("ix_auditoria_creado_en", "registro_auditoria", ["creado_en"])

    # Inmutabilidad de la auditoría (SEC013): sin UPDATE ni DELETE a nivel de DB.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cronos_auditoria_inmutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'registro_auditoria es inmutable (append-only)';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_auditoria_inmutable
        BEFORE UPDATE OR DELETE ON registro_auditoria
        FOR EACH ROW EXECUTE FUNCTION cronos_auditoria_inmutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_auditoria_inmutable ON registro_auditoria")
    op.execute("DROP FUNCTION IF EXISTS cronos_auditoria_inmutable()")
    op.drop_table("registro_auditoria")
    op.drop_table("parametro_configuracion")
