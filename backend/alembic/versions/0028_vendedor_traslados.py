"""Agrega multisucursal:crear+consultar al rol Vendedor.

El flujo principal (spec §4.1/§4.4) exige que el vendedor pueda iniciar un
traslado cuando localiza el modelo pedido en otra sucursal vía la búsqueda
global de inventario (`GET /relojes/buscar-global`, migración 0027). La
ejecución física del traslado (enviar/recibir el envío) sigue siendo
responsabilidad del Gerente de Sucursal — Vendedor NO recibe
`multisucursal:editar`, solo `crear` (para levantar la solicitud) y
`consultar` (para ver su estado).

0024 sembró la matriz de Vendedor sin el módulo `multisucursal` porque en ese
momento el flujo de traslado-desde-venta aún no existía; esta migración
agrega el módulo sin tocar el resto de su matriz.

Revision ID: 0028
Revises: 0027
Create Date: 2026-09-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OPERACIONES = ["crear", "consultar"]


def upgrade() -> None:
    bind = op.get_bind()
    rol = bind.execute(sa.text("SELECT id FROM rol WHERE nombre = 'Vendedor'")).first()
    if rol is None:
        return  # entorno sin el seed de 0024 (p.ej. algún test aislado); nada que hacer
    rol_id = rol[0]
    modulo_id = bind.execute(sa.text("SELECT id FROM modulo WHERE clave = 'multisucursal'")).scalar()

    ya_tiene = bind.execute(
        sa.text("SELECT 1 FROM permiso_modulo WHERE rol_id = :rid AND modulo_id = :mid"),
        {"rid": rol_id, "mid": modulo_id},
    ).first()
    if not ya_tiene:
        bind.execute(
            sa.text("INSERT INTO permiso_modulo (rol_id, modulo_id) VALUES (:rid, :mid)"),
            {"rid": rol_id, "mid": modulo_id},
        )

    operacion_ids = dict(bind.execute(sa.text("SELECT clave, id FROM operacion")).all())
    for clave in _OPERACIONES:
        oid = operacion_ids[clave]
        existe = bind.execute(
            sa.text(
                "SELECT 1 FROM permiso_operacion WHERE rol_id = :rid AND modulo_id = :mid AND operacion_id = :oid"
            ),
            {"rid": rol_id, "mid": modulo_id, "oid": oid},
        ).first()
        if not existe:
            bind.execute(
                sa.text(
                    "INSERT INTO permiso_operacion (rol_id, modulo_id, operacion_id) "
                    "VALUES (:rid, :mid, :oid)"
                ),
                {"rid": rol_id, "mid": modulo_id, "oid": oid},
            )


def downgrade() -> None:
    bind = op.get_bind()
    rol = bind.execute(sa.text("SELECT id FROM rol WHERE nombre = 'Vendedor'")).first()
    if rol is None:
        return
    rol_id = rol[0]
    modulo_id = bind.execute(sa.text("SELECT id FROM modulo WHERE clave = 'multisucursal'")).scalar()
    bind.execute(
        sa.text("DELETE FROM permiso_operacion WHERE rol_id = :rid AND modulo_id = :mid"),
        {"rid": rol_id, "mid": modulo_id},
    )
    bind.execute(
        sa.text("DELETE FROM permiso_modulo WHERE rol_id = :rid AND modulo_id = :mid"),
        {"rid": rol_id, "mid": modulo_id},
    )
