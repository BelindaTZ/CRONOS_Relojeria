"""Feature 011 — amplía mermas con motivo detallado (feedback del usuario tras
la 1ª implementación: "me faltaría el motivo, la razón específica — ¿podría
haber una tabla de categorías de merma? robo, defecto de fábrica, o un
incidente aislado como que se cayera o se rompió").

- `categoria_merma` (catálogo editable, como `categoria_gasto`): motivo
  específico dentro de una `causa` (ej. causa `dano_tienda` → "Caída
  accidental", "Golpe o impacto", "Rotura de cristal/correa"). Se administra
  igual que `categoria_gasto` — sin pantalla propia, se crea inline (`:crear`)
  desde el formulario de merma; `GET` es de referencia (cualquier autenticado),
  `POST` exige `configuracion:crear` (Gerencia General o delegado).
- `merma.categoria_merma_id` (FK nullable — la categoría es opcional, algunas
  causas como `insumo_caducado` no la necesitan) + `merma.descripcion`
  (texto libre, el relato del hecho — "se cayó del mostrador al limpiarlo").

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORIAS = [
    # (nombre, causa)
    ("Caída accidental", "dano_tienda"),
    ("Golpe o impacto", "dano_tienda"),
    ("Manipulación incorrecta", "dano_tienda"),
    ("Rotura de cristal o correa", "dano_tienda"),
    ("Caída durante el transporte", "dano_transito"),
    ("Golpe en el empaque", "dano_transito"),
    ("Extravío en tránsito", "dano_transito"),
    ("Robo con violencia", "robo_perdida"),
    ("Hurto interno", "robo_perdida"),
    ("Pérdida sin explicación", "robo_perdida"),
    ("Falla de movimiento", "defecto_fabrica"),
    ("Defecto de materiales", "defecto_fabrica"),
    ("Defecto de acabado", "defecto_fabrica"),
    ("Daño durante el desarme", "dano_servicio"),
    ("Daño durante prueba o ajuste", "dano_servicio"),
    ("Pieza incompatible instalada por error", "dano_servicio"),
    ("Vencimiento de lote", "insumo_caducado"),
]


def upgrade() -> None:
    op.create_table(
        "categoria_merma",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("causa", sa.String(length=20), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("nombre", name="uq_categoria_merma_nombre"),
    )

    op.add_column("merma", sa.Column("categoria_merma_id", sa.BigInteger(), nullable=True))
    op.add_column("merma", sa.Column("descripcion", sa.String(length=500), nullable=True))
    op.create_foreign_key(
        "fk_merma_categoria", "merma", "categoria_merma", ["categoria_merma_id"], ["id"], ondelete="SET NULL",
    )

    tabla = sa.table(
        "categoria_merma", sa.column("nombre", sa.String), sa.column("causa", sa.String),
    )
    op.bulk_insert(tabla, [{"nombre": n, "causa": c} for n, c in _CATEGORIAS])


def downgrade() -> None:
    op.drop_constraint("fk_merma_categoria", "merma", type_="foreignkey")
    op.drop_column("merma", "descripcion")
    op.drop_column("merma", "categoria_merma_id")
    op.drop_table("categoria_merma")
