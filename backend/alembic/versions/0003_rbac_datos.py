"""permiso_usuario (excepciones individuales) + siembra del catálogo `modulo`.

Módulos de §3.1 de la especificación + `ventas` y `notificaciones`.
Cada feature 002+ puede añadir el suyo si falta.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MODULOS = [
    ("citas", "Citas"),
    ("proveedores", "Proveedores"),
    ("tecnicos", "Técnicos"),
    ("inventario_relojes", "Inventario de relojes"),
    ("piezas", "Piezas"),
    ("lubricacion", "Fichas de lubricación"),
    ("ordenes_trabajo", "Órdenes de trabajo"),
    ("clientes_fidelizacion", "Clientes y fidelización"),
    ("multisucursal", "Multisucursal y traslados"),
    ("contable", "Contabilidad"),
    ("reportes", "Reportes y dashboards"),
    ("mermas", "Mermas y pérdidas"),
    ("configuracion", "Configuración del sistema"),
    ("ventas", "Ventas"),
    ("notificaciones", "Notificaciones"),
]


def upgrade() -> None:
    op.create_table(
        "permiso_usuario",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("modulo_id", sa.BigInteger(), nullable=False),
        sa.Column("operacion_id", sa.BigInteger(), nullable=True),
        sa.Column("efecto", sa.String(length=8), nullable=False),
        sa.CheckConstraint("efecto in ('conceder','revocar')", name="ck_permiso_usuario_efecto"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name="fk_permiso_usuario_usuario", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["modulo_id"], ["modulo.id"], name="fk_permiso_usuario_modulo", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["operacion_id"], ["operacion.id"], name="fk_permiso_usuario_operacion", ondelete="CASCADE"
        ),
    )
    # NULL en operacion_id representa "excepción a nivel de acceso a módulo";
    # el UNIQUE de Postgres trata cada NULL como distinto, así que usamos un
    # índice único parcial + otro para la fila de módulo.
    op.create_index(
        "uq_permiso_usuario_operacion",
        "permiso_usuario",
        ["usuario_id", "modulo_id", "operacion_id"],
        unique=True,
        postgresql_where=sa.text("operacion_id IS NOT NULL"),
    )
    op.create_index(
        "uq_permiso_usuario_modulo",
        "permiso_usuario",
        ["usuario_id", "modulo_id"],
        unique=True,
        postgresql_where=sa.text("operacion_id IS NULL"),
    )

    modulo = sa.table("modulo", sa.column("clave", sa.String), sa.column("nombre", sa.String))
    op.bulk_insert(modulo, [{"clave": c, "nombre": n} for c, n in _MODULOS])


def downgrade() -> None:
    op.execute(
        "DELETE FROM modulo WHERE clave IN ("
        + ",".join(f"'{c}'" for c, _ in _MODULOS)
        + ")"
    )
    op.drop_index("uq_permiso_usuario_modulo", table_name="permiso_usuario")
    op.drop_index("uq_permiso_usuario_operacion", table_name="permiso_usuario")
    op.drop_table("permiso_usuario")
