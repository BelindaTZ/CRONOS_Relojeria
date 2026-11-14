"""Contabilidad, gastos, cuentas por cobrar y por pagar (feature 010).

- **Plan de cuentas** (NIIF PYMES, simplificado) + **libro diario** (`asiento` +
  `linea_asiento`, partida doble balanceada) → mayor/balance/estado de resultados
  se derivan por consulta (research D2).
- **Caja y bancos por sucursal** (`caja`/`sesion_caja`/`movimiento_caja`), **cheques**
  (emitidos/recibidos, con protesto).
- **`cuenta_por_pagar`** (de compras de 002 o de gastos) + `pago_cxp` (con
  retención en la fuente, campos sin cálculo fiscal) + `beneficiario` (acreedor de
  servicios que no es proveedor de mercadería).
- **`cobro_cxc`** — pagos de seguimiento contra la `cuenta_por_cobrar` de 009
  (reutilizada, no se duplica la tabla).
- **`gasto`** (pagado / por pagar) + **`gasto_recurrente`** (scheduler in-proceso).
- **`regla_asiento_automatico`** — motor de asiento automático por evento de negocio.
- **`periodo_contable`** — cierre; ajustes solo por asiento nuevo.

Reutiliza `sucursal`, `categoria_gasto`, `medio_pago`, `usuario` (001);
`cuenta_por_cobrar` (009); `orden_compra`, `proveedor` (002).

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-10
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------- plan de cuentas
_CUENTAS = [
    # (codigo, nombre, tipo, padre, imputable)
    ("1", "ACTIVO", "activo", None, False),
    ("1.1", "Activo Corriente", "activo", "1", False),
    ("1.1.01", "Caja y Bancos", "activo", "1.1", True),
    ("1.1.02", "Cuentas por Cobrar Clientes", "activo", "1.1", True),
    ("1.1.03", "Inventario", "activo", "1.1", True),
    ("2", "PASIVO", "pasivo", None, False),
    ("2.1", "Pasivo Corriente", "pasivo", "2", False),
    ("2.1.01", "Cuentas por Pagar Proveedores", "pasivo", "2.1", True),
    ("2.1.02", "Cuentas por Pagar Gastos", "pasivo", "2.1", True),
    ("3", "PATRIMONIO", "patrimonio", None, False),
    ("3.01", "Capital Social", "patrimonio", "3", True),
    ("4", "INGRESOS", "ingreso", None, False),
    ("4.01", "Ventas de Relojes y Piezas", "ingreso", "4", True),
    ("4.02", "Ingresos por Servicio Técnico", "ingreso", "4", True),
    ("5", "COSTO DE VENTAS", "gasto", None, False),
    ("5.01", "Costo de Ventas", "gasto", "5", True),
    ("5.02", "Costo de Servicio Técnico", "gasto", "5", True),
    ("6", "GASTOS", "gasto", None, False),
    ("6.01", "Gastos Local / Operativos", "gasto", "6", True),
    ("6.02", "Gastos de Personal", "gasto", "6", True),
    ("6.03", "Otros Gastos", "gasto", "6", True),
    ("6.04", "Pérdidas Extraordinarias", "gasto", "6", True),
]

# (evento, cuenta_debe, cuenta_haber, condicion|None)
_REGLAS = [
    ("venta_confirmada", "1.1.02", "4.01", None),
    ("ot_entregada", "1.1.02", "4.02", None),
    ("cobro_cxc", "1.1.01", "1.1.02", None),
    ("compra", "1.1.03", "2.1.01", None),
    ("pago_cxp", "2.1.01", "1.1.01", {"origen_tipo": "orden_compra"}),
    ("pago_cxp", "2.1.02", "1.1.01", {"origen_tipo": "gasto"}),
    ("gasto_pagado", "6.01", "1.1.01", {"categoria_tipo": "local_operativos"}),
    ("gasto_pagado", "6.02", "1.1.01", {"categoria_tipo": "personal"}),
    ("gasto_pagado", "6.03", "1.1.01", {"categoria_tipo": "otros"}),
    ("gasto_pagado", "6.04", "1.1.01", {"categoria_tipo": "mermas_perdidas"}),
    ("gasto_por_pagar", "6.01", "2.1.02", {"categoria_tipo": "local_operativos"}),
    ("gasto_por_pagar", "6.02", "2.1.02", {"categoria_tipo": "personal"}),
    ("gasto_por_pagar", "6.03", "2.1.02", {"categoria_tipo": "otros"}),
    ("gasto_por_pagar", "6.04", "2.1.02", {"categoria_tipo": "mermas_perdidas"}),
    ("merma_confirmada", "6.04", "1.1.03", None),
]

_CATEGORIAS_GASTO = [
    ("Arriendo", "local_operativos"), ("Luz", "local_operativos"), ("Agua", "local_operativos"),
    ("Internet / Wifi", "local_operativos"), ("Teléfono", "local_operativos"),
    ("Seguridad / Alarma", "local_operativos"), ("Limpieza", "local_operativos"),
    ("Seguros del local y mercancía", "local_operativos"), ("Impuestos municipales", "local_operativos"),
    ("Sueldos de técnicos", "personal"), ("Sueldos de vendedores/administrativos", "personal"),
    ("Aportes de seguridad social", "personal"), ("Bonos o comisiones", "personal"),
    ("Publicidad y marketing", "otros"), ("Materiales de oficina", "otros"),
    ("Mantenimiento de herramientas y equipos", "otros"), ("Capacitación de técnicos", "otros"),
    ("Transporte / envíos", "otros"), ("Comisiones bancarias y de tarjetas", "otros"),
    ("Mermas y pérdidas", "mermas_perdidas"),
]


def upgrade() -> None:
    op.create_table(
        "cuenta_contable",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("tipo", sa.String(length=12), nullable=False),
        sa.Column("cuenta_padre_id", sa.BigInteger(), nullable=True),
        sa.Column("imputable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "tipo in ('activo','pasivo','patrimonio','ingreso','gasto')", name="ck_cuenta_contable_tipo"
        ),
        sa.UniqueConstraint("codigo", name="uq_cuenta_contable_codigo"),
        sa.ForeignKeyConstraint(["cuenta_padre_id"], ["cuenta_contable.id"], name="fk_cc_padre", ondelete="SET NULL"),
    )

    op.create_table(
        "periodo_contable",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="abierto"),
        sa.Column("cerrado_por", sa.BigInteger(), nullable=True),
        sa.Column("cerrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado in ('abierto','cerrado')", name="ck_periodo_estado"),
        sa.CheckConstraint("fecha_fin >= fecha_inicio", name="ck_periodo_fechas"),
        sa.ForeignKeyConstraint(["cerrado_por"], ["usuario.id"], name="fk_periodo_cerrado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_periodo_fechas", "periodo_contable", ["fecha_inicio", "fecha_fin"])

    op.create_table(
        "asiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("glosa", sa.String(length=255), nullable=False),
        sa.Column("origen", sa.String(length=24), nullable=False, server_default="manual"),
        sa.Column("origen_id", sa.BigInteger(), nullable=True),
        sa.Column("ajuste_de_asiento_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "origen in ('manual','venta','ot','compra','gasto','merma','cobro','pago','ajuste')",
            name="ck_asiento_origen",
        ),
        sa.ForeignKeyConstraint(["ajuste_de_asiento_id"], ["asiento.id"], name="fk_asiento_ajuste", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_asiento_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_asiento_fecha", "asiento", ["fecha"])
    op.create_index("ix_asiento_origen", "asiento", ["origen", "origen_id"])

    op.create_table(
        "linea_asiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("asiento_id", sa.BigInteger(), nullable=False),
        sa.Column("cuenta_contable_id", sa.BigInteger(), nullable=False),
        sa.Column("debe", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("haber", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["asiento_id"], ["asiento.id"], name="fk_la_asiento", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cuenta_contable_id"], ["cuenta_contable.id"], name="fk_la_cuenta", ondelete="RESTRICT"),
    )
    op.create_index("ix_linea_asiento_cuenta", "linea_asiento", ["cuenta_contable_id"])
    op.create_index("ix_linea_asiento_asiento", "linea_asiento", ["asiento_id"])

    op.create_table(
        "caja",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False, server_default="Caja principal"),
        sa.UniqueConstraint("sucursal_id", name="uq_caja_sucursal"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_caja_sucursal", ondelete="CASCADE"),
    )

    op.create_table(
        "sesion_caja",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("caja_id", sa.BigInteger(), nullable=False),
        sa.Column("abierta_por", sa.BigInteger(), nullable=True),
        sa.Column("saldo_inicial", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("abierta_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cerrada_por", sa.BigInteger(), nullable=True),
        sa.Column("efectivo_contado", sa.Numeric(14, 2), nullable=True),
        sa.Column("efectivo_esperado", sa.Numeric(14, 2), nullable=True),
        sa.Column("diferencia", sa.Numeric(14, 2), nullable=True),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="abierta"),
        sa.CheckConstraint("estado in ('abierta','cerrada')", name="ck_sesion_caja_estado"),
        sa.ForeignKeyConstraint(["caja_id"], ["caja.id"], name="fk_sesion_caja", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["abierta_por"], ["usuario.id"], name="fk_sesion_abierta_por", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cerrada_por"], ["usuario.id"], name="fk_sesion_cerrada_por", ondelete="SET NULL"),
    )
    op.create_index("ix_sesion_caja_estado", "sesion_caja", ["caja_id", "estado"])

    op.create_table(
        "movimiento_caja",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("sesion_caja_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("medio_pago_id", sa.BigInteger(), nullable=True),
        sa.Column("documento_tipo", sa.String(length=24), nullable=True),
        sa.Column("documento_id", sa.BigInteger(), nullable=True),
        sa.Column("nota", sa.String(length=255), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo in ('entrada','salida')", name="ck_movimiento_caja_tipo"),
        sa.CheckConstraint("monto > 0", name="ck_movimiento_caja_monto"),
        sa.ForeignKeyConstraint(["sesion_caja_id"], ["sesion_caja.id"], name="fk_mc_sesion", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["medio_pago_id"], ["medio_pago.id"], name="fk_mc_medio", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_mc_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_movimiento_caja_sesion", "movimiento_caja", ["sesion_caja_id"])

    op.create_table(
        "beneficiario",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("identificacion", sa.String(length=20), nullable=True),
        sa.Column("tipo_servicio", sa.String(length=60), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_beneficiario_nombre"),
    )

    op.create_table(
        "cuenta_por_pagar",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("origen_tipo", sa.String(length=12), nullable=False),
        sa.Column("orden_compra_id", sa.BigInteger(), nullable=True),
        sa.Column("gasto_id", sa.BigInteger(), nullable=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=True),
        sa.Column("beneficiario_id", sa.BigInteger(), nullable=True),
        sa.Column("monto_original", sa.Numeric(14, 2), nullable=False),
        sa.Column("saldo", sa.Numeric(14, 2), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="pendiente"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("origen_tipo in ('orden_compra','gasto')", name="ck_cxp_origen_tipo"),
        sa.CheckConstraint("estado in ('pendiente','saldada','anulada')", name="ck_cxp_estado"),
        sa.CheckConstraint(
            "(orden_compra_id is not null)::int + (gasto_id is not null)::int = 1", name="ck_cxp_un_origen"
        ),
        sa.CheckConstraint(
            "(proveedor_id is not null)::int + (beneficiario_id is not null)::int = 1", name="ck_cxp_una_contraparte"
        ),
        sa.ForeignKeyConstraint(["orden_compra_id"], ["orden_compra.id"], name="fk_cxp_oc", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_cxp_proveedor", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["beneficiario_id"], ["beneficiario.id"], name="fk_cxp_beneficiario", ondelete="RESTRICT"),
    )
    op.create_index("ix_cxp_estado", "cuenta_por_pagar", ["estado"])
    op.create_index("ix_cxp_origen", "cuenta_por_pagar", ["origen_tipo", "orden_compra_id", "gasto_id"])

    op.create_table(
        "cheque",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("banco", sa.String(length=80), nullable=True),
        sa.Column("numero", sa.String(length=40), nullable=True),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=14), nullable=False, server_default="en_cartera"),
        sa.Column("cliente_id", sa.BigInteger(), nullable=True),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=True),
        sa.Column("beneficiario_id", sa.BigInteger(), nullable=True),
        sa.Column("documento_origen_tipo", sa.String(length=12), nullable=True),
        sa.Column("documento_origen_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo in ('emitido','recibido')", name="ck_cheque_tipo"),
        sa.CheckConstraint(
            "estado in ('en_cartera','depositado','cobrado','protestado')", name="ck_cheque_estado"
        ),
        sa.CheckConstraint(
            "documento_origen_tipo is null or documento_origen_tipo in ('venta','orden_trabajo','cobro_cxc')",
            name="ck_cheque_origen_tipo",
        ),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_cheque_proveedor", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["beneficiario_id"], ["beneficiario.id"], name="fk_cheque_beneficiario", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_cheque_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_cheque_tipo_estado", "cheque", ["tipo", "estado"])

    op.create_table(
        "cobro_cxc",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("cxc_id", sa.BigInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("medio_pago_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cheque_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("monto > 0", name="ck_cobro_cxc_monto"),
        sa.ForeignKeyConstraint(["cxc_id"], ["cuenta_por_cobrar.id"], name="fk_cobro_cxc", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medio_pago_id"], ["medio_pago.id"], name="fk_cobro_medio", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cheque_id"], ["cheque.id"], name="fk_cobro_cheque", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_cobro_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_cobro_cxc_cxc", "cobro_cxc", ["cxc_id"])

    op.create_table(
        "pago_cxp",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("cxp_id", sa.BigInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("medio_pago_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cheque_id", sa.BigInteger(), nullable=True),
        sa.Column("retencion_fuente", postgresql.JSONB(), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("monto > 0", name="ck_pago_cxp_monto"),
        sa.ForeignKeyConstraint(["cxp_id"], ["cuenta_por_pagar.id"], name="fk_pago_cxp", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medio_pago_id"], ["medio_pago.id"], name="fk_pago_cxp_medio", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cheque_id"], ["cheque.id"], name="fk_pago_cxp_cheque", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_pago_cxp_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_pago_cxp_cxp", "pago_cxp", ["cxp_id"])

    op.create_table(
        "gasto_recurrente",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("categoria_gasto_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=True),
        sa.Column("beneficiario_id", sa.BigInteger(), nullable=True),
        sa.Column("descripcion", sa.String(length=160), nullable=False),
        sa.Column("monto_estimado", sa.Numeric(14, 2), nullable=False),
        sa.Column("frecuencia", sa.String(length=12), nullable=False),
        sa.Column("proxima_generacion", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="activo"),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("frecuencia in ('mensual','bimestral','trimestral')", name="ck_gr_frecuencia"),
        sa.CheckConstraint("estado in ('activo','pausado','cancelado')", name="ck_gr_estado"),
        sa.ForeignKeyConstraint(["categoria_gasto_id"], ["categoria_gasto.id"], name="fk_gr_categoria", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_gr_sucursal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_gr_proveedor", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["beneficiario_id"], ["beneficiario.id"], name="fk_gr_beneficiario", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_gr_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_gr_proxima", "gasto_recurrente", ["estado", "proxima_generacion"])

    op.create_table(
        "gasto",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("sucursal_id", sa.BigInteger(), nullable=False),
        sa.Column("categoria_gasto_id", sa.BigInteger(), nullable=False),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=True),
        sa.Column("beneficiario_id", sa.BigInteger(), nullable=True),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("documento_soporte_objeto", sa.String(length=255), nullable=True),
        sa.Column("estado_pago", sa.String(length=10), nullable=True),
        sa.Column("medio_pago_id", sa.BigInteger(), nullable=True),
        sa.Column("movimiento_caja_id", sa.BigInteger(), nullable=True),
        sa.Column("cuenta_por_pagar_id", sa.BigInteger(), nullable=True),
        sa.Column("gasto_recurrente_id", sa.BigInteger(), nullable=True),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="confirmado"),
        sa.Column("asiento_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("estado_pago is null or estado_pago in ('pagado','por_pagar')", name="ck_gasto_estado_pago"),
        sa.CheckConstraint("estado in ('borrador','confirmado')", name="ck_gasto_estado"),
        sa.CheckConstraint("monto >= 0", name="ck_gasto_monto"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_gasto_sucursal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["categoria_gasto_id"], ["categoria_gasto.id"], name="fk_gasto_categoria", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], name="fk_gasto_proveedor", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["beneficiario_id"], ["beneficiario.id"], name="fk_gasto_beneficiario", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["medio_pago_id"], ["medio_pago.id"], name="fk_gasto_medio", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["movimiento_caja_id"], ["movimiento_caja.id"], name="fk_gasto_mov_caja", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cuenta_por_pagar_id"], ["cuenta_por_pagar.id"], name="fk_gasto_cxp", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gasto_recurrente_id"], ["gasto_recurrente.id"], name="fk_gasto_recurrente", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["asiento_id"], ["asiento.id"], name="fk_gasto_asiento", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], name="fk_gasto_creado_por", ondelete="SET NULL"),
    )
    op.create_index("ix_gasto_sucursal_fecha", "gasto", ["sucursal_id", "fecha"])
    op.create_index("ix_gasto_estado", "gasto", ["estado"])

    # FK diferida: cuenta_por_pagar.gasto_id -> gasto.id (gasto se crea después de cuenta_por_pagar en el flujo)
    op.create_foreign_key("fk_cxp_gasto", "cuenta_por_pagar", "gasto", ["gasto_id"], ["id"], ondelete="RESTRICT")

    op.create_table(
        "regla_asiento_automatico",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("evento", sa.String(length=24), nullable=False),
        sa.Column("cuenta_debe_id", sa.BigInteger(), nullable=False),
        sa.Column("cuenta_haber_id", sa.BigInteger(), nullable=False),
        sa.Column("condicion", postgresql.JSONB(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["cuenta_debe_id"], ["cuenta_contable.id"], name="fk_regla_debe", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cuenta_haber_id"], ["cuenta_contable.id"], name="fk_regla_haber", ondelete="RESTRICT"),
    )
    op.create_index("ix_regla_evento", "regla_asiento_automatico", ["evento", "activa"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION cronos_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% es append-only (solo INSERT)', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for t in ("linea_asiento", "cobro_cxc", "pago_cxp"):
        op.execute(
            f"CREATE TRIGGER trg_{t}_append_only BEFORE UPDATE OR DELETE ON {t} "
            f"FOR EACH ROW EXECUTE FUNCTION cronos_append_only();"
        )

    # ---------------------------------------------------------------- semillas
    bind = op.get_bind()
    ids: dict[str, int] = {}
    for codigo, nombre, tipo, padre_codigo, imputable in _CUENTAS:
        padre_id = ids.get(padre_codigo) if padre_codigo else None
        row = bind.execute(
            sa.text(
                "INSERT INTO cuenta_contable (codigo, nombre, tipo, cuenta_padre_id, imputable) "
                "VALUES (:codigo, :nombre, :tipo, :padre, :imputable) RETURNING id"
            ),
            {"codigo": codigo, "nombre": nombre, "tipo": tipo, "padre": padre_id, "imputable": imputable},
        ).first()
        ids[codigo] = row[0]

    for evento, debe_cod, haber_cod, condicion in _REGLAS:
        bind.execute(
            sa.text(
                "INSERT INTO regla_asiento_automatico (evento, cuenta_debe_id, cuenta_haber_id, condicion) "
                "VALUES (:evento, :debe, :haber, CAST(:condicion AS jsonb))"
            ),
            {
                "evento": evento, "debe": ids[debe_cod], "haber": ids[haber_cod],
                "condicion": json.dumps(condicion) if condicion is not None else None,
            },
        )

    cat_tabla = sa.table(
        "categoria_gasto", sa.column("nombre", sa.String), sa.column("tipo", sa.String)
    )
    op.bulk_insert(cat_tabla, [{"nombre": n, "tipo": t} for n, t in _CATEGORIAS_GASTO])


def downgrade() -> None:
    op.drop_constraint("fk_cxp_gasto", "cuenta_por_pagar", type_="foreignkey")
    for t in ("linea_asiento", "cobro_cxc", "pago_cxp"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{t}_append_only ON {t}")
    op.execute(
        "DELETE FROM categoria_gasto WHERE nombre IN (" + ",".join(f"'{n}'" for n, _ in _CATEGORIAS_GASTO) + ")"
    )
    op.drop_table("regla_asiento_automatico")
    op.drop_table("gasto")
    op.drop_table("gasto_recurrente")
    op.drop_table("pago_cxp")
    op.drop_table("cobro_cxc")
    op.drop_table("cheque")
    op.drop_table("cuenta_por_pagar")
    op.drop_table("beneficiario")
    op.drop_table("movimiento_caja")
    op.drop_table("sesion_caja")
    op.drop_table("caja")
    op.drop_table("linea_asiento")
    op.drop_table("asiento")
    op.drop_table("periodo_contable")
    op.drop_table("cuenta_contable")
