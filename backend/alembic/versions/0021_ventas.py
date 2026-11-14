"""Ventas, comprobantes y garantías (feature 009).

- **`orden_venta`** (§2.2, Principio II) + `linea_venta` (reloj por N.º de serie o
  pieza suelta) + `garantia_venta` (fábrica / tienda) + `comprobante_venta`
  (clave en `comprobantes-venta`) + `anulacion_venta`.
- **`cuenta_por_cobrar`** — la crea 009 al confirmar una venta a crédito (y la
  entrega a crédito de una OT de 008); el subledger / aging lo maneja 010.

Reutiliza `reloj`, `pieza` (003); `cliente`, `descuento`, `cupon`,
`autorizacion_margen_minimo` (006); `cita` (007); `medio_pago`, `usuario` (001);
la tabla `pago` de `shared/pagos` con `documento_tipo='venta'` (008).

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-10
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS orden_venta_numero_seq START WITH 1")

    op.create_table(
        "orden_venta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("vendedor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("cita_id", sa.BigInteger(), nullable=True),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="borrador"),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("margen_venta", sa.Numeric(14, 2), nullable=True),
        sa.Column("descuento_aplicado", postgresql.JSONB(), nullable=True),
        sa.Column("autorizacion_margen_minimo_id", sa.BigInteger(), nullable=True),
        sa.Column("identificacion_fiscal", sa.String(length=20), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado in ('borrador','confirmada','anulada')", name="ck_orden_venta_estado"),
        sa.UniqueConstraint("numero", name="uq_orden_venta_numero"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_ov_cliente", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_ov_sucursal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendedor_usuario_id"], ["usuario.id"], name="fk_ov_vendedor", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cita_id"], ["cita.id"], name="fk_ov_cita", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["autorizacion_margen_minimo_id"], ["autorizacion_margen_minimo.id"],
            name="fk_ov_autorizacion", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_ov_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_orden_venta_estado", "orden_venta", ["estado"])
    op.create_index("ix_orden_venta_cliente", "orden_venta", ["cliente_id"])
    op.create_index("ix_orden_venta_sucursal_fecha", "orden_venta", ["sucursal_id", "fecha"])

    op.create_table(
        "linea_venta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_venta_id", sa.BigInteger(), nullable=False),
        sa.Column("item_tipo", sa.String(length=8), nullable=False),
        sa.Column("reloj_id", sa.BigInteger(), nullable=True),
        sa.Column("pieza_id", sa.BigInteger(), nullable=True),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("precio_lista", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("precio_final", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("costo", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("margen", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.CheckConstraint("item_tipo in ('reloj','pieza')", name="ck_linea_venta_tipo"),
        sa.CheckConstraint("cantidad > 0", name="ck_linea_venta_cantidad"),
        sa.ForeignKeyConstraint(["orden_venta_id"], ["orden_venta.id"], name="fk_lv_orden", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reloj_id"], ["reloj.id"], name="fk_lv_reloj", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pieza_id"], ["pieza.id"], name="fk_lv_pieza", ondelete="RESTRICT"),
    )
    op.create_index("ix_linea_venta_orden", "linea_venta", ["orden_venta_id"])

    op.create_table(
        "garantia_venta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_venta_id", sa.BigInteger(), nullable=False),
        sa.Column("linea_venta_id", sa.BigInteger(), nullable=True),
        sa.Column("tipo", sa.String(length=8), nullable=False),
        sa.Column("periodo_dias", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("cobertura", sa.String(length=255), nullable=True),
        sa.CheckConstraint("tipo in ('fabrica','tienda')", name="ck_garantia_venta_tipo"),
        sa.ForeignKeyConstraint(["orden_venta_id"], ["orden_venta.id"], name="fk_gv_orden", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linea_venta_id"], ["linea_venta.id"], name="fk_gv_linea", ondelete="CASCADE"),
    )
    op.create_index("ix_garantia_venta_orden", "garantia_venta", ["orden_venta_id"])

    op.create_table(
        "comprobante_venta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_venta_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("objeto", sa.String(length=255), nullable=False),
        sa.Column("numero_serie_vinculado", sa.String(length=80), nullable=True),
        sa.Column("generado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tipo in ('comprobante','certificado_garantia_autenticidad')", name="ck_comprobante_venta_tipo"
        ),
        sa.ForeignKeyConstraint(["orden_venta_id"], ["orden_venta.id"], name="fk_cv_orden", ondelete="CASCADE"),
    )
    op.create_index("ix_comprobante_venta_orden", "comprobante_venta", ["orden_venta_id"])

    op.create_table(
        "anulacion_venta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_venta_id", sa.BigInteger(), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("actor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reversas", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["orden_venta_id"], ["orden_venta.id"], name="fk_av_orden", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_usuario_id"], ["usuario.id"], name="fk_av_actor", ondelete="SET NULL"),
    )

    op.create_table(
        "cuenta_por_cobrar",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("origen_tipo", sa.String(length=16), nullable=False),
        sa.Column("origen_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("monto_original", sa.Numeric(14, 2), nullable=False),
        sa.Column("saldo", sa.Numeric(14, 2), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="pendiente"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("origen_tipo in ('venta','orden_trabajo')", name="ck_cxc_origen_tipo"),
        sa.CheckConstraint("estado in ('pendiente','saldada','anulada')", name="ck_cxc_estado"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_cxc_cliente", ondelete="RESTRICT"),
    )
    op.create_index("ix_cxc_cliente_estado", "cuenta_por_cobrar", ["cliente_id", "estado"])
    op.create_index("ix_cxc_origen", "cuenta_por_cobrar", ["origen_tipo", "origen_id"])

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
            "VALUES ('garantia_fabrica_dias_default', 'numero', CAST(:v AS jsonb), 'global')"
        ),
        {"v": json.dumps(730)},
    )


def downgrade() -> None:
    op.execute("DELETE FROM parametro_configuracion WHERE clave = 'garantia_fabrica_dias_default'")
    op.drop_table("cuenta_por_cobrar")
    op.drop_table("anulacion_venta")
    op.drop_table("comprobante_venta")
    op.drop_table("garantia_venta")
    op.drop_table("linea_venta")
    op.drop_table("orden_venta")
    op.execute("DROP SEQUENCE IF EXISTS orden_venta_numero_seq")
