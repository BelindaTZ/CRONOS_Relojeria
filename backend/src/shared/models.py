"""Modelos ORM del sustrato central de CRONOS (identidad, RBAC, configuración, auditoría).

Vive en `shared/` porque son infraestructura compartida: el guard, la auditoría y
el motor de parámetros los consumen de forma transversal. Los módulos de negocio
(`auth`, `usuarios`, `rbac`, `sucursales`, `configuracion`) construyen su lógica
router→service→repository ENCIMA de estos modelos; no redefinen el esquema.

El esquema físico lo crean las migraciones Alembic (`0001`–`0006`), hechas a mano.
Estos modelos deben mantenerse consistentes con ellas (sin autogenerate).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class _PK:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


# --------------------------------------------------------------------------- RBAC
class Rol(_PK, Base):
    __tablename__ = "rol"
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Modulo(_PK, Base):
    __tablename__ = "modulo"
    clave: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[str | None] = mapped_column(String(255))


class Operacion(_PK, Base):
    __tablename__ = "operacion"
    clave: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(40))


class PermisoModulo(_PK, Base):
    __tablename__ = "permiso_modulo"
    rol_id: Mapped[int] = mapped_column(ForeignKey("rol.id", ondelete="CASCADE"))
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulo.id", ondelete="CASCADE"))


class PermisoOperacion(_PK, Base):
    __tablename__ = "permiso_operacion"
    rol_id: Mapped[int] = mapped_column(ForeignKey("rol.id", ondelete="CASCADE"))
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulo.id", ondelete="CASCADE"))
    operacion_id: Mapped[int] = mapped_column(ForeignKey("operacion.id", ondelete="CASCADE"))


# ----------------------------------------------------------------------- Identidad
class Usuario(_PK, Base):
    __tablename__ = "usuario"
    identificacion: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    foto_perfil_objeto: Mapped[str | None] = mapped_column(String(255))
    estado: Mapped[str] = mapped_column(String(12), server_default="activo")
    must_change_password: Mapped[bool] = mapped_column(Boolean, server_default="false")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UsuarioRol(_PK, Base):
    __tablename__ = "usuario_rol"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    rol_id: Mapped[int] = mapped_column(ForeignKey("rol.id", ondelete="CASCADE"))


class UsuarioSucursal(_PK, Base):
    __tablename__ = "usuario_sucursal"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="CASCADE"))


class PermisoUsuario(_PK, Base):
    __tablename__ = "permiso_usuario"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulo.id", ondelete="CASCADE"))
    operacion_id: Mapped[int | None] = mapped_column(ForeignKey("operacion.id", ondelete="CASCADE"))
    efecto: Mapped[str] = mapped_column(String(8))  # conceder | revocar


class RefreshToken(_PK, Base):
    __tablename__ = "refresh_token"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SolicitudRestablecimiento(_PK, Base):
    __tablename__ = "solicitud_restablecimiento"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    password_temporal_hash: Mapped[str] = mapped_column(String(255))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usada: Mapped[bool] = mapped_column(Boolean, server_default="false")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------------------ Sucursal
class Sucursal(_PK, Base):
    __tablename__ = "sucursal"
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    direccion: Mapped[str | None] = mapped_column(String(255))
    responsable_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL")
    )
    estado: Mapped[str] = mapped_column(String(12), server_default="activa")
    motivo_inactivacion: Mapped[str | None] = mapped_column(String(500))
    inactivada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HorarioSucursal(_PK, Base):
    """Horario de atención por sucursal y día de semana (feedback del usuario,
    2026-09-11 — flujo de servicio técnico: el correo de "listo para retiro"
    necesita informar el horario de la sucursal correspondiente)."""

    __tablename__ = "horario_sucursal"
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id", ondelete="CASCADE"))
    dia_semana: Mapped[int] = mapped_column(Integer)  # 0 lunes … 6 domingo
    cerrado: Mapped[bool] = mapped_column(Boolean, server_default="false")
    hora_apertura: Mapped[object | None] = mapped_column(Time)
    hora_cierre: Mapped[object | None] = mapped_column(Time)


# ------------------------------------------------------------------------ Catálogos
class MedioPago(_PK, Base):
    __tablename__ = "medio_pago"
    clave: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class CategoriaGasto(_PK, Base):
    __tablename__ = "categoria_gasto"
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    tipo: Mapped[str] = mapped_column(String(24))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class CanalCita(_PK, Base):
    __tablename__ = "canal_cita"
    clave: Mapped[str] = mapped_column(String(40), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class CategoriaMerma(_PK, Base):
    """Catálogo editable (011): motivo específico dentro de una `causa` de merma
    (ej. causa `dano_tienda` → categoría "Caída accidental")."""

    __tablename__ = "categoria_merma"
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    causa: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class CondicionPago(_PK, Base):
    """Catálogo maestro de condiciones de pago (feature 002 v2). Editable."""

    __tablename__ = "condicion_pago"
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    dias_credito: Mapped[int] = mapped_column(Integer, server_default="0")
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class MarcaReloj(_PK, Base):
    """Catálogo de marcas de reloj (feedback 2026-09-10). Editable, campos ricos."""

    __tablename__ = "marca_reloj"
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    pais: Mapped[str | None] = mapped_column(String(80))
    sitio_web: Mapped[str | None] = mapped_column(String(200))
    nota: Mapped[str | None] = mapped_column(String(500))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Material(_PK, Base):
    """Catálogo compartido de materiales (caja y brazalete de reloj)."""

    __tablename__ = "material"
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Color(_PK, Base):
    """Catálogo de colores (esfera de reloj). `hex` opcional para la muestra."""

    __tablename__ = "color"
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    hex: Mapped[str | None] = mapped_column(String(7))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class PlantillaEmail(_PK, Base):
    """Override editable de una plantilla de `shared/correo` (feature 014).
    Vive en `shared/` (no en `notificaciones/`) porque `shared/correo/service.py`
    la lee al renderizar CUALQUIER correo del sistema — Ppio X: lo que dos
    módulos comparten vive en `shared/`, nunca un módulo de negocio importado
    desde `shared/` (eso invertiría la dependencia). Histórico por versión:
    como mucho una fila `activa=true` por `tipo` (índice único parcial,
    migración `0030`); sin fila activa, `shared/correo` sigue usando el
    archivo Jinja2 de siempre."""

    __tablename__ = "plantilla_email"
    tipo: Mapped[str] = mapped_column(String(30))
    asunto: Mapped[str] = mapped_column(String(200))
    cuerpo: Mapped[str] = mapped_column(Text)
    variables: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------- Parámetros / auditoría
class ParametroConfiguracion(_PK, Base):
    __tablename__ = "parametro_configuracion"
    clave: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(16))
    valor: Mapped[dict] = mapped_column(JSONB)
    ambito_tipo: Mapped[str] = mapped_column(String(16), server_default="global")
    ambito_ref: Mapped[str | None] = mapped_column(String(80))
    vigente_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegistroAuditoria(_PK, Base):
    __tablename__ = "registro_auditoria"
    actor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[str] = mapped_column(String(60))
    entidad_id: Mapped[str | None] = mapped_column(String(40))
    antes: Mapped[dict | None] = mapped_column(JSONB)
    despues: Mapped[dict | None] = mapped_column(JSONB)
    ip_origen: Mapped[str | None] = mapped_column(String(45))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
