"""Técnicos y productividad (feature 005).

- `especialidad` (catálogo) + `tecnico` con especialidades y sucursales (N—M),
  vínculo opcional 1—1 a `usuario`.
- `esquema_costo_mano_obra` — sueldo mensual con vigencia (historial por inserción);
  la tarifa horaria se deriva de `parametro("horas_productivas_estandar_mes")`.
- `regla_bono` + `componente_bono` — esquema de bono configurable por Gerencia.
- `periodo_liquidacion` — rango con estado abierto/cerrado.
- `bono_acumulado` (técnico × periodo, `valor_total >= 0`, desglose por indicador)
  + `bono_ot` (prorrateo del bono entre las OT cerradas del periodo, consumido por 008).

Reutiliza `usuario`, `sucursal`, `parametro_configuracion`, `registro_auditoria` (001).

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARAMETROS = [
    ("horas_productivas_estandar_mes", 160),
    ("tiempo_estimado_horas_default", 2),
]

_ESPECIALIDADES = [
    "Rolex", "Omega", "Tudor", "Patek Philippe", "Audemars Piguet", "Jaeger-LeCoultre",
    "Cronógrafo", "Calendario perpetuo", "Tourbillon", "Repetición de minutos",
    "Automático", "Cuerda manual",
]


def upgrade() -> None:
    op.create_table(
        "especialidad",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=60), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("nombre", name="uq_especialidad_nombre"),
    )

    op.create_table(
        "tecnico",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("certificaciones", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=12), nullable=False, server_default="activo"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado in ('activo','inactivo')", name="ck_tecnico_estado"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name="fk_tecnico_usuario", ondelete="SET NULL"),
        sa.UniqueConstraint("usuario_id", name="uq_tecnico_usuario"),
    )
    op.create_index("ix_tecnico_estado", "tecnico", ["estado"])

    op.create_table(
        "tecnico_especialidad",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tecnico_id", sa.BigInteger(), nullable=False),
        sa.Column("especialidad_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnico.id"], name="fk_tec_esp_tecnico", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["especialidad_id"], ["especialidad.id"], name="fk_tec_esp_especialidad", ondelete="RESTRICT"),
        sa.UniqueConstraint("tecnico_id", "especialidad_id", name="uq_tecnico_especialidad"),
    )

    op.create_table(
        "tecnico_sucursal",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tecnico_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnico.id"], name="fk_tec_suc_tecnico", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_tec_suc_sucursal", ondelete="RESTRICT"),
        sa.UniqueConstraint("tecnico_id", "sucursal_id", name="uq_tecnico_sucursal"),
    )

    op.create_table(
        "esquema_costo_mano_obra",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tecnico_id", sa.BigInteger(), nullable=False),
        sa.Column("sueldo_mensual", sa.Numeric(14, 2), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sueldo_mensual >= 0", name="ck_esquema_costo_sueldo"),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnico.id"], name="fk_esquema_costo_tecnico", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_esquema_costo_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_esquema_costo_tecnico", "esquema_costo_mano_obra", ["tecnico_id", "vigente_desde"])

    op.create_table(
        "regla_bono",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("periodicidad", sa.String(length=10), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("periodicidad in ('mensual','trimestral')", name="ck_regla_bono_periodicidad"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_regla_bono_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_regla_bono_vigencia", "regla_bono", ["vigente_desde", "activa"])

    op.create_table(
        "componente_bono",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("regla_bono_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("indicador", sa.String(length=24), nullable=False),
        sa.Column("umbral", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("valor", sa.Numeric(14, 4), nullable=False),
        sa.CheckConstraint("tipo in ('monto_por_meta','porcentaje_margen','combinacion')", name="ck_componente_bono_tipo"),
        sa.CheckConstraint(
            "indicador in ('ot_completadas','cumplimiento_tiempos','margen_generado','calidad')",
            name="ck_componente_bono_indicador",
        ),
        sa.ForeignKeyConstraint(["regla_bono_id"], ["regla_bono.id"], name="fk_componente_bono_regla", ondelete="CASCADE"),
    )
    op.create_index("ix_componente_bono_regla", "componente_bono", ["regla_bono_id"])

    op.create_table(
        "periodo_liquidacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="abierto"),
        sa.Column("cerrado_por", sa.BigInteger(), nullable=True),
        sa.Column("cerrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado in ('abierto','cerrado')", name="ck_periodo_estado"),
        sa.CheckConstraint("fecha_fin >= fecha_inicio", name="ck_periodo_rango"),
        sa.ForeignKeyConstraint(["cerrado_por"], ["usuario.id"], name="fk_periodo_cerrado_por", ondelete="SET NULL"),
        sa.UniqueConstraint("fecha_inicio", "fecha_fin", name="uq_periodo_rango"),
    )

    op.create_table(
        "bono_acumulado",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tecnico_id", sa.BigInteger(), nullable=False),
        sa.Column("periodo_liquidacion_id", sa.BigInteger(), nullable=False),
        sa.Column("regla_bono_id", sa.BigInteger(), nullable=True),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("desglose", postgresql.JSONB(), nullable=True),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="preliminar"),
        sa.Column("calculado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("valor_total >= 0", name="ck_bono_acumulado_no_negativo"),
        sa.CheckConstraint("estado in ('preliminar','definitivo')", name="ck_bono_acumulado_estado"),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnico.id"], name="fk_bono_acumulado_tecnico", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["periodo_liquidacion_id"], ["periodo_liquidacion.id"], name="fk_bono_acumulado_periodo", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["regla_bono_id"], ["regla_bono.id"], name="fk_bono_acumulado_regla", ondelete="SET NULL"),
        sa.UniqueConstraint("tecnico_id", "periodo_liquidacion_id", name="uq_bono_acumulado_tecnico_periodo"),
    )

    op.create_table(
        "bono_ot",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("bono_acumulado_id", sa.BigInteger(), nullable=False),
        sa.Column("orden_trabajo_id", sa.BigInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["bono_acumulado_id"], ["bono_acumulado.id"], name="fk_bono_ot_bono", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_bono_ot_bono", "bono_ot", ["bono_acumulado_id"])
    op.create_index("ix_bono_ot_orden", "bono_ot", ["orden_trabajo_id"])

    for clave, valor in _PARAMETROS:
        op.execute(
            "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
            f"VALUES ('{clave}', 'numero', '{int(valor)}'::jsonb, 'global')"
        )

    esp = sa.table("especialidad", sa.column("nombre", sa.String))
    op.bulk_insert(esp, [{"nombre": n} for n in _ESPECIALIDADES])


def downgrade() -> None:
    op.execute(
        "DELETE FROM parametro_configuracion WHERE clave IN "
        "('horas_productivas_estandar_mes','tiempo_estimado_horas_default')"
    )
    op.drop_table("bono_ot")
    op.drop_table("bono_acumulado")
    op.drop_table("periodo_liquidacion")
    op.drop_table("componente_bono")
    op.drop_table("regla_bono")
    op.drop_table("esquema_costo_mano_obra")
    op.drop_table("tecnico_sucursal")
    op.drop_table("tecnico_especialidad")
    op.drop_table("tecnico")
    op.drop_table("especialidad")
