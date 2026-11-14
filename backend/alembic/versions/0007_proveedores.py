"""Proveedores y órdenes de compra (feature 002).

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proveedor",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("razon_social", sa.String(length=200), nullable=False),
        sa.Column("nombre_comercial", sa.String(length=200), nullable=True),
        sa.Column("contacto_nombre", sa.String(length=160), nullable=True),
        sa.Column("telefono", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("ruc_nit", sa.String(length=20), nullable=True),
        sa.Column("certificacion_autorizada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("condiciones_pago", sa.String(length=255), nullable=True),
        sa.Column("plazo_entrega_dias", sa.Integer(), nullable=True),
        sa.Column("indicador_plazos_dias", sa.Numeric(6, 2), nullable=True),
        sa.Column("estado", sa.String(length=12), nullable=False, server_default="activo"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado in ('activo','inactivo')", name="ck_proveedor_estado"),
        sa.UniqueConstraint("ruc_nit", name="uq_proveedor_ruc_nit"),
    )
    op.create_index("ix_proveedor_razon_social", "proveedor", ["razon_social"])

    op.create_table(
        "proveedor_tipo",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=24), nullable=False),
        sa.CheckConstraint(
            "tipo in ('relojes','piezas_originales','piezas_no_originales','lubricantes','herramientas')",
            name="ck_proveedor_tipo_valor",
        ),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_proveedor_tipo_proveedor", ondelete="CASCADE"),
        sa.UniqueConstraint("proveedor_id", "tipo", name="uq_proveedor_tipo"),
    )

    op.create_table(
        "proveedor_documento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False, server_default="otro"),
        sa.Column("objeto", sa.String(length=255), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=True),
        sa.Column("subido_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo in ('certificado','ruc','contrato','otro')", name="ck_proveedor_documento_tipo"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_proveedor_documento_proveedor", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subido_por"], ["usuario.id"], name="fk_proveedor_documento_usuario", ondelete="SET NULL"),
    )

    op.create_table(
        "calificacion_proveedor",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=False),
        sa.Column("nota_plazos", sa.Numeric(2, 1), nullable=True),
        sa.Column("nota_calidad", sa.Numeric(2, 1), nullable=True),
        sa.Column("nota_soporte", sa.Numeric(2, 1), nullable=True),
        sa.Column("nota_agregada", sa.Numeric(2, 1), nullable=True),
        sa.Column("autor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_calificacion_proveedor", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["autor_usuario_id"], ["usuario.id"], name="fk_calificacion_autor", ondelete="SET NULL"),
    )
    op.create_index("ix_calificacion_proveedor", "calificacion_proveedor", ["proveedor_id", "creado_en"])

    op.create_table(
        "compra_programada",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_destino_id", sa.BigInteger(), nullable=False),
        sa.Column("frecuencia", sa.String(length=12), nullable=False),
        sa.Column("proxima_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="activa"),
        sa.Column("plantilla_lineas", postgresql.JSONB(), nullable=False),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("frecuencia in ('semanal','mensual','trimestral')", name="ck_compra_programada_frecuencia"),
        sa.CheckConstraint("estado in ('activa','pausada','cancelada')", name="ck_compra_programada_estado"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_compra_programada_proveedor", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sucursal_destino_id"], ["sucursal.id"], name="fk_compra_programada_sucursal", ondelete="RESTRICT"),
    )

    op.create_table(
        "orden_compra",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_destino_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=12), nullable=False, server_default="puntual"),
        sa.Column("compra_programada_id", sa.BigInteger(), nullable=True),
        sa.Column("estado", sa.String(length=14), nullable=False, server_default="borrador"),
        sa.Column("fecha_emision", sa.Date(), nullable=True),
        sa.Column("fecha_pactada", sa.Date(), nullable=True),
        sa.Column("importe_a_pagar", sa.Numeric(14, 2), nullable=True),
        sa.Column("condiciones_pago", sa.String(length=255), nullable=True),
        sa.Column("retencion_aplicable", postgresql.JSONB(), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo in ('puntual','programada')", name="ck_orden_compra_tipo"),
        sa.CheckConstraint(
            "estado in ('borrador','emitida','parcial','recibida','cancelada')", name="ck_orden_compra_estado"
        ),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_orden_compra_proveedor", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sucursal_destino_id"], ["sucursal.id"], name="fk_orden_compra_sucursal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["compra_programada_id"], ["compra_programada.id"], name="fk_orden_compra_programada", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_orden_compra_usuario", ondelete="SET NULL"),
    )
    op.create_index("ix_orden_compra_proveedor", "orden_compra", ["proveedor_id", "estado"])

    op.create_table(
        "linea_orden_compra",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_compra_id", sa.BigInteger(), nullable=False),
        sa.Column("item_tipo", sa.String(length=8), nullable=False),
        sa.Column("item_ref", sa.String(length=80), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=False),
        sa.Column("es_perecedero", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("item_tipo in ('reloj','pieza')", name="ck_linea_orden_item_tipo"),
        sa.CheckConstraint("cantidad > 0", name="ck_linea_orden_cantidad"),
        sa.ForeignKeyConstraint(
            ["orden_compra_id"], ["orden_compra.id"], name="fk_linea_orden_compra", ondelete="CASCADE"
        ),
    )

    op.create_table(
        "recepcion_compra",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_compra_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_real", sa.Date(), nullable=False),
        sa.Column("responsable_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("desfase_dias", sa.Integer(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["orden_compra_id"], ["orden_compra.id"], name="fk_recepcion_orden_compra", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["responsable_usuario_id"], ["usuario.id"], name="fk_recepcion_responsable", ondelete="SET NULL"
        ),
    )

    op.create_table(
        "recepcion_linea",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("recepcion_compra_id", sa.BigInteger(), nullable=False),
        sa.Column("linea_orden_compra_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad_recibida", sa.Integer(), nullable=False),
        sa.Column("lote", sa.String(length=60), nullable=True),
        sa.Column("fecha_caducidad", sa.Date(), nullable=True),
        sa.Column("sobre_entrega", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("cantidad_recibida > 0", name="ck_recepcion_linea_cantidad"),
        sa.ForeignKeyConstraint(
            ["recepcion_compra_id"], ["recepcion_compra.id"], name="fk_recepcion_linea_recepcion", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["linea_orden_compra_id"], ["linea_orden_compra.id"], name="fk_recepcion_linea_linea", ondelete="RESTRICT"
        ),
    )


def downgrade() -> None:
    op.drop_table("recepcion_linea")
    op.drop_table("recepcion_compra")
    op.drop_table("linea_orden_compra")
    op.drop_table("orden_compra")
    op.drop_table("compra_programada")
    op.drop_table("calificacion_proveedor")
    op.drop_table("proveedor_documento")
    op.drop_table("proveedor_tipo")
    op.drop_table("proveedor")
