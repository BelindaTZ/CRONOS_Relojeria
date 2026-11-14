"""Sucursales: CRUD + inactivación con motivo obligatorio y aviso por email (FR-017)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.auditoria import registrar_cambio
from shared.correo import enviar
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from sucursales import repository
from sucursales.schemas import HorarioSucursalIn, HorarioSucursalOut, SucursalIn, SucursalOut

logger = logging.getLogger("cronos.sucursales")

_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _out(s) -> SucursalOut:
    return SucursalOut(
        id=s.id,
        nombre=s.nombre,
        direccion=s.direccion,
        responsable_usuario_id=s.responsable_usuario_id,
        estado=s.estado,
        motivo_inactivacion=s.motivo_inactivacion,
    )


def listar(db: Session, *, q: str | None, offset: int, limit: int) -> tuple[list[SucursalOut], int]:
    filas, total = repository.buscar(db, q, offset, limit)
    return [_out(s) for s in filas], total


def crear(db: Session, datos: SucursalIn, *, actor: int) -> SucursalOut:
    if repository.por_nombre(db, datos.nombre):
        raise ConflictError("Ya existe una sucursal con ese nombre", field="nombre")
    s = repository.crear(
        db,
        nombre=datos.nombre,
        direccion=datos.direccion,
        responsable_usuario_id=datos.responsable_usuario_id,
        estado="activa",
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="sucursal", entidad_id=s.id,
                     despues=datos.model_dump())
    return _out(s)


def inactivar(db: Session, sucursal_id: int, *, motivo: str, actor: int) -> SucursalOut:
    s = repository.obtener(db, sucursal_id)
    if s is None:
        raise NotFoundError("Sucursal no encontrada")
    if not motivo or len(motivo.strip()) < 5:
        raise ValidationError("El motivo de inactivación es obligatorio", field="motivo")
    if s.estado == "inactiva":
        raise ConflictError("La sucursal ya está inactiva")

    s.estado = "inactiva"
    s.motivo_inactivacion = motivo.strip()
    s.inactivada_en = datetime.now(timezone.utc)
    db.flush()

    personal = repository.personal_de(db, sucursal_id)
    enviados = 0
    for u in personal:
        if not u.email:
            continue
        try:
            enviar(
                "inactivacion_sucursal",
                u.email,
                {
                    "nombre": u.nombre,
                    "sucursal": s.nombre,
                    "motivo": s.motivo_inactivacion,
                    "fecha": s.inactivada_en.strftime("%Y-%m-%d %H:%M UTC"),
                },
            )
            enviados += 1
        except Exception:  # noqa: BLE001
            logger.exception("Fallo al enviar aviso de inactivación a %s", u.email)

    registrar_cambio(
        db, actor=actor, accion="inactivar", entidad="sucursal", entidad_id=sucursal_id,
        despues={"motivo": s.motivo_inactivacion, "avisos_enviados": enviados, "personal": len(personal)},
    )
    return _out(s)


# ============================================================ horario de atención
def _horario_out(h) -> HorarioSucursalOut:
    return HorarioSucursalOut(
        dia_semana=h.dia_semana, cerrado=h.cerrado,
        hora_apertura=h.hora_apertura.strftime("%H:%M") if h.hora_apertura else None,
        hora_cierre=h.hora_cierre.strftime("%H:%M") if h.hora_cierre else None,
    )


def horario_de(db: Session, sucursal_id: int) -> list[HorarioSucursalOut]:
    if repository.obtener(db, sucursal_id) is None:
        raise NotFoundError("Sucursal no encontrada")
    return [_horario_out(h) for h in repository.horario_de(db, sucursal_id)]


def set_horario(db: Session, sucursal_id: int, dias: list[HorarioSucursalIn], *, actor: int) -> list[HorarioSucursalOut]:
    if repository.obtener(db, sucursal_id) is None:
        raise NotFoundError("Sucursal no encontrada")
    from datetime import time as _time

    campos = []
    vistos = set()
    for d in dias:
        if d.dia_semana in vistos:
            raise ValidationError(f"Día {d.dia_semana} repetido", field="dia_semana")
        vistos.add(d.dia_semana)
        if not d.cerrado and (not d.hora_apertura or not d.hora_cierre):
            raise ValidationError("Indica apertura y cierre, o marca el día como cerrado", field="hora_apertura")
        campos.append({
            "dia_semana": d.dia_semana, "cerrado": d.cerrado,
            "hora_apertura": _time.fromisoformat(d.hora_apertura) if d.hora_apertura else None,
            "hora_cierre": _time.fromisoformat(d.hora_cierre) if d.hora_cierre else None,
        })
    filas = repository.reemplazar_horario(db, sucursal_id, campos)
    registrar_cambio(db, actor=actor, accion="editar", entidad="horario_sucursal", entidad_id=sucursal_id,
                     despues={"dias": len(filas)})
    return [_horario_out(h) for h in filas]


def horario_texto(db: Session, sucursal_id: int) -> str:
    """Público (servicio técnico — correo de "listo para retiro"): el horario
    de la sucursal en una línea legible, agrupando días consecutivos iguales."""
    filas = repository.horario_de(db, sucursal_id)
    if not filas:
        return "Consulta el horario de atención con la sucursal."
    partes = []
    for h in filas:
        nombre = _DIAS[h.dia_semana]
        if h.cerrado or not h.hora_apertura or not h.hora_cierre:
            partes.append(f"{nombre}: cerrado")
        else:
            partes.append(f"{nombre}: {h.hora_apertura.strftime('%H:%M')} a {h.hora_cierre.strftime('%H:%M')}")
    return " · ".join(partes)


def datos_contacto(db: Session, sucursal_id: int) -> dict | None:
    """Público: nombre + dirección de la sucursal para correos y comprobantes."""
    s = repository.obtener(db, sucursal_id)
    if s is None:
        return None
    return {"nombre": s.nombre, "direccion": s.direccion}
