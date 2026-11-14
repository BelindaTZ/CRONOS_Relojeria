from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.models import (
    CanalCita,
    CategoriaGasto,
    CategoriaMerma,
    Color,
    CondicionPago,
    MarcaReloj,
    Material,
    MedioPago,
)


def medios_pago(db: Session) -> list[MedioPago]:
    return list(db.scalars(select(MedioPago).order_by(MedioPago.id)))


def medio_pago(db: Session, mid: int) -> MedioPago | None:
    return db.get(MedioPago, mid)


def medio_pago_por_clave(db: Session, clave: str) -> MedioPago | None:
    return db.scalars(select(MedioPago).where(MedioPago.clave == clave)).first()


def crear_medio_pago(db: Session, *, clave: str, nombre: str) -> MedioPago:
    m = MedioPago(clave=clave, nombre=nombre, activo=True)
    db.add(m)
    db.flush()
    return m


def condiciones_pago(db: Session, *, solo_activas: bool = False) -> list[CondicionPago]:
    stmt = select(CondicionPago).order_by(CondicionPago.dias_credito, CondicionPago.nombre)
    if solo_activas:
        stmt = stmt.where(CondicionPago.activo.is_(True))
    return list(db.scalars(stmt))


def condicion_pago(db: Session, cid: int) -> CondicionPago | None:
    return db.get(CondicionPago, cid)


def crear_condicion_pago(db: Session, *, nombre: str, dias_credito: int) -> CondicionPago:
    c = CondicionPago(nombre=nombre, dias_credito=dias_credito, activo=True)
    db.add(c)
    db.flush()
    return c


def categorias_gasto(db: Session) -> list[CategoriaGasto]:
    return list(db.scalars(select(CategoriaGasto).order_by(CategoriaGasto.nombre)))


def crear_categoria_gasto(db: Session, *, nombre: str, tipo: str) -> CategoriaGasto:
    c = CategoriaGasto(nombre=nombre, tipo=tipo, activo=True)
    db.add(c)
    db.flush()
    return c


def categorias_merma(db: Session, *, causa: str | None = None) -> list[CategoriaMerma]:
    stmt = select(CategoriaMerma).order_by(CategoriaMerma.nombre)
    if causa:
        stmt = stmt.where(CategoriaMerma.causa == causa)
    return list(db.scalars(stmt))


def crear_categoria_merma(db: Session, *, nombre: str, causa: str) -> CategoriaMerma:
    c = CategoriaMerma(nombre=nombre, causa=causa, activo=True)
    db.add(c)
    db.flush()
    return c


def canales_cita(db: Session) -> list[CanalCita]:
    return list(db.scalars(select(CanalCita).order_by(CanalCita.id)))


def canal_por_clave(db: Session, clave: str) -> CanalCita | None:
    return db.scalars(select(CanalCita).where(CanalCita.clave == clave)).first()


def upsert_canal(db: Session, *, clave: str, nombre: str, activo: bool) -> CanalCita:
    existente = canal_por_clave(db, clave)
    if existente:
        existente.nombre = nombre
        existente.activo = activo
        db.flush()
        return existente
    c = CanalCita(clave=clave, nombre=nombre, activo=activo)
    db.add(c)
    db.flush()
    return c


# --- catálogos de la ficha de reloj (marca / material / color) ---
def marcas_reloj(db: Session, *, solo_activas: bool = False) -> list[MarcaReloj]:
    stmt = select(MarcaReloj).order_by(MarcaReloj.nombre)
    if solo_activas:
        stmt = stmt.where(MarcaReloj.activo.is_(True))
    return list(db.scalars(stmt))


def marca_reloj(db: Session, mid: int) -> MarcaReloj | None:
    return db.get(MarcaReloj, mid)


def marca_reloj_por_nombre(db: Session, nombre: str) -> MarcaReloj | None:
    return db.scalars(select(MarcaReloj).where(func.lower(MarcaReloj.nombre) == nombre.strip().lower())).first()


def crear_marca_reloj(db: Session, **campos) -> MarcaReloj:
    m = MarcaReloj(**campos)
    db.add(m)
    db.flush()
    return m


def materiales(db: Session, *, solo_activas: bool = False) -> list[Material]:
    stmt = select(Material).order_by(Material.nombre)
    if solo_activas:
        stmt = stmt.where(Material.activo.is_(True))
    return list(db.scalars(stmt))


def material(db: Session, mid: int) -> Material | None:
    return db.get(Material, mid)


def material_por_nombre(db: Session, nombre: str) -> Material | None:
    return db.scalars(select(Material).where(func.lower(Material.nombre) == nombre.strip().lower())).first()


def crear_material(db: Session, *, nombre: str) -> Material:
    m = Material(nombre=nombre)
    db.add(m)
    db.flush()
    return m


def colores(db: Session, *, solo_activas: bool = False) -> list[Color]:
    stmt = select(Color).order_by(Color.nombre)
    if solo_activas:
        stmt = stmt.where(Color.activo.is_(True))
    return list(db.scalars(stmt))


def color(db: Session, cid: int) -> Color | None:
    return db.get(Color, cid)


def color_por_nombre(db: Session, nombre: str) -> Color | None:
    return db.scalars(select(Color).where(func.lower(Color.nombre) == nombre.strip().lower())).first()


def crear_color(db: Session, *, nombre: str, hex: str | None) -> Color:
    c = Color(nombre=nombre, hex=hex)
    db.add(c)
    db.flush()
    return c
