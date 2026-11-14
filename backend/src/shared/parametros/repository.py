"""Acceso a datos de `parametro_configuracion`. Historial solo por INSERT."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import ParametroConfiguracion


def vigente(
    db: Session,
    clave: str,
    *,
    ambito_tipo: str = "global",
    ambito_ref: str | None = None,
    en_fecha: datetime | None = None,
) -> ParametroConfiguracion | None:
    momento = en_fecha or datetime.now(timezone.utc)
    stmt = (
        select(ParametroConfiguracion)
        .where(
            ParametroConfiguracion.clave == clave,
            ParametroConfiguracion.ambito_tipo == ambito_tipo,
            ParametroConfiguracion.ambito_ref.is_(ambito_ref)
            if ambito_ref is None
            else ParametroConfiguracion.ambito_ref == ambito_ref,
            ParametroConfiguracion.vigente_desde <= momento,
        )
        .order_by(ParametroConfiguracion.vigente_desde.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def historial(
    db: Session, clave: str, *, ambito_tipo: str = "global", ambito_ref: str | None = None
) -> list[ParametroConfiguracion]:
    stmt = (
        select(ParametroConfiguracion)
        .where(
            ParametroConfiguracion.clave == clave,
            ParametroConfiguracion.ambito_tipo == ambito_tipo,
            ParametroConfiguracion.ambito_ref.is_(ambito_ref)
            if ambito_ref is None
            else ParametroConfiguracion.ambito_ref == ambito_ref,
        )
        .order_by(ParametroConfiguracion.vigente_desde.desc())
    )
    return list(db.scalars(stmt))


def insertar(
    db: Session,
    *,
    clave: str,
    tipo: str,
    valor,
    ambito_tipo: str,
    ambito_ref: str | None,
    vigente_desde: datetime,
    creado_por: int | None,
) -> ParametroConfiguracion:
    row = ParametroConfiguracion(
        clave=clave,
        tipo=tipo,
        valor=valor,
        ambito_tipo=ambito_tipo,
        ambito_ref=ambito_ref,
        vigente_desde=vigente_desde,
        creado_por=creado_por,
    )
    db.add(row)
    db.flush()
    return row
