"""Entorno de Alembic para CRONOS.

Toma la URL de conexión de `DATABASE_URL` (vía `shared.config`) y el metadata de
`shared.database.Base`. Cada feature 001+ importa aquí sus modelos para que el
`target_metadata` esté completo en autogeneración (no se usa autogen en 000).
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from shared.config import get_settings
from shared.database import Base

# Importa el metadata de los modelos ORM del sustrato central (feature 001+).
# Las migraciones se escriben a mano; esto solo mantiene `Base.metadata` completo
# para tests que hagan create_all y como referencia.
from shared import models as _models  # noqa: F401
from proveedores import models as _proveedores_models  # noqa: F401
from inventario import models as _inventario_models  # noqa: F401
from piezas import models as _piezas_models  # noqa: F401
from traslados import models as _traslados_models  # noqa: F401
from tecnicos import models as _tecnicos_models  # noqa: F401
from clientes import models as _clientes_models  # noqa: F401
from citas import models as _citas_models  # noqa: F401
from shared.pagos import models as _pagos_models  # noqa: F401
from lubricacion import models as _lubricacion_models  # noqa: F401
from servicio_tecnico import models as _servicio_tecnico_models  # noqa: F401
from ventas import models as _ventas_models  # noqa: F401
from contabilidad import models as _contabilidad_models  # noqa: F401
from mermas import models as _mermas_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
