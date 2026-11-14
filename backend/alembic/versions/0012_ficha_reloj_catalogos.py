"""Catálogos de la ficha de reloj (feedback del usuario 2026-09-10): marca,
material y color dejan de ser texto libre.

- `marca_reloj` — catálogo rico: nombre, país, sitio web, nota.
- `material` — catálogo compartido para caja y brazalete.
- `color` — catálogo con nombre + hex opcional.
- `reloj` gana `marca_id`, `material_caja_id`, `material_brazalete_id`,
  `color_esfera_id` (FK, nullable). Se conserva `reloj.marca` (texto) porque las
  alertas de stock indexan por `marca|referencia`; se rellena siempre desde el
  catálogo. Se retro-cargan los valores existentes.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marca_reloj",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("pais", sa.String(length=80), nullable=True),
        sa.Column("sitio_web", sa.String(length=200), nullable=True),
        sa.Column("nota", sa.String(length=500), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_marca_reloj_nombre"),
    )
    op.create_table(
        "material",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_material_nombre"),
    )
    op.create_table(
        "color",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("hex", sa.String(length=7), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_color_nombre"),
    )

    op.add_column("reloj", sa.Column("marca_id", sa.BigInteger(), nullable=True))
    op.add_column("reloj", sa.Column("material_caja_id", sa.BigInteger(), nullable=True))
    op.add_column("reloj", sa.Column("material_brazalete_id", sa.BigInteger(), nullable=True))
    op.add_column("reloj", sa.Column("color_esfera_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_reloj_marca", "reloj", "marca_reloj", ["marca_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_reloj_material_caja", "reloj", "material", ["material_caja_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(
        "fk_reloj_material_brazalete", "reloj", "material", ["material_brazalete_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key("fk_reloj_color_esfera", "reloj", "color", ["color_esfera_id"], ["id"], ondelete="SET NULL")

    # --- retro-carga desde los valores de texto existentes ---
    op.execute(
        """
        INSERT INTO marca_reloj (nombre)
        SELECT DISTINCT trim(marca) FROM reloj
        WHERE marca IS NOT NULL AND trim(marca) <> ''
        ON CONFLICT (nombre) DO NOTHING
        """
    )
    op.execute(
        "UPDATE reloj r SET marca_id = m.id FROM marca_reloj m WHERE trim(r.marca) = m.nombre"
    )
    op.execute(
        """
        INSERT INTO material (nombre)
        SELECT DISTINCT trim(v) FROM (
            SELECT material_caja AS v FROM reloj
            UNION SELECT material_brazalete FROM reloj
        ) s WHERE v IS NOT NULL AND trim(v) <> ''
        ON CONFLICT (nombre) DO NOTHING
        """
    )
    op.execute("UPDATE reloj r SET material_caja_id = m.id FROM material m WHERE trim(r.material_caja) = m.nombre")
    op.execute(
        "UPDATE reloj r SET material_brazalete_id = m.id FROM material m WHERE trim(r.material_brazalete) = m.nombre"
    )
    op.execute(
        """
        INSERT INTO color (nombre)
        SELECT DISTINCT trim(color_esfera) FROM reloj
        WHERE color_esfera IS NOT NULL AND trim(color_esfera) <> ''
        ON CONFLICT (nombre) DO NOTHING
        """
    )
    op.execute("UPDATE reloj r SET color_esfera_id = c.id FROM color c WHERE trim(r.color_esfera) = c.nombre")


def downgrade() -> None:
    op.drop_constraint("fk_reloj_color_esfera", "reloj", type_="foreignkey")
    op.drop_constraint("fk_reloj_material_brazalete", "reloj", type_="foreignkey")
    op.drop_constraint("fk_reloj_material_caja", "reloj", type_="foreignkey")
    op.drop_constraint("fk_reloj_marca", "reloj", type_="foreignkey")
    op.drop_column("reloj", "color_esfera_id")
    op.drop_column("reloj", "material_brazalete_id")
    op.drop_column("reloj", "material_caja_id")
    op.drop_column("reloj", "marca_id")
    op.drop_table("color")
    op.drop_table("material")
    op.drop_table("marca_reloj")
