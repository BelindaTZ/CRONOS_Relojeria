"""Acceso a datos del módulo `notificaciones` (feature 014). Sin lógica de
negocio (Principio X) — eso vive en `service.py`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from notificaciones.models import Envio, PreferenciaComunicacion
from shared.models import PlantillaEmail


# ------------------------------------------------------------------- envío
def por_clave_idempotencia(db: Session, clave: str) -> Envio | None:
    return db.scalars(select(Envio).where(Envio.clave_idempotencia == clave)).first()


def crear_envio(db: Session, **campos) -> Envio:
    e = Envio(**campos)
    db.add(e)
    db.flush()
    return e


def obtener_envio(db: Session, envio_id: int) -> Envio | None:
    return db.get(Envio, envio_id)


def pendientes(db: Session, *, ahora: datetime, limite: int = 20) -> list[Envio]:
    return list(
        db.scalars(
            select(Envio)
            .where(Envio.estado == "encolado", Envio.proxima_ejecucion <= ahora)
            .order_by(Envio.proxima_ejecucion)
            .limit(limite)
        )
    )


def listar_envios(
    db: Session, *, tipo: str | None, estado: str | None, cliente_id: int | None,
    disparo_origen_id: int | None, offset: int, limit: int,
) -> tuple[list[Envio], int]:
    stmt = select(Envio)
    if tipo:
        stmt = stmt.where(Envio.tipo == tipo)
    if estado:
        stmt = stmt.where(Envio.estado == estado)
    if cliente_id:
        stmt = stmt.where(Envio.cliente_id == cliente_id)
    if disparo_origen_id:
        stmt = stmt.where(Envio.disparo_origen_id == disparo_origen_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Envio.creado_en.desc()).offset(offset).limit(limit)))
    return filas, total


def por_proveedor_message_id_prefijo(db: Session, message_id: str) -> Envio | None:
    """SendGrid añade un sufijo por destinatario al `X-Message-Id` original en
    los eventos de webhook — se concilia por prefijo (research D4)."""
    base = message_id.split(".")[0]
    return db.scalars(select(Envio).where(Envio.proveedor_message_id.like(f"{base}%"))).first()


# --------------------------------------------------------------- preferencia
def preferencia(db: Session, cliente_id: int, tipo_comunicacion: str) -> PreferenciaComunicacion | None:
    return db.scalars(
        select(PreferenciaComunicacion).where(
            PreferenciaComunicacion.cliente_id == cliente_id,
            PreferenciaComunicacion.tipo_comunicacion == tipo_comunicacion,
        )
    ).first()


def preferencias_de(db: Session, cliente_id: int) -> list[PreferenciaComunicacion]:
    return list(db.scalars(select(PreferenciaComunicacion).where(PreferenciaComunicacion.cliente_id == cliente_id)))


# ---------------------------------------------------------------- plantillas
def plantilla_activa(db: Session, tipo: str) -> PlantillaEmail | None:
    return db.scalars(select(PlantillaEmail).where(PlantillaEmail.tipo == tipo, PlantillaEmail.activa.is_(True))).first()


def historial_plantilla(db: Session, tipo: str) -> list[PlantillaEmail]:
    return list(db.scalars(select(PlantillaEmail).where(PlantillaEmail.tipo == tipo).order_by(PlantillaEmail.version.desc())))
