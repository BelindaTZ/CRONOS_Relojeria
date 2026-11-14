"""Clientes, fidelización y descuentos (feature 006).

- `cliente` (CRM básico) con `identificacion` única (cédula/RUC), `numero_afiliado`
  único autogenerado (`AF-######`), consentimiento LOPDP obligatorio, y una fila
  genérica `es_consumidor_final = true` para ventas de pieza suelta (009).
- `nivel_fidelizacion` + `regla_nivel` (criterio monto/frecuencia/combinación,
  ventana, umbrales) + `historial_nivel_cliente` (append-only).
- `descuento` (general) y `cupon` (código único, uso con lock).
- `aplicacion_descuento` (la crea 008/009) y `autorizacion_margen_minimo`.

Reutiliza `parametro_configuracion`, `registro_auditoria`, `usuario` (001).
El módulo RBAC `clientes_fidelizacion` ya se sembró en `0003`.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-10
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSENTIMIENTO_V1 = (
    "Autorizo de forma libre, previa, informada y expresa el tratamiento de mis "
    "datos personales por parte de la relojería para la gestión de compras, "
    "servicio técnico, programa de fidelización y comunicaciones comerciales "
    "relacionadas, conforme a la Ley Orgánica de Protección de Datos Personales "
    "del Ecuador. Puedo revocar este consentimiento y ejercer mis derechos en "
    "cualquier momento."
)


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS cliente_afiliado_seq START WITH 1")

    op.create_table(
        "nivel_fidelizacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=60), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("beneficios", postgresql.JSONB(), nullable=True),
        sa.Column("es_base", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_nivel_fidelizacion_nombre"),
    )

    op.create_table(
        "cliente",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tipo", sa.String(length=10), nullable=False, server_default="natural"),
        sa.Column("identificacion", sa.String(length=20), nullable=False),
        sa.Column("numero_afiliado", sa.String(length=16), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("telefono", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("direccion", sa.String(length=255), nullable=True),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("preferencias", postgresql.JSONB(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("nivel_fidelizacion_id", sa.BigInteger(), nullable=True),
        sa.Column("es_consumidor_final", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("estado", sa.String(length=12), nullable=False, server_default="activo"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo in ('natural','juridica')", name="ck_cliente_tipo"),
        sa.CheckConstraint("estado in ('activo','inactivo')", name="ck_cliente_estado"),
        sa.ForeignKeyConstraint(
            ["nivel_fidelizacion_id"], ["nivel_fidelizacion.id"], name="fk_cliente_nivel", ondelete="SET NULL"
        ),
        sa.UniqueConstraint("identificacion", name="uq_cliente_identificacion"),
        sa.UniqueConstraint("numero_afiliado", name="uq_cliente_numero_afiliado"),
    )
    op.create_index("ix_cliente_nombre", "cliente", ["nombre"])
    op.create_index("ix_cliente_estado", "cliente", ["estado"])
    op.create_index(
        "uq_cliente_consumidor_final", "cliente", ["es_consumidor_final"],
        unique=True, postgresql_where=sa.text("es_consumidor_final = true"),
    )

    op.create_table(
        "consentimiento_datos",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("aceptado", sa.Boolean(), nullable=False),
        sa.Column("version_texto", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_consentimiento_cliente", ondelete="CASCADE"),
    )
    op.create_index("ix_consentimiento_cliente", "consentimiento_datos", ["cliente_id"])

    op.create_table(
        "regla_nivel",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nivel_fidelizacion_id", sa.BigInteger(), nullable=False),
        sa.Column("criterio", sa.String(length=20), nullable=False),
        sa.Column("ventana_meses", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("umbral_monto", sa.Numeric(14, 2), nullable=True),
        sa.Column("umbral_frecuencia", sa.Integer(), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "criterio in ('monto_acumulado','frecuencia','combinacion')", name="ck_regla_nivel_criterio"
        ),
        sa.ForeignKeyConstraint(
            ["nivel_fidelizacion_id"], ["nivel_fidelizacion.id"], name="fk_regla_nivel_nivel", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_regla_nivel_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_regla_nivel_nivel", "regla_nivel", ["nivel_fidelizacion_id", "vigente_desde"])

    op.create_table(
        "historial_nivel_cliente",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("nivel_anterior_id", sa.BigInteger(), nullable=True),
        sa.Column("nivel_nuevo_id", sa.BigInteger(), nullable=False),
        sa.Column("hecho_disparador", sa.String(length=30), nullable=False),
        sa.Column("documento_id", sa.BigInteger(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_hist_nivel_cliente", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nivel_anterior_id"], ["nivel_fidelizacion.id"], name="fk_hist_nivel_ant", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["nivel_nuevo_id"], ["nivel_fidelizacion.id"], name="fk_hist_nivel_nuevo", ondelete="SET NULL"),
    )
    op.create_index("ix_hist_nivel_cliente", "historial_nivel_cliente", ["cliente_id", "fecha"])

    op.create_table(
        "descuento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("valor", sa.Numeric(14, 4), nullable=False),
        sa.Column("alcance", sa.String(length=10), nullable=False, server_default="tienda"),
        sa.Column("alcance_ref", sa.String(length=80), nullable=True),
        sa.Column("segmento", sa.String(length=10), nullable=False, server_default="todos"),
        sa.Column("segmento_ref", sa.String(length=80), nullable=True),
        sa.Column("vigencia_inicio", sa.Date(), nullable=True),
        sa.Column("vigencia_fin", sa.Date(), nullable=True),
        sa.Column("evento", sa.String(length=24), nullable=True),
        sa.Column("limite_uso", sa.String(length=12), nullable=False, server_default="global"),
        sa.Column("max_usos", sa.Integer(), nullable=True),
        sa.Column("usos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="activo"),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo in ('porcentaje','monto')", name="ck_descuento_tipo"),
        sa.CheckConstraint("alcance in ('producto','marca','tienda')", name="ck_descuento_alcance"),
        sa.CheckConstraint("segmento in ('todos','nivel','cliente')", name="ck_descuento_segmento"),
        sa.CheckConstraint("estado in ('activo','inactivo','vencido')", name="ck_descuento_estado"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_descuento_creado_por", ondelete="SET NULL"),
    )

    op.create_table(
        "cupon",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("codigo", sa.String(length=24), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("valor", sa.Numeric(14, 4), nullable=False),
        sa.Column("alcance", sa.String(length=10), nullable=False, server_default="tienda"),
        sa.Column("alcance_ref", sa.String(length=80), nullable=True),
        sa.Column("vigencia_inicio", sa.Date(), nullable=True),
        sa.Column("vigencia_fin", sa.Date(), nullable=True),
        sa.Column("evento", sa.String(length=24), nullable=True),
        sa.Column("limite_uso", sa.String(length=12), nullable=False, server_default="una_vez"),
        sa.Column("max_usos", sa.Integer(), nullable=True),
        sa.Column("usos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="activo"),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo in ('porcentaje','monto')", name="ck_cupon_tipo"),
        sa.CheckConstraint("alcance in ('producto','marca','tienda')", name="ck_cupon_alcance"),
        sa.CheckConstraint("estado in ('activo','usado','vencido')", name="ck_cupon_estado"),
        sa.CheckConstraint("usos >= 0", name="ck_cupon_usos"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_cupon_cliente", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_cupon_creado_por", ondelete="SET NULL"),
        sa.UniqueConstraint("codigo", name="uq_cupon_codigo"),
    )
    op.create_index("ix_cupon_cliente", "cupon", ["cliente_id", "estado"])

    op.create_table(
        "aplicacion_descuento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("documento_tipo", sa.String(length=16), nullable=False),
        sa.Column("documento_id", sa.BigInteger(), nullable=False),
        sa.Column("linea_id", sa.BigInteger(), nullable=True),
        sa.Column("origen", sa.String(length=10), nullable=False),
        sa.Column("origen_id", sa.BigInteger(), nullable=True),
        sa.Column("precio_lista", sa.Numeric(14, 2), nullable=False),
        sa.Column("precio_final", sa.Numeric(14, 2), nullable=False),
        sa.Column("margen_resultante", sa.Numeric(14, 4), nullable=True),
        sa.Column("autorizacion_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("documento_tipo in ('venta','orden_trabajo')", name="ck_aplicacion_doc_tipo"),
        sa.CheckConstraint("origen in ('descuento','cupon')", name="ck_aplicacion_origen"),
    )
    op.create_index("ix_aplicacion_documento", "aplicacion_descuento", ["documento_tipo", "documento_id"])

    op.create_table(
        "autorizacion_margen_minimo",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("documento_tipo", sa.String(length=16), nullable=False),
        sa.Column("documento_id", sa.BigInteger(), nullable=False),
        sa.Column("autorizador_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("margen_resultante", sa.Numeric(14, 4), nullable=True),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("documento_tipo in ('venta','orden_trabajo')", name="ck_autorizacion_doc_tipo"),
        sa.ForeignKeyConstraint(
            ["autorizador_usuario_id"], ["usuario.id"], name="fk_autorizacion_usuario", ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_autorizacion_documento", "autorizacion_margen_minimo", ["documento_tipo", "documento_id"]
    )
    op.create_foreign_key(
        "fk_aplicacion_autorizacion", "aplicacion_descuento", "autorizacion_margen_minimo",
        ["autorizacion_id"], ["id"], ondelete="SET NULL",
    )

    # ---- append-only del historial de nivel -------------------------------------
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
        CREATE TRIGGER trg_historial_nivel_cliente_append_only
        BEFORE UPDATE OR DELETE ON historial_nivel_cliente
        FOR EACH ROW EXECUTE FUNCTION cronos_append_only();
        """
    )

    # ---- semillas -------------------------------------------------------------
    niv = sa.table(
        "nivel_fidelizacion",
        sa.column("nombre", sa.String), sa.column("orden", sa.Integer),
        sa.column("beneficios", postgresql.JSONB), sa.column("es_base", sa.Boolean),
    )
    op.bulk_insert(niv, [{"nombre": "Bronce", "orden": 1, "beneficios": {}, "es_base": True}])

    bind = op.get_bind()
    for clave, tipo, valor in [
        ("margen_minimo", "json", {"tipo": "porcentaje_costo", "valor": 0.15}),
        ("margen_minimo_politica", "texto", "autorizar"),
        ("monto_max_consumidor_final", "monto", 500),
        ("fidelizacion_ventana_meses", "numero", 12),
        ("texto_consentimiento_lopdp", "json", {"version": 1, "texto": _CONSENTIMIENTO_V1}),
    ]:
        bind.execute(
            sa.text(
                "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
                "VALUES (:clave, :tipo, CAST(:valor AS jsonb), 'global')"
            ),
            {"clave": clave, "tipo": tipo, "valor": json.dumps(valor)},
        )

    # fila genérica "consumidor final"
    op.execute(
        """
        INSERT INTO cliente (tipo, identificacion, numero_afiliado, nombre, es_consumidor_final,
                             nivel_fidelizacion_id, estado)
        SELECT 'natural', 'CONSUMIDOR-FINAL', 'AF-000000', 'Consumidor Final', true, nf.id, 'activo'
        FROM nivel_fidelizacion nf WHERE nf.es_base = true
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM parametro_configuracion WHERE clave IN "
        "('margen_minimo','margen_minimo_politica','monto_max_consumidor_final',"
        "'fidelizacion_ventana_meses','texto_consentimiento_lopdp')"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_historial_nivel_cliente_append_only ON historial_nivel_cliente")
    op.drop_constraint("fk_aplicacion_autorizacion", "aplicacion_descuento", type_="foreignkey")
    op.drop_table("autorizacion_margen_minimo")
    op.drop_table("aplicacion_descuento")
    op.drop_table("cupon")
    op.drop_table("descuento")
    op.drop_table("historial_nivel_cliente")
    op.drop_table("regla_nivel")
    op.drop_table("consentimiento_datos")
    op.drop_table("cliente")
    op.drop_table("nivel_fidelizacion")
    op.execute("DROP SEQUENCE IF EXISTS cliente_afiliado_seq")
