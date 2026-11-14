"""Facturación: datos del emisor, puntos de emisión, desglose de IVA (feature 009 — ampliación).

Tras el feedback del usuario (2026-09-10): los precios son PVP (IVA incluido); la
factura debe hacer el back-out y mostrar el desglose reglamentario ecuatoriano
(base imponible, IVA por tarifa, descuento, total). Numeración tipo SRI
`EEE-PPP-NNNNNNNNN`. La venta toma la sucursal del vendedor (no es un campo libre).

- **`config_facturacion`** — fila única global: datos del emisor (RUC, razón social,
  dirección matriz, obligado a llevar contabilidad, contribuyente especial, régimen).
- **`punto_emision`** — por sucursal: código de establecimiento + punto de emisión +
  secuencial propio.
- `orden_venta` / `linea_venta` ganan las columnas del desglose de impuestos.
- Parámetro `iva_porcentaje` (0.15).

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-10
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "config_facturacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("razon_social", sa.String(length=200), nullable=False, server_default="CRONOS Relojería"),
        sa.Column("nombre_comercial", sa.String(length=200), nullable=True),
        sa.Column("ruc", sa.String(length=13), nullable=False, server_default="0000000000001"),
        sa.Column("direccion_matriz", sa.String(length=255), nullable=True),
        sa.Column("obligado_contabilidad", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("contribuyente_especial", sa.String(length=40), nullable=True),
        sa.Column("regimen", sa.String(length=40), nullable=True),  # "RIMPE", "General"…
        sa.Column("leyenda_pie", sa.String(length=255), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute(
        "INSERT INTO config_facturacion (id, razon_social, ruc, direccion_matriz, obligado_contabilidad, "
        "leyenda_pie) VALUES (1, 'CRONOS Relojería de Alta Gama', '0000000000001', 'Configura la dirección "
        "en Sistema → Facturación', true, 'Documento interno — sin autorización del SRI en esta fase.')"
    )

    op.create_table(
        "punto_emision",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("establecimiento_codigo", sa.String(length=3), nullable=False, server_default="001"),
        sa.Column("punto_emision_codigo", sa.String(length=3), nullable=False, server_default="001"),
        sa.Column("secuencial_actual", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("direccion_establecimiento", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("sucursal_id", name="uq_punto_emision_sucursal"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_punto_emision_sucursal", ondelete="CASCADE"),
    )
    # un punto de emisión por sucursal activa existente (001-001)
    op.execute(
        "INSERT INTO punto_emision (sucursal_id, establecimiento_codigo, punto_emision_codigo, secuencial_actual) "
        "SELECT id, '001', '001', 0 FROM sucursal"
    )

    for tabla, cols in {
        "orden_venta": [
            ("numero_factura", sa.String(length=20)),
            ("subtotal_sin_impuestos", sa.Numeric(14, 2)),
            ("total_descuento", sa.Numeric(14, 2)),
            ("iva_porcentaje", sa.Numeric(6, 4)),
            ("iva_monto", sa.Numeric(14, 2)),
        ],
        "linea_venta": [
            ("descuento_monto", sa.Numeric(14, 2)),
            ("base_imponible", sa.Numeric(14, 2)),
            ("iva_monto", sa.Numeric(14, 2)),
            ("tarifa_iva", sa.Numeric(6, 4)),
        ],
    }.items():
        for nombre, tipo in cols:
            op.add_column(tabla, sa.Column(nombre, tipo, nullable=True))

    op.get_bind().execute(
        sa.text(
            "INSERT INTO parametro_configuracion (clave, tipo, valor, ambito_tipo) "
            "VALUES ('iva_porcentaje', 'porcentaje', CAST(:v AS jsonb), 'global')"
        ),
        {"v": json.dumps(0.15)},
    )


def downgrade() -> None:
    op.execute("DELETE FROM parametro_configuracion WHERE clave = 'iva_porcentaje'")
    for nombre in ("descuento_monto", "base_imponible", "iva_monto", "tarifa_iva"):
        op.drop_column("linea_venta", nombre)
    for nombre in ("numero_factura", "subtotal_sin_impuestos", "total_descuento", "iva_porcentaje", "iva_monto"):
        op.drop_column("orden_venta", nombre)
    op.drop_table("punto_emision")
    op.drop_table("config_facturacion")
