"""Inventario de relojes y piezas (feature 003).

- `calibre` — catálogo básico del movimiento (008 añade la ficha de lubricación).
- `reloj` — unidad física, número de serie único, ligada opcionalmente a una
  línea de recepción de compra (002).
- `foto_reloj` / `documento_reloj` — objetos en `reloj-imagenes` / `documentos`.
- `evento_serie` — historial INALTERABLE por número de serie (solo INSERT).
- `pieza` / `pieza_calibre` / `stock_pieza` — repuestos con stock por sucursal
  (invariante `stock_actual >= 0`).
- `movimiento_stock_pieza` — libro de movimientos APPEND-ONLY.
- `lote_pieza` — lote y caducidad de insumos perecederos (FEFO).
- `alerta_stock` — alertas materializadas (no bloquean).

Parámetros sembrados: `stock_maximo_modelo`, `umbral_reposicion_relojes`,
`umbral_reposicion_piezas`, `umbral_caducidad_dias`.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARAMETROS = [
    ("stock_maximo_modelo", 12),
    ("umbral_reposicion_relojes", 1),
    ("umbral_reposicion_piezas", 0),
    ("umbral_caducidad_dias", 30),
]


def upgrade() -> None:
    op.create_table(
        "calibre",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("codigo", sa.String(length=60), nullable=False),
        sa.Column("marca", sa.String(length=80), nullable=True),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_calibre_codigo"),
    )

    op.create_table(
        "reloj",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("numero_serie", sa.String(length=80), nullable=False),
        sa.Column("marca", sa.String(length=80), nullable=False),
        sa.Column("referencia", sa.String(length=120), nullable=False),
        sa.Column("calibre_id", sa.BigInteger(), nullable=True),
        sa.Column("anio_fabricacion", sa.Integer(), nullable=True),
        sa.Column("material_caja", sa.String(length=120), nullable=True),
        sa.Column("material_brazalete", sa.String(length=120), nullable=True),
        sa.Column("color_esfera", sa.String(length=80), nullable=True),
        sa.Column("tipo_cristal", sa.String(length=40), nullable=True),
        sa.Column("resistencia_agua", sa.String(length=40), nullable=True),
        sa.Column("estado_producto", sa.String(length=10), nullable=False, server_default="nuevo"),
        sa.Column("costo_adquisicion", sa.Numeric(14, 2), nullable=True),
        sa.Column("precio_venta", sa.Numeric(14, 2), nullable=True),
        sa.Column("fecha_ingreso", sa.Date(), nullable=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=True),
        sa.Column("recepcion_linea_id", sa.BigInteger(), nullable=True),
        sa.Column("full_set", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("full_set_detalle", sa.String(length=255), nullable=True),
        sa.Column("sucursal_actual_id", sa.BigInteger(), nullable=True),
        sa.Column("disponibilidad", sa.String(length=14), nullable=False, server_default="disponible"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tipo_cristal is null or tipo_cristal in ('zafiro','mineral','acrilico','otro')",
            name="ck_reloj_tipo_cristal",
        ),
        sa.CheckConstraint("estado_producto in ('nuevo','usado')", name="ck_reloj_estado_producto"),
        sa.CheckConstraint(
            "disponibilidad in ('disponible','reservado','en_transito','vendido','en_servicio','dado_de_baja')",
            name="ck_reloj_disponibilidad",
        ),
        sa.ForeignKeyConstraint(["calibre_id"], ["calibre.id"], name="fk_reloj_calibre", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_reloj_proveedor", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["recepcion_linea_id"], ["linea_orden_compra.id"], name="fk_reloj_recepcion_linea", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_actual_id"], ["sucursal.id"], name="fk_reloj_sucursal", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("numero_serie", name="uq_reloj_numero_serie"),
    )
    op.create_index("ix_reloj_marca_ref", "reloj", ["marca", "referencia"])
    op.create_index("ix_reloj_disponibilidad", "reloj", ["disponibilidad"])
    op.create_index("ix_reloj_sucursal", "reloj", ["sucursal_actual_id"])

    op.create_table(
        "foto_reloj",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("reloj_id", sa.BigInteger(), nullable=False),
        sa.Column("objeto", sa.String(length=255), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reloj_id"], ["reloj.id"], name="fk_foto_reloj_reloj", ondelete="CASCADE"),
    )

    op.create_table(
        "documento_reloj",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("reloj_id", sa.BigInteger(), nullable=False),
        sa.Column("objeto", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False, server_default="otro"),
        sa.Column("nombre", sa.String(length=200), nullable=True),
        sa.Column("subido_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tipo in ('papeles_full_set','factura_compra','otro')", name="ck_documento_reloj_tipo"
        ),
        sa.ForeignKeyConstraint(["reloj_id"], ["reloj.id"], name="fk_documento_reloj_reloj", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subido_por"], ["usuario.id"], name="fk_documento_reloj_usuario", ondelete="SET NULL"
        ),
    )

    op.create_table(
        "evento_serie",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("numero_serie", sa.String(length=80), nullable=False),
        sa.Column("reloj_id", sa.BigInteger(), nullable=True),
        sa.Column("tipo", sa.String(length=14), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("documento_tipo", sa.String(length=30), nullable=True),
        sa.Column("documento_id", sa.BigInteger(), nullable=True),
        sa.Column("detalle", postgresql.JSONB(), nullable=True),
        sa.Column("actor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tipo in ('ingreso','venta','servicio','transferencia','baja','reingreso','correccion')",
            name="ck_evento_serie_tipo",
        ),
        sa.ForeignKeyConstraint(["reloj_id"], ["reloj.id"], name="fk_evento_serie_reloj", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["actor_usuario_id"], ["usuario.id"], name="fk_evento_serie_actor", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_evento_serie_numero", "evento_serie", ["numero_serie", "fecha"])

    op.create_table(
        "pieza",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("codigo", sa.String(length=60), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=24), nullable=False, server_default="original"),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=True),
        sa.Column("costo_adquisicion", sa.Numeric(14, 2), nullable=True),
        sa.Column("precio_venta_suelta", sa.Numeric(14, 2), nullable=True),
        sa.Column("stock_minimo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("perecedera", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tipo in ('original','no_original_equivalente')", name="ck_pieza_tipo"
        ),
        sa.CheckConstraint("stock_minimo >= 0", name="ck_pieza_stock_minimo"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_pieza_proveedor", ondelete="SET NULL"),
        sa.UniqueConstraint("codigo", name="uq_pieza_codigo"),
    )
    op.create_index("ix_pieza_descripcion", "pieza", ["descripcion"])

    op.create_table(
        "pieza_calibre",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("pieza_id", sa.BigInteger(), nullable=False),
        sa.Column("calibre_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["pieza_id"], ["pieza.id"], name="fk_pieza_calibre_pieza", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["calibre_id"], ["calibre.id"], name="fk_pieza_calibre_calibre", ondelete="CASCADE"),
        sa.UniqueConstraint("pieza_id", "calibre_id", name="uq_pieza_calibre"),
    )

    op.create_table(
        "stock_pieza",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("pieza_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("stock_actual >= 0", name="ck_stock_pieza_no_negativo"),
        sa.ForeignKeyConstraint(["pieza_id"], ["pieza.id"], name="fk_stock_pieza_pieza", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sucursal_id"], ["sucursal.id"], name="fk_stock_pieza_sucursal", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("pieza_id", "sucursal_id", name="uq_stock_pieza"),
    )

    op.create_table(
        "lote_pieza",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("pieza_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("numero_lote", sa.String(length=60), nullable=False),
        sa.Column("fecha_caducidad", sa.Date(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="vigente"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("cantidad >= 0", name="ck_lote_pieza_cantidad"),
        sa.CheckConstraint(
            "estado in ('vigente','proximo_vencer','vencido')", name="ck_lote_pieza_estado"
        ),
        sa.ForeignKeyConstraint(["pieza_id"], ["pieza.id"], name="fk_lote_pieza_pieza", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sucursal_id"], ["sucursal.id"], name="fk_lote_pieza_sucursal", ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_lote_pieza_pieza", "lote_pieza", ["pieza_id", "fecha_caducidad"])

    op.create_table(
        "movimiento_stock_pieza",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("pieza_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=24), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.BigInteger(), nullable=True),
        sa.Column("documento_tipo", sa.String(length=30), nullable=True),
        sa.Column("documento_id", sa.BigInteger(), nullable=True),
        sa.Column("nota", sa.String(length=255), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tipo in ('ingreso','consumo_ot','venta_suelta','ajuste','merma',"
            "'transferencia_salida','transferencia_entrada')",
            name="ck_movimiento_stock_pieza_tipo",
        ),
        sa.CheckConstraint("cantidad <> 0", name="ck_movimiento_stock_pieza_cantidad"),
        sa.ForeignKeyConstraint(
            ["pieza_id"], ["pieza.id"], name="fk_movimiento_stock_pieza_pieza", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_id"], ["sucursal.id"], name="fk_movimiento_stock_pieza_sucursal", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["lote_id"], ["lote_pieza.id"], name="fk_movimiento_stock_pieza_lote", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["creado_por"], ["usuario.id"], name="fk_movimiento_stock_pieza_usuario", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_movimiento_stock_pieza_pieza", "movimiento_stock_pieza", ["pieza_id", "creado_en"])

    op.create_table(
        "alerta_stock",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ambito", sa.String(length=10), nullable=False),
        sa.Column("ref", sa.String(length=200), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=True),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="abierta"),
        sa.Column("detalle", postgresql.JSONB(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resuelto_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("ambito in ('modelo','pieza')", name="ck_alerta_stock_ambito"),
        sa.CheckConstraint(
            "tipo in ('cerca_maximo','ultima_unidad','bajo_minimo','caducidad_proxima','lote_vencido')",
            name="ck_alerta_stock_tipo",
        ),
        sa.CheckConstraint("estado in ('abierta','resuelta')", name="ck_alerta_stock_estado"),
        sa.ForeignKeyConstraint(
            ["sucursal_id"], ["sucursal.id"], name="fk_alerta_stock_sucursal", ondelete="CASCADE"
        ),
    )
    op.create_index(
        "uq_alerta_stock_abierta",
        "alerta_stock",
        ["ambito", "ref", "sucursal_id", "tipo"],
        unique=True,
        postgresql_where=sa.text("estado = 'abierta'"),
    )

    # Inmutabilidad del historial de serie y del libro de movimientos (append-only).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cronos_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% es append-only (solo INSERT)', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for tabla in ("evento_serie", "movimiento_stock_pieza"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{tabla}_append_only
            BEFORE UPDATE OR DELETE ON {tabla}
            FOR EACH ROW EXECUTE FUNCTION cronos_append_only();
            """
        )

    # Parámetros configurables (§9.2) con su valor por defecto.
    for clave, valor in _PARAMETROS:
        op.execute(
            "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
            f"VALUES ('{clave}', 'numero', '{int(valor)}'::jsonb, 'global')"
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM parametro_configuracion WHERE clave IN "
        "('stock_maximo_modelo','umbral_reposicion_relojes','umbral_reposicion_piezas','umbral_caducidad_dias')"
    )
    for tabla in ("evento_serie", "movimiento_stock_pieza"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_append_only ON {tabla}")
    op.execute("DROP FUNCTION IF EXISTS cronos_append_only()")
    op.drop_table("alerta_stock")
    op.drop_table("movimiento_stock_pieza")
    op.drop_table("lote_pieza")
    op.drop_table("stock_pieza")
    op.drop_table("pieza_calibre")
    op.drop_table("pieza")
    op.drop_table("evento_serie")
    op.drop_table("documento_reloj")
    op.drop_table("foto_reloj")
    op.drop_table("reloj")
    op.drop_table("calibre")
