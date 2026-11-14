"""Modelo ORM de la capacidad compartida `shared/pagos` (feature 008).

Tabla física `pago` creada a mano por la migración `0020_servicio_tecnico`.
Es **append-only** (trigger en DB): una anulación es una bandera, nunca un DELETE.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class Pago(Base):
    __tablename__ = "pago"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    documento_tipo: Mapped[str] = mapped_column(String(16))   # "orden_trabajo" | "venta"
    documento_id: Mapped[int] = mapped_column(BigInteger)
    medio_pago_id: Mapped[int] = mapped_column(ForeignKey("medio_pago.id", ondelete="RESTRICT"))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    referencia: Mapped[str | None] = mapped_column(String(80))
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
