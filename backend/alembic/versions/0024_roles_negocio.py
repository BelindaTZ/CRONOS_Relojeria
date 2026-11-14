"""Siembra los 5 roles de negocio de la Constitución §3 (además de "Gerencia
General", que la crea `scripts/seed_gerencia.py`): Gerente de Sucursal, Vendedor,
Técnico, Técnico Jefe, Contador — con una matriz de permisos por defecto
(módulo × operación) razonable según la tabla ilustrativa de §3.1 de
`docs/especificacion_sistema_relojeria.md`, extendida a los módulos que la
tabla no cubre explícitamente.

Es solo el PUNTO DE PARTIDA: Gerencia General puede ajustar cualquier matriz
desde Sistema → Roles en cualquier momento (el propio sembrado no es especial,
usa las mismas tablas `permiso_modulo`/`permiso_operacion` que esa pantalla).

Si el rol ya existe (p.ej. un "Vendedor" creado a mano en una sesión de prueba
anterior), se reconcilia: se actualiza la descripción y se REEMPLAZA su matriz
de permisos por la canónica de abajo (idempotente).

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# módulo -> operaciones concedidas; un módulo ausente = sin acceso.
_MATRICES: dict[str, dict[str, list[str]]] = {
    "Gerente de Sucursal": {
        "citas": ["crear", "consultar", "editar", "eliminar"],
        "proveedores": ["crear", "consultar", "editar"],
        "tecnicos": ["consultar"],
        "inventario_relojes": ["crear", "consultar", "editar"],
        "piezas": ["crear", "consultar", "editar"],
        "lubricacion": ["consultar"],
        "ordenes_trabajo": ["crear", "consultar", "editar", "eliminar"],
        "clientes_fidelizacion": ["crear", "consultar", "editar"],
        "multisucursal": ["crear", "consultar", "editar"],
        "contable": ["consultar"],
        "reportes": ["consultar"],
        "mermas": ["crear", "consultar", "editar"],
        "ventas": ["crear", "consultar", "editar"],
        "notificaciones": ["consultar"],
    },
    "Vendedor": {
        "citas": ["crear", "consultar", "editar"],
        "inventario_relojes": ["consultar"],
        "piezas": ["consultar"],
        "ordenes_trabajo": ["crear", "consultar"],
        "clientes_fidelizacion": ["crear", "consultar", "editar"],
        "mermas": ["consultar"],
        "ventas": ["crear", "consultar", "editar"],
    },
    "Técnico": {
        "citas": ["consultar"],
        "tecnicos": ["consultar"],
        "inventario_relojes": ["consultar"],
        "piezas": ["consultar"],
        "lubricacion": ["consultar", "editar"],
        "ordenes_trabajo": ["consultar", "editar"],  # "solo las propias" se aplica en el service, no aquí
        "clientes_fidelizacion": ["consultar"],
        "mermas": ["crear", "consultar"],
    },
    "Técnico Jefe": {
        "citas": ["consultar", "editar"],
        "proveedores": ["consultar"],
        "tecnicos": ["crear", "consultar", "editar"],
        "inventario_relojes": ["consultar"],
        "piezas": ["consultar", "editar"],
        "lubricacion": ["crear", "consultar", "editar"],
        "ordenes_trabajo": ["crear", "consultar", "editar", "eliminar"],
        "clientes_fidelizacion": ["consultar"],
        "reportes": ["consultar"],
        "mermas": ["crear", "consultar", "editar"],
    },
    "Contador": {
        "proveedores": ["consultar"],
        "inventario_relojes": ["consultar"],
        "piezas": ["consultar"],
        "ordenes_trabajo": ["consultar"],
        "clientes_fidelizacion": ["consultar"],
        "contable": ["crear", "consultar", "editar", "eliminar"],
        "reportes": ["consultar"],
        "mermas": ["consultar"],
        "ventas": ["consultar"],
    },
}

_DESCRIPCIONES = {
    "Gerente de Sucursal": "Gestión operativa de su sucursal, reportes locales",
    "Vendedor": "Vendedor / Encargado de mostrador — citas, ventas, atención al cliente",
    "Técnico": "Ejecución de órdenes de trabajo, registro de lubricación e insumos usados",
    "Técnico Jefe": "Técnico Jefe / Maestro relojero — supervisión técnica, asignación, control de calidad",
    "Contador": "Contador / Administrativo — módulo contable, cuentas por cobrar/pagar, gastos",
}


def upgrade() -> None:
    bind = op.get_bind()

    modulo_ids = dict(bind.execute(sa.text("SELECT clave, id FROM modulo")).all())
    operacion_ids = dict(bind.execute(sa.text("SELECT clave, id FROM operacion")).all())

    for nombre, matriz in _MATRICES.items():
        row = bind.execute(
            sa.text(
                "INSERT INTO rol (nombre, descripcion) VALUES (:nombre, :desc) "
                "ON CONFLICT (nombre) DO UPDATE SET descripcion = EXCLUDED.descripcion "
                "RETURNING id"
            ),
            {"nombre": nombre, "desc": _DESCRIPCIONES[nombre]},
        ).first()
        rol_id = row[0]

        # Reemplazo limpio (idempotente ante un rol homónimo creado a mano antes).
        bind.execute(sa.text("DELETE FROM permiso_operacion WHERE rol_id = :rid"), {"rid": rol_id})
        bind.execute(sa.text("DELETE FROM permiso_modulo WHERE rol_id = :rid"), {"rid": rol_id})

        for modulo_clave, operaciones in matriz.items():
            bind.execute(
                sa.text("INSERT INTO permiso_modulo (rol_id, modulo_id) VALUES (:rid, :mid)"),
                {"rid": rol_id, "mid": modulo_ids[modulo_clave]},
            )
            for op_clave in operaciones:
                bind.execute(
                    sa.text(
                        "INSERT INTO permiso_operacion (rol_id, modulo_id, operacion_id) "
                        "VALUES (:rid, :mid, :oid)"
                    ),
                    {"rid": rol_id, "mid": modulo_ids[modulo_clave], "oid": operacion_ids[op_clave]},
                )


def downgrade() -> None:
    op.execute(
        "DELETE FROM rol WHERE nombre IN (" + ",".join(f"'{n}'" for n in _MATRICES) + ")"
    )
