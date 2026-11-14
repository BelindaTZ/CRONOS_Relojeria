"""Acceso a datos del módulo `tecnicos`."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from tecnicos.models import (
    BonoAcumulado,
    ComponenteBono,
    Especialidad,
    EsquemaCostoManoObra,
    PeriodoLiquidacion,
    ReglaBono,
    Tecnico,
    TecnicoEspecialidad,
    TecnicoSucursal,
)


# ------------------------------------------------------------------- técnico
def obtener(db: Session, tid: int) -> Tecnico | None:
    return db.get(Tecnico, tid)


def por_usuario(db: Session, usuario_id: int) -> Tecnico | None:
    return db.scalars(select(Tecnico).where(Tecnico.usuario_id == usuario_id)).first()


def por_especialidad_y_sucursal(db: Session, *, especialidad: str | None, sucursal_id: int | None) -> list[Tecnico]:
    stmt = select(Tecnico).where(Tecnico.estado == "activo")
    if sucursal_id is not None:
        stmt = stmt.join(TecnicoSucursal, TecnicoSucursal.tecnico_id == Tecnico.id).where(
            TecnicoSucursal.sucursal_id == sucursal_id
        )
    if especialidad:
        stmt = stmt.join(TecnicoEspecialidad, TecnicoEspecialidad.tecnico_id == Tecnico.id).join(
            Especialidad, Especialidad.id == TecnicoEspecialidad.especialidad_id
        ).where(Especialidad.nombre.ilike(f"%{especialidad.strip()}%"))
    return list(db.scalars(stmt.distinct()))


def crear(db: Session, **campos) -> Tecnico:
    t = Tecnico(**campos)
    db.add(t)
    db.flush()
    return t


def buscar(
    db: Session, *, q: str | None, especialidad: str | None, sucursal_id: int | None,
    solo_activos: bool, offset: int, limit: int,
) -> tuple[list[Tecnico], int]:
    stmt = select(Tecnico)
    if solo_activos:
        stmt = stmt.where(Tecnico.estado == "activo")
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Tecnico.nombre.ilike(like), Tecnico.certificaciones.ilike(like)))
    if especialidad:
        stmt = stmt.where(
            Tecnico.id.in_(
                select(TecnicoEspecialidad.tecnico_id)
                .join(Especialidad, Especialidad.id == TecnicoEspecialidad.especialidad_id)
                .where(Especialidad.nombre == especialidad)
            )
        )
    if sucursal_id:
        stmt = stmt.where(
            Tecnico.id.in_(
                select(TecnicoSucursal.tecnico_id).where(TecnicoSucursal.sucursal_id == sucursal_id)
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    filas = list(db.scalars(stmt.order_by(Tecnico.nombre).offset(offset).limit(limit)))
    return filas, int(total)


def set_especialidades(db: Session, tecnico_id: int, ids: list[int]) -> None:
    db.query(TecnicoEspecialidad).filter_by(tecnico_id=tecnico_id).delete()
    db.add_all(
        TecnicoEspecialidad(tecnico_id=tecnico_id, especialidad_id=i) for i in dict.fromkeys(ids)
    )
    db.flush()


def set_sucursales(db: Session, tecnico_id: int, ids: list[int]) -> None:
    db.query(TecnicoSucursal).filter_by(tecnico_id=tecnico_id).delete()
    db.add_all(TecnicoSucursal(tecnico_id=tecnico_id, sucursal_id=i) for i in dict.fromkeys(ids))
    db.flush()


def especialidad_ids(db: Session, tecnico_id: int) -> list[int]:
    return list(
        db.scalars(
            select(TecnicoEspecialidad.especialidad_id).where(
                TecnicoEspecialidad.tecnico_id == tecnico_id
            )
        )
    )


def sucursal_ids(db: Session, tecnico_id: int) -> list[int]:
    return list(
        db.scalars(select(TecnicoSucursal.sucursal_id).where(TecnicoSucursal.tecnico_id == tecnico_id))
    )


def nombres_especialidad(db: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {
        i: n
        for i, n in db.execute(
            select(Especialidad.id, Especialidad.nombre).where(Especialidad.id.in_(ids))
        )
    }


# --------------------------------------------------------------- especialidades
def listar_especialidades(db: Session, *, solo_activas: bool = True) -> list[Especialidad]:
    stmt = select(Especialidad).order_by(Especialidad.nombre)
    if solo_activas:
        stmt = stmt.where(Especialidad.activo.is_(True))
    return list(db.scalars(stmt))


def especialidad_por_nombre(db: Session, nombre: str) -> Especialidad | None:
    return db.scalars(select(Especialidad).where(func.lower(Especialidad.nombre) == nombre.strip().lower())).first()


def crear_especialidad(db: Session, nombre: str) -> Especialidad:
    e = Especialidad(nombre=nombre.strip())
    db.add(e)
    db.flush()
    return e


# ----------------------------------------------------------------- costo de MO
def costo_vigente(db: Session, tecnico_id: int, en_fecha: date | None = None) -> EsquemaCostoManoObra | None:
    stmt = select(EsquemaCostoManoObra).where(EsquemaCostoManoObra.tecnico_id == tecnico_id)
    if en_fecha is not None:
        stmt = stmt.where(EsquemaCostoManoObra.vigente_desde <= en_fecha)
    return db.scalars(
        stmt.order_by(EsquemaCostoManoObra.vigente_desde.desc(), EsquemaCostoManoObra.id.desc())
    ).first()


def insertar_costo(db: Session, **campos) -> EsquemaCostoManoObra:
    e = EsquemaCostoManoObra(**campos)
    db.add(e)
    db.flush()
    return e


# --------------------------------------------------------------------- regla bono
def crear_regla(db: Session, **campos) -> ReglaBono:
    r = ReglaBono(**campos)
    db.add(r)
    db.flush()
    return r


def agregar_componente(db: Session, **campos) -> ComponenteBono:
    c = ComponenteBono(**campos)
    db.add(c)
    db.flush()
    return c


def listar_reglas(db: Session, *, solo_activas: bool = False) -> list[ReglaBono]:
    stmt = select(ReglaBono).order_by(ReglaBono.vigente_desde.desc(), ReglaBono.id.desc())
    if solo_activas:
        stmt = stmt.where(ReglaBono.activa.is_(True))
    return list(db.scalars(stmt))


def regla_vigente(db: Session, en_fecha: date) -> ReglaBono | None:
    return db.scalars(
        select(ReglaBono)
        .where(ReglaBono.activa.is_(True), ReglaBono.vigente_desde <= en_fecha)
        .order_by(ReglaBono.vigente_desde.desc(), ReglaBono.id.desc())
    ).first()


# ------------------------------------------------------------ periodo / bono
def crear_periodo(db: Session, **campos) -> PeriodoLiquidacion:
    p = PeriodoLiquidacion(**campos)
    db.add(p)
    db.flush()
    return p


def obtener_periodo(db: Session, pid: int) -> PeriodoLiquidacion | None:
    return db.get(PeriodoLiquidacion, pid)


def periodos_abiertos(db: Session) -> list[PeriodoLiquidacion]:
    return list(db.scalars(select(PeriodoLiquidacion).where(PeriodoLiquidacion.estado == "abierto")))


def listar_periodos(db: Session) -> list[PeriodoLiquidacion]:
    return list(
        db.scalars(select(PeriodoLiquidacion).order_by(PeriodoLiquidacion.fecha_inicio.desc()))
    )


def bono_de(db: Session, *, tecnico_id: int, periodo_id: int) -> BonoAcumulado | None:
    return db.scalars(
        select(BonoAcumulado).where(
            BonoAcumulado.tecnico_id == tecnico_id,
            BonoAcumulado.periodo_liquidacion_id == periodo_id,
        )
    ).first()


def listar_bonos(db: Session, *, periodo_id: int | None, tecnico_id: int | None) -> list[BonoAcumulado]:
    stmt = select(BonoAcumulado)
    if periodo_id:
        stmt = stmt.where(BonoAcumulado.periodo_liquidacion_id == periodo_id)
    if tecnico_id:
        stmt = stmt.where(BonoAcumulado.tecnico_id == tecnico_id)
    return list(db.scalars(stmt.order_by(BonoAcumulado.id)))


def bonos_de_periodos_abiertos(db: Session) -> list[BonoAcumulado]:
    return list(
        db.scalars(
            select(BonoAcumulado)
            .join(PeriodoLiquidacion, PeriodoLiquidacion.id == BonoAcumulado.periodo_liquidacion_id)
            .where(PeriodoLiquidacion.estado == "abierto")
        )
    )


def tecnicos_activos(db: Session) -> list[Tecnico]:
    return list(db.scalars(select(Tecnico).where(Tecnico.estado == "activo").order_by(Tecnico.nombre)))
