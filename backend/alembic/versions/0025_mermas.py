"""Feature 011 — mermas y pérdidas (spec decía `0016`; renumerada).

`merma` (reloj o pieza, exactamente un bien — CHECK), `autorizacion_baja`,
`documento_soporte_merma` (bucket `documentos`), `reclamo_merma` (proveedor/
seguro), `historial_estado_merma` (append-only, reutiliza la función
`cronos_append_only()` creada por 0023). Secuencia `merma_numero_seq` →
`M-000001`. Semilla: parámetro `umbral_merma_autorizacion` — la cuenta contable
de pérdida extraordinaria (`6.04`) y la regla `merma_confirmada` YA existen
desde `0023_contabilidad` (010 las sembró previendo esta feature); nada que
resembrar aquí.

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-10
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS merma_numero_seq START WITH 1")

    op.create_table(
        "merma",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("bien_tipo", sa.String(length=8), nullable=False),
        sa.Column("reloj_id", sa.BigInteger(), nullable=True),
        sa.Column("pieza_id", sa.BigInteger(), nullable=True),
        sa.Column("lote_id", sa.BigInteger(), nullable=True),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("causa", sa.String(length=20), nullable=False),
        sa.Column("fecha_evento", sa.Date(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("responsable_usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("costo_perdida", sa.Numeric(14, 2), nullable=False),
        sa.Column("estado", sa.String(length=24), nullable=False, server_default="en_evaluacion"),
        sa.Column("orden_trabajo_id", sa.BigInteger(), nullable=True),
        sa.Column("tecnico_id", sa.BigInteger(), nullable=True),
        sa.Column("transferencia_id", sa.BigInteger(), nullable=True),
        sa.Column("autorizacion_baja_id", sa.BigInteger(), nullable=True),
        sa.Column("asiento_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("numero", name="uq_merma_numero"),
        sa.CheckConstraint("bien_tipo in ('reloj','pieza')", name="ck_merma_bien_tipo"),
        sa.CheckConstraint(
            "causa in ('dano_tienda','dano_transito','robo_perdida','defecto_fabrica','dano_servicio','insumo_caducado')",
            name="ck_merma_causa",
        ),
        sa.CheckConstraint(
            "estado in ('en_evaluacion','dado_de_baja','en_reclamo_proveedor','en_reclamo_seguro','reparado_reingresado')",
            name="ck_merma_estado",
        ),
        sa.CheckConstraint("cantidad > 0", name="ck_merma_cantidad"),
        sa.CheckConstraint(
            "(reloj_id is not null)::int + (pieza_id is not null)::int = 1", name="ck_merma_un_bien"
        ),
        sa.ForeignKeyConstraint(["reloj_id"], ["reloj.id"], name="fk_merma_reloj", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pieza_id"], ["pieza.id"], name="fk_merma_pieza", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lote_id"], ["lote_pieza.id"], name="fk_merma_lote", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_merma_sucursal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["responsable_usuario_id"], ["usuario.id"], name="fk_merma_responsable", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnico.id"], name="fk_merma_tecnico", ondelete="SET NULL"),
    )
    op.create_index("ix_merma_sucursal", "merma", ["sucursal_id"])
    op.create_index("ix_merma_estado", "merma", ["estado"])
    op.create_index("ix_merma_reloj", "merma", ["reloj_id"])
    op.create_index("ix_merma_pieza", "merma", ["pieza_id"])

    op.create_table(
        "autorizacion_baja",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("merma_id", sa.BigInteger(), nullable=False),
        sa.Column("autorizador_usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("observacion", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["merma_id"], ["merma.id"], name="fk_autorizacion_baja_merma", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["autorizador_usuario_id"], ["usuario.id"], name="fk_autorizacion_baja_usuario", ondelete="RESTRICT"
        ),
    )
    op.create_foreign_key(
        "fk_merma_autorizacion_baja", "merma", "autorizacion_baja", ["autorizacion_baja_id"], ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "documento_soporte_merma",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("merma_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=12), nullable=False),
        sa.Column("objeto", sa.String(length=255), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("subido_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("tipo in ('acta','fotografia','denuncia','otro')", name="ck_documento_merma_tipo"),
        sa.ForeignKeyConstraint(["merma_id"], ["merma.id"], name="fk_documento_merma_merma", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subido_por"], ["usuario.id"], name="fk_documento_merma_usuario", ondelete="SET NULL"),
    )

    op.create_table(
        "reclamo_merma",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("merma_id", sa.BigInteger(), nullable=False),
        sa.Column("destino", sa.String(length=12), nullable=False),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=True),
        sa.Column("aseguradora", sa.String(length=120), nullable=True),
        sa.Column("estado", sa.String(length=24), nullable=False, server_default="abierto"),
        sa.Column("monto_recuperado", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("destino in ('proveedor','seguro')", name="ck_reclamo_merma_destino"),
        sa.ForeignKeyConstraint(["merma_id"], ["merma.id"], name="fk_reclamo_merma_merma", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_reclamo_merma_proveedor", ondelete="SET NULL"),
    )

    op.create_table(
        "historial_estado_merma",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("merma_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=24), nullable=False),
        sa.Column("actor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["merma_id"], ["merma.id"], name="fk_historial_merma_merma", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["actor_usuario_id"], ["usuario.id"], name="fk_historial_merma_usuario", ondelete="SET NULL"
        ),
    )
    # `cronos_append_only()` ya existe (0023) — solo agrega el trigger sobre esta tabla.
    op.execute(
        "CREATE TRIGGER trg_historial_estado_merma_append_only BEFORE UPDATE OR DELETE ON historial_estado_merma "
        "FOR EACH ROW EXECUTE FUNCTION cronos_append_only();"
    )

    # ---------------------------------------------------------------- semilla
    op.get_bind().execute(
        sa.text(
            "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
            "VALUES ('umbral_merma_autorizacion', 'monto', CAST(:v AS jsonb), 'global')"
        ),
        {"v": json.dumps(200)},
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_historial_estado_merma_append_only ON historial_estado_merma")
    op.execute("DELETE FROM parametro_configuracion WHERE clave = 'umbral_merma_autorizacion'")
    op.drop_table("historial_estado_merma")
    op.drop_table("reclamo_merma")
    op.drop_table("documento_soporte_merma")
    op.drop_constraint("fk_merma_autorizacion_baja", "merma", type_="foreignkey")
    op.drop_table("autorizacion_baja")
    op.drop_table("merma")
    op.execute("DROP SEQUENCE IF EXISTS merma_numero_seq")
