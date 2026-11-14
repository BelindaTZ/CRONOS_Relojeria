"""Feature 014 — notificaciones automatizadas por email (spec decía `0017`;
renumerada).

`plantilla_email` (override editable de una plantilla de `shared/correo` —
histórico por versión, como máximo una fila `activa` por `tipo` vía índice
único parcial; SIN fila activa el render sigue usando el archivo Jinja2 de
siempre — nunca se duplicó el HTML de las 10 plantillas ya existentes en esta
migración, solo se habilita el mecanismo de override), `envio` (cola +
seguimiento de estado, dedup por `clave_idempotencia`), `preferencia_comunicacion`
(opt-out por cliente y tipo), `evento_webhook_email` (append-only, reutiliza
`cronos_append_only()` de `0023`).

Semilla: parámetros `antelacion_recordatorio_cita_horas` (24), `max_reintentos_email`
(5), `backoff_email_minutos` (10) — mecanismo de `parametro_configuracion` de 001,
sin tabla nueva.

Revision ID: 0030
Revises: 0029
Create Date: 2026-09-11
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plantilla_email",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("asunto", sa.String(length=200), nullable=False),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("actualizado_por", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_plantilla_email_tipo_activa ON plantilla_email (tipo) WHERE activa"
    )

    op.create_table(
        "envio",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("destinatario_email", sa.String(length=160), nullable=True),
        sa.Column("cliente_id", sa.BigInteger(), nullable=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("disparo_origen_tipo", sa.String(length=24), nullable=False),
        sa.Column("disparo_origen_id", sa.BigInteger(), nullable=False),
        sa.Column("hito", sa.String(length=40), nullable=False),
        sa.Column("clave_idempotencia", sa.String(length=80), nullable=False),
        sa.Column("contexto", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="encolado"),
        sa.Column("motivo_estado", sa.String(length=120), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_reintentos", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("proxima_ejecucion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("proveedor_message_id", sa.String(length=120), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("clave_idempotencia", name="uq_envio_clave_idempotencia"),
        sa.CheckConstraint(
            "estado in ('encolado','enviando','enviado','entregado','rebotado','fallido','sin_destinatario','cancelado')",
            name="ck_envio_estado",
        ),
    )
    op.create_index("ix_envio_estado_proxima", "envio", ["estado", "proxima_ejecucion"])
    op.create_index("ix_envio_cliente", "envio", ["cliente_id"])
    op.create_index("ix_envio_disparo", "envio", ["disparo_origen_tipo", "disparo_origen_id"])

    op.create_table(
        "preferencia_comunicacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_comunicacion", sa.String(length=30), nullable=False),
        sa.Column("opt_in", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("cliente_id", "tipo_comunicacion", name="uq_preferencia_cliente_tipo"),
    )

    op.create_table(
        "evento_webhook_email",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("proveedor_message_id", sa.String(length=120), nullable=True),
        sa.Column("evento", sa.String(length=20), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("recibido_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    # Append-only: reutiliza la función creada por 0023 (mismo patrón que
    # historial_estado_merma/historial_estado_ot — nunca se define dos veces).
    op.execute(
        "CREATE TRIGGER trg_evento_webhook_email_append_only "
        "BEFORE UPDATE OR DELETE ON evento_webhook_email "
        "FOR EACH ROW EXECUTE FUNCTION cronos_append_only()"
    )

    bind = op.get_bind()
    for clave, valor in [
        ("antelacion_recordatorio_cita_horas", 24),
        ("max_reintentos_email", 5),
        ("backoff_email_minutos", 10),
    ]:
        bind.execute(
            sa.text(
                "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
                "VALUES (:clave, 'numero', CAST(:v AS jsonb), 'global')"
            ),
            {"clave": clave, "v": json.dumps(valor)},
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM parametro_configuracion WHERE clave IN "
        "('antelacion_recordatorio_cita_horas', 'max_reintentos_email', 'backoff_email_minutos')"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_evento_webhook_email_append_only ON evento_webhook_email")
    op.drop_table("evento_webhook_email")
    op.drop_table("preferencia_comunicacion")
    op.drop_index("ix_envio_disparo", table_name="envio")
    op.drop_index("ix_envio_cliente", table_name="envio")
    op.drop_index("ix_envio_estado_proxima", table_name="envio")
    op.drop_table("envio")
    op.execute("DROP INDEX IF EXISTS uq_plantilla_email_tipo_activa")
    op.drop_table("plantilla_email")
