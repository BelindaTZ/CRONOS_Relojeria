"""Modelos ORM del módulo `notificaciones` (feature 014). Esquema físico creado
a mano por la migración `0030_notificaciones`. Reutiliza `cliente` (006),
`usuario` (001) solo por FK cruda (sin import — Principio X).

`PlantillaEmail` NO vive aquí — vive en `shared/models.py` porque
`shared/correo/service.py` la lee al renderizar cualquier correo del sistema
(ver el docstring de esa clase)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class Envio(_PK, Base):
    __tablename__ = "envio"
    tipo: Mapped[str] = mapped_column(String(30))
    destinatario_email: Mapped[str | None] = mapped_column(String(160))
    cliente_id: Mapped[int | None] = mapped_column(BigInteger)
    usuario_id: Mapped[int | None] = mapped_column(BigInteger)
    disparo_origen_tipo: Mapped[str] = mapped_column(String(24))
    disparo_origen_id: Mapped[int] = mapped_column(BigInteger)
    hito: Mapped[str] = mapped_column(String(40))
    clave_idempotencia: Mapped[str] = mapped_column(String(80))
    contexto: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    estado: Mapped[str] = mapped_column(String(16), server_default="encolado")
    motivo_estado: Mapped[str | None] = mapped_column(String(120))
    intentos: Mapped[int] = mapped_column(Integer, server_default="0")
    max_reintentos: Mapped[int] = mapped_column(Integer, server_default="5")
    proxima_ejecucion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    proveedor_message_id: Mapped[str | None] = mapped_column(String(120))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PreferenciaComunicacion(_PK, Base):
    __tablename__ = "preferencia_comunicacion"
    cliente_id: Mapped[int] = mapped_column(BigInteger)
    tipo_comunicacion: Mapped[str] = mapped_column(String(30))
    opt_in: Mapped[bool] = mapped_column(Boolean, server_default="true")
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventoWebhookEmail(_PK, Base):
    """Append-only (trigger `cronos_append_only`, migración 0030)."""

    __tablename__ = "evento_webhook_email"
    proveedor_message_id: Mapped[str | None] = mapped_column(String(120))
    evento: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSONB)
    recibido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
