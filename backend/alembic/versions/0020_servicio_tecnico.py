"""Servicio técnico y lubricación (feature 008).

- **`pago`** (capacidad compartida `shared/pagos`, append-only): pagos multimedios
  contra un documento facturable (`orden_trabajo` ahora, `venta` en 009).
- **`orden_trabajo`** (§4.7) + `historial_estado_ot` (append-only) + `presupuesto`
  (+ líneas de pieza original/no original) + `pieza_usada_ot` + `documento_ot`.
- **Lubricación** (§4.6): `producto_moebius` (catálogo), `ficha_lubricacion_calibre`
  (1—1 con `calibre`) + `punto_lubricacion`, y `registro_lubricacion_ot` (append-only,
  recomendado vs. usado).

Reutiliza `reloj`, `pieza`, `calibre` (003); `tecnico` (005); `cliente`,
`autorizacion_margen_minimo` (006); `cita` (007); `medio_pago`, `usuario`,
`parametro_configuracion` (001). Los módulos RBAC `ordenes_trabajo` y `lubricacion`
ya se sembraron en `0003`.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-10
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MOEBIUS = [
    ("9010", "Pivotes rápidos de baja carga (balanza, rueda de escape, tren rápido)"),
    ("9104", "Pivotes de mayor presión (centro, tercera, barrilete, automáticos)"),
    ("HP-1300", "Pivotes de mayor presión — alternativa sintética de larga duración"),
    ("9415", "Paletas del áncora (escapement)"),
    ("9501", "Mecanismo de cuerda, puesta en hora, calendario"),
    ("9504", "Mecanismo de cuerda y calendario — mayor adherencia"),
    ("8200", "Resorte de barrilete y paredes del barrilete"),
    ("8217", "Resorte de barrilete — automáticos, efecto brake grease"),
    ("8513", "Juntas de estanqueidad (gaskets)"),
    ("8516", "Juntas de estanqueidad — alta resistencia a la temperatura"),
]


def _append_only_trigger(tabla: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{tabla}_append_only
        BEFORE UPDATE OR DELETE ON {tabla}
        FOR EACH ROW EXECUTE FUNCTION cronos_append_only();
        """
    )


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cronos_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% es append-only (solo INSERT)', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("CREATE SEQUENCE IF NOT EXISTS orden_trabajo_numero_seq START WITH 1")

    # ---- shared/pagos -------------------------------------------------------
    op.create_table(
        "pago",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("documento_tipo", sa.String(length=16), nullable=False),
        sa.Column("documento_id", sa.BigInteger(), nullable=False),
        sa.Column("medio_pago_id", sa.BigInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("referencia", sa.String(length=80), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("documento_tipo in ('orden_trabajo','venta')", name="ck_pago_documento_tipo"),
        sa.CheckConstraint("monto > 0", name="ck_pago_monto"),
        sa.ForeignKeyConstraint(["medio_pago_id"], ["medio_pago.id"], name="fk_pago_medio", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_pago_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_pago_documento", "pago", ["documento_tipo", "documento_id"])

    # ---- lubricación: catálogo + fichas -----------------------------------
    op.create_table(
        "producto_moebius",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("uso_recomendado", sa.String(length=255), nullable=True),
        sa.Column("pieza_id", sa.BigInteger(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("codigo", name="uq_producto_moebius_codigo"),
        sa.ForeignKeyConstraint(["pieza_id"], ["pieza.id"], name="fk_moebius_pieza", ondelete="SET NULL"),
    )

    op.create_table(
        "ficha_lubricacion_calibre",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("calibre_id", sa.BigInteger(), nullable=False),
        sa.Column("notas_generales", sa.Text(), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("calibre_id", name="uq_ficha_lubricacion_calibre"),
        sa.ForeignKeyConstraint(["calibre_id"], ["calibre.id"], name="fk_ficha_lub_calibre", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_ficha_lub_creado_por", ondelete="SET NULL"),
    )

    op.create_table(
        "punto_lubricacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ficha_lubricacion_calibre_id", sa.BigInteger(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("producto_moebius_id", sa.BigInteger(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["ficha_lubricacion_calibre_id"], ["ficha_lubricacion_calibre.id"],
            name="fk_punto_ficha", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["producto_moebius_id"], ["producto_moebius.id"], name="fk_punto_moebius", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_punto_ficha", "punto_lubricacion", ["ficha_lubricacion_calibre_id"])

    # ---- orden de trabajo -------------------------------------------------
    op.create_table(
        "orden_trabajo",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("reloj_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("tecnico_id", sa.BigInteger(), nullable=True),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("cita_id", sa.BigInteger(), nullable=True),
        sa.Column("ot_original_id", sa.BigInteger(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("diagnostico", sa.Text(), nullable=True),
        sa.Column("trabajo_realizado", sa.Text(), nullable=True),
        sa.Column("tipo_reparacion", sa.String(length=40), nullable=False),
        sa.Column("horas_trabajadas", sa.Numeric(6, 2), nullable=True),
        sa.Column("fecha_ingreso", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fecha_estimada_entrega", sa.Date(), nullable=True),
        sa.Column("fecha_real_entrega", sa.DateTime(timezone=True), nullable=True),
        sa.Column("costo_interno", sa.Numeric(14, 2), nullable=True),
        sa.Column("precio_cobrado", sa.Numeric(14, 2), nullable=True),
        sa.Column("margen_real", sa.Numeric(14, 2), nullable=True),
        sa.Column("descuento_aplicado", postgresql.JSONB(), nullable=True),
        sa.Column("garantia_periodo_dias", sa.Integer(), nullable=True),
        sa.Column("garantia_cobertura", sa.String(length=255), nullable=True),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="recibido"),
        sa.Column("autorizacion_credito_id", sa.BigInteger(), nullable=True),
        sa.Column("adquirido_en_tienda_ok", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("override_adquisicion_motivo", sa.String(length=255), nullable=True),
        sa.Column("reproceso", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "estado in ('recibido','en_diagnostico','presupuesto','en_reparacion','listo','entregado','cancelada')",
            name="ck_ot_estado",
        ),
        sa.UniqueConstraint("numero", name="uq_orden_trabajo_numero"),
        sa.ForeignKeyConstraint(["reloj_id"], ["reloj.id"], name="fk_ot_reloj", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_ot_cliente", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnico.id"], name="fk_ot_tecnico", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_ot_sucursal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cita_id"], ["cita.id"], name="fk_ot_cita", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ot_original_id"], ["orden_trabajo.id"], name="fk_ot_original", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["autorizacion_credito_id"], ["autorizacion_margen_minimo.id"],
            name="fk_ot_autorizacion_credito", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_ot_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_ot_estado", "orden_trabajo", ["estado"])
    op.create_index("ix_ot_tecnico", "orden_trabajo", ["tecnico_id"])
    op.create_index("ix_ot_reloj", "orden_trabajo", ["reloj_id"])
    op.create_index("ix_ot_sucursal", "orden_trabajo", ["sucursal_id"])

    op.create_table(
        "historial_estado_ot",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_trabajo_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=16), nullable=False),
        sa.Column("actor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["orden_trabajo_id"], ["orden_trabajo.id"], name="fk_hist_ot_ot", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_usuario_id"], ["usuario.id"], name="fk_hist_ot_actor", ondelete="SET NULL"),
    )
    op.create_index("ix_hist_estado_ot", "historial_estado_ot", ["orden_trabajo_id", "timestamp"])

    op.create_table(
        "presupuesto",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_trabajo_id", sa.BigInteger(), nullable=False),
        sa.Column("precio_servicio", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(length=12), nullable=False, server_default="borrador"),
        sa.Column("confirmado_por", sa.String(length=160), nullable=True),
        sa.Column("medio_confirmacion", sa.String(length=40), nullable=True),
        sa.Column("fecha_confirmacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado in ('borrador','enviado','aprobado','rechazado')", name="ck_presupuesto_estado"),
        sa.ForeignKeyConstraint(["orden_trabajo_id"], ["orden_trabajo.id"], name="fk_presupuesto_ot", ondelete="CASCADE"),
    )
    op.create_index("ix_presupuesto_ot", "presupuesto", ["orden_trabajo_id"])

    op.create_table(
        "presupuesto_linea_pieza",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("presupuesto_id", sa.BigInteger(), nullable=False),
        sa.Column("pieza_original_id", sa.BigInteger(), nullable=False),
        sa.Column("pieza_no_original_id", sa.BigInteger(), nullable=True),
        sa.Column("precio_original", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("precio_no_original", sa.Numeric(14, 2), nullable=True),
        sa.Column("preferencia_cliente", sa.String(length=12), nullable=True),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "preferencia_cliente is null or preferencia_cliente in ('original','no_original','mixto')",
            name="ck_presu_linea_preferencia",
        ),
        sa.ForeignKeyConstraint(
            ["presupuesto_id"], ["presupuesto.id"], name="fk_presu_linea_presu", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pieza_original_id"], ["pieza.id"], name="fk_presu_linea_orig", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pieza_no_original_id"], ["pieza.id"], name="fk_presu_linea_noorig", ondelete="RESTRICT"),
    )

    op.create_table(
        "pieza_usada_ot",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_trabajo_id", sa.BigInteger(), nullable=False),
        sa.Column("pieza_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_elegido", sa.String(length=12), nullable=False, server_default="original"),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("costo", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("lote_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo_elegido in ('original','no_original')", name="ck_pieza_usada_tipo"),
        sa.CheckConstraint("cantidad > 0", name="ck_pieza_usada_cantidad"),
        sa.ForeignKeyConstraint(["orden_trabajo_id"], ["orden_trabajo.id"], name="fk_pieza_usada_ot", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pieza_id"], ["pieza.id"], name="fk_pieza_usada_pieza", ondelete="RESTRICT"),
    )
    op.create_index("ix_pieza_usada_ot", "pieza_usada_ot", ["orden_trabajo_id"])

    op.create_table(
        "registro_lubricacion_ot",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_trabajo_id", sa.BigInteger(), nullable=False),
        sa.Column("punto_lubricacion_id", sa.BigInteger(), nullable=True),
        sa.Column("punto_nombre", sa.String(length=120), nullable=False),
        sa.Column("producto_recomendado_id", sa.BigInteger(), nullable=True),
        sa.Column("producto_usado_id", sa.BigInteger(), nullable=False),
        sa.Column("tecnico_id", sa.BigInteger(), nullable=True),
        sa.Column("desviacion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["orden_trabajo_id"], ["orden_trabajo.id"], name="fk_reg_lub_ot", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["punto_lubricacion_id"], ["punto_lubricacion.id"], name="fk_reg_lub_punto", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["producto_recomendado_id"], ["producto_moebius.id"], name="fk_reg_lub_reco", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["producto_usado_id"], ["producto_moebius.id"], name="fk_reg_lub_usado", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnico.id"], name="fk_reg_lub_tecnico", ondelete="SET NULL"),
    )
    op.create_index("ix_reg_lub_ot", "registro_lubricacion_ot", ["orden_trabajo_id"])
    op.create_index("ix_reg_lub_desviacion", "registro_lubricacion_ot", ["desviacion", "fecha"])

    op.create_table(
        "documento_ot",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("orden_trabajo_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=24), nullable=False),
        sa.Column("objeto", sa.String(length=255), nullable=False),
        sa.Column("generado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo in ('orden_trabajo','certificado_garantia')", name="ck_documento_ot_tipo"),
        sa.ForeignKeyConstraint(["orden_trabajo_id"], ["orden_trabajo.id"], name="fk_documento_ot_ot", ondelete="CASCADE"),
    )
    op.create_index("ix_documento_ot", "documento_ot", ["orden_trabajo_id"])

    for t in ("pago", "historial_estado_ot", "registro_lubricacion_ot"):
        _append_only_trigger(t)

    # ---- semillas -------------------------------------------------------
    moe = sa.table("producto_moebius", sa.column("codigo", sa.String), sa.column("uso_recomendado", sa.String))
    op.bulk_insert(moe, [{"codigo": c, "uso_recomendado": u} for c, u in _MOEBIUS])

    bind = op.get_bind()
    for clave, tipo, valor in [
        ("margen_objetivo_servicio", "porcentaje", 0.5),
        ("garantia_tienda_dias_default", "numero", 180),
    ]:
        bind.execute(
            sa.text(
                "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
                "VALUES (:c, :t, CAST(:v AS jsonb), 'global')"
            ),
            {"c": clave, "t": tipo, "v": json.dumps(valor)},
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM parametro_configuracion WHERE clave IN "
        "('margen_objetivo_servicio','garantia_tienda_dias_default')"
    )
    for t in ("pago", "historial_estado_ot", "registro_lubricacion_ot"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{t}_append_only ON {t}")
    op.drop_table("documento_ot")
    op.drop_table("registro_lubricacion_ot")
    op.drop_table("pieza_usada_ot")
    op.drop_table("presupuesto_linea_pieza")
    op.drop_table("presupuesto")
    op.drop_table("historial_estado_ot")
    op.drop_table("orden_trabajo")
    op.drop_table("punto_lubricacion")
    op.drop_table("ficha_lubricacion_calibre")
    op.drop_table("producto_moebius")
    op.drop_table("pago")
    op.execute("DROP SEQUENCE IF EXISTS orden_trabajo_numero_seq")
