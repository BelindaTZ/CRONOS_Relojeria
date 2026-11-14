"""Modelos ORM del módulo `clientes` (feature 006).

Esquema físico creado a mano por la migración `0017_clientes`. Reutiliza
`usuario` (001) y `parametro_configuracion` (001) solo por FK / lectura.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class NivelFidelizacion(_PK, Base):
    __tablename__ = "nivel_fidelizacion"
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    orden: Mapped[int] = mapped_column(Integer)
    beneficios: Mapped[dict | None] = mapped_column(JSONB)
    es_base: Mapped[bool] = mapped_column(Boolean, server_default="false")
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reglas: Mapped[list["ReglaNivel"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ReglaNivel.vigente_desde"
    )


class ReglaNivel(_PK, Base):
    __tablename__ = "regla_nivel"
    nivel_fidelizacion_id: Mapped[int] = mapped_column(ForeignKey("nivel_fidelizacion.id", ondelete="CASCADE"))
    criterio: Mapped[str] = mapped_column(String(20))
    ventana_meses: Mapped[int] = mapped_column(Integer, server_default="12")
    umbral_monto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    umbral_frecuencia: Mapped[int | None] = mapped_column(Integer)
    vigente_desde: Mapped[date] = mapped_column(Date)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cliente(_PK, Base):
    __tablename__ = "cliente"
    tipo: Mapped[str] = mapped_column(String(10), server_default="natural")
    identificacion: Mapped[str] = mapped_column(String(20), unique=True)
    numero_afiliado: Mapped[str] = mapped_column(String(16), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    direccion: Mapped[str | None] = mapped_column(String(255))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    preferencias: Mapped[dict | None] = mapped_column(JSONB)
    notas: Mapped[str | None] = mapped_column(Text)
    nivel_fidelizacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("nivel_fidelizacion.id", ondelete="SET NULL")
    )
    es_consumidor_final: Mapped[bool] = mapped_column(Boolean, server_default="false")
    estado: Mapped[str] = mapped_column(String(12), server_default="activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentimientoDatos(_PK, Base):
    __tablename__ = "consentimiento_datos"
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="CASCADE"))
    aceptado: Mapped[bool] = mapped_column(Boolean)
    version_texto: Mapped[int] = mapped_column(Integer)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistorialNivelCliente(_PK, Base):
    __tablename__ = "historial_nivel_cliente"
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="CASCADE"))
    nivel_anterior_id: Mapped[int | None] = mapped_column(ForeignKey("nivel_fidelizacion.id", ondelete="SET NULL"))
    nivel_nuevo_id: Mapped[int] = mapped_column(ForeignKey("nivel_fidelizacion.id", ondelete="SET NULL"))
    hecho_disparador: Mapped[str] = mapped_column(String(30))
    documento_id: Mapped[int | None] = mapped_column(BigInteger)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Descuento(_PK, Base):
    __tablename__ = "descuento"
    nombre: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(10))
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    alcance: Mapped[str] = mapped_column(String(10), server_default="tienda")
    alcance_ref: Mapped[str | None] = mapped_column(String(80))
    segmento: Mapped[str] = mapped_column(String(10), server_default="todos")
    segmento_ref: Mapped[str | None] = mapped_column(String(80))
    vigencia_inicio: Mapped[date | None] = mapped_column(Date)
    vigencia_fin: Mapped[date | None] = mapped_column(Date)
    evento: Mapped[str | None] = mapped_column(String(24))
    limite_uso: Mapped[str] = mapped_column(String(12), server_default="global")
    max_usos: Mapped[int | None] = mapped_column(Integer)
    usos: Mapped[int] = mapped_column(Integer, server_default="0")
    estado: Mapped[str] = mapped_column(String(10), server_default="activo")
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cupon(_PK, Base):
    __tablename__ = "cupon"
    codigo: Mapped[str] = mapped_column(String(24), unique=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(10))
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    alcance: Mapped[str] = mapped_column(String(10), server_default="tienda")
    alcance_ref: Mapped[str | None] = mapped_column(String(80))
    vigencia_inicio: Mapped[date | None] = mapped_column(Date)
    vigencia_fin: Mapped[date | None] = mapped_column(Date)
    evento: Mapped[str | None] = mapped_column(String(24))
    limite_uso: Mapped[str] = mapped_column(String(12), server_default="una_vez")
    max_usos: Mapped[int | None] = mapped_column(Integer)
    usos: Mapped[int] = mapped_column(Integer, server_default="0")
    estado: Mapped[str] = mapped_column(String(10), server_default="activo")
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AplicacionDescuento(_PK, Base):
    __tablename__ = "aplicacion_descuento"
    documento_tipo: Mapped[str] = mapped_column(String(16))
    documento_id: Mapped[int] = mapped_column(BigInteger)
    linea_id: Mapped[int | None] = mapped_column(BigInteger)
    origen: Mapped[str] = mapped_column(String(10))
    origen_id: Mapped[int | None] = mapped_column(BigInteger)
    precio_lista: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    precio_final: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    margen_resultante: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    autorizacion_id: Mapped[int | None] = mapped_column(BigInteger)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AutorizacionMargenMinimo(_PK, Base):
    __tablename__ = "autorizacion_margen_minimo"
    documento_tipo: Mapped[str] = mapped_column(String(16))
    documento_id: Mapped[int] = mapped_column(BigInteger)
    autorizador_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    margen_resultante: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    motivo: Mapped[str] = mapped_column(String(255))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
