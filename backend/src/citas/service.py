"""Lógica del módulo `citas` (feature 007).

Registro manual por el personal (§4.1). Ciclo de estados:
  pendiente --confirmar--> confirmada
  pendiente | confirmada --cancelar(motivo)--> cancelada
  pendiente | confirmada --atender--> atendida  (exige o inicia el vínculo a venta/OT)
`atendida` y `cancelada` son terminales.

- El canal de origen sale del catálogo `canal_cita` (001); el sistema NO lee Gmail.
- La cita siempre se ata a un `cliente` existente (006).
- Al atender sin venta/OT previa, la respuesta trae la **acción de creación** con el
  cliente y la cita como contexto (Const. Ppio XI); 008/009 vinculan la cita al
  confirmar su transacción vía `PUT /_internal/citas/{id}/vincular`.
- Scope por sucursal en listados y agenda (helper único de 003/004).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from citas import repository
from citas.models import Cita
from citas.schemas import (
    AccionCreacion,
    AgendaItemOut,
    AtenderOut,
    CitaOut,
    ConfirmarOut,
    ConversionOut,
)
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from shared.parametros import get_parametro

logger = logging.getLogger("cronos.citas")

_EDITABLES = ("pendiente", "confirmada")
_ACCION_POR_MOTIVO = {"servicio_tecnico": "crear_ot", "compra": "crear_venta"}


def _sucursales(user: CurrentUser) -> list[int] | None:
    from inventario import sucursales_visibles

    return sucursales_visibles(user, None)


# ============================================================ salida
def _sucursal_nombre(db: Session, sid: int) -> str | None:
    from shared.models import Sucursal

    s = db.get(Sucursal, sid)
    return s.nombre if s else f"#{sid}"


def _canal_nombre(db: Session, cid: int) -> str | None:
    from shared.models import CanalCita

    c = db.get(CanalCita, cid)
    return c.nombre if c else None


def _cita_out(db: Session, c: Cita) -> CitaOut:
    from clientes import cliente_mini

    cli = cliente_mini(db, c.cliente_id) or {}
    return CitaOut(
        id=c.id, cliente_id=c.cliente_id, cliente_nombre=cli.get("nombre"),
        cliente_afiliado=cli.get("numero_afiliado"),
        sucursal_id=c.sucursal_id, sucursal_nombre=_sucursal_nombre(db, c.sucursal_id),
        canal_cita_id=c.canal_cita_id, canal_nombre=_canal_nombre(db, c.canal_cita_id),
        motivo=c.motivo, fecha_preferida=c.fecha_preferida, fecha_confirmada=c.fecha_confirmada,
        estado=c.estado, motivo_cancelacion=c.motivo_cancelacion, observaciones=c.observaciones,
        venta_id=c.venta_id, orden_trabajo_id=c.orden_trabajo_id, creado_en=c.creado_en,
    )


# ============================================================ CRUD
def listar(db, *, user, q, estado, canal_cita_id, sucursal_id, cliente_id, desde, hasta, offset, limit):
    cliente_ids = None
    if q and q.strip():
        from clientes import ids_por_texto

        cliente_ids = ids_por_texto(db, q)
    filas, total = repository.buscar(
        db, sucursales=_sucursales(user), estado=estado, canal_cita_id=canal_cita_id,
        sucursal_id=sucursal_id, cliente_id=cliente_id, cliente_ids=cliente_ids,
        desde=desde, hasta=hasta, offset=offset, limit=limit,
    )
    return [_cita_out(db, c) for c in filas], total


def obtener_detalle(db: Session, cid: int) -> CitaOut:
    c = repository.obtener(db, cid)
    if c is None:
        raise NotFoundError("Cita no encontrada")
    return _cita_out(db, c)


def crear(db: Session, datos, *, actor: int) -> CitaOut:
    from clientes import cliente_mini
    from shared.models import CanalCita, Sucursal

    cli = cliente_mini(db, datos.cliente_id)
    if cli is None:
        raise ValidationError(
            "La cita debe atarse a un cliente registrado. Crea primero su ficha.", field="cliente_id"
        )
    if cli.get("es_consumidor_final"):
        raise ValidationError("No se registran citas para el «Consumidor Final»", field="cliente_id")

    canal = db.get(CanalCita, datos.canal_cita_id)
    if canal is None or not canal.activo:
        raise ValidationError("Canal de origen inválido o inactivo", field="canal_cita_id")
    suc = db.get(Sucursal, datos.sucursal_id)
    if suc is None or suc.estado != "activa":
        raise ValidationError("Sucursal inválida o inactiva", field="sucursal_id")

    c = repository.crear(
        db, cliente_id=datos.cliente_id, sucursal_id=datos.sucursal_id,
        canal_cita_id=datos.canal_cita_id, motivo=datos.motivo,
        fecha_preferida=datos.fecha_preferida,
        observaciones=(datos.observaciones or "").strip() or None,
        estado="pendiente", creado_por=actor,
    )
    repository.registrar_estado(db, cita_id=c.id, estado="pendiente", actor_usuario_id=actor)
    registrar_cambio(db, actor=actor, accion="crear", entidad="cita", entidad_id=c.id,
                     despues={"cliente_id": c.cliente_id, "motivo": c.motivo, "sucursal_id": c.sucursal_id})
    return _cita_out(db, c)


def actualizar(db: Session, cid: int, datos, *, actor: int) -> CitaOut:
    c = repository.obtener(db, cid)
    if c is None:
        raise NotFoundError("Cita no encontrada")
    if c.estado not in _EDITABLES:
        raise ConflictError(f"No se edita una cita en estado '{c.estado}'")
    cambios = datos.model_dump(exclude_unset=True)
    if "canal_cita_id" in cambios and cambios["canal_cita_id"]:
        from shared.models import CanalCita

        if db.get(CanalCita, cambios["canal_cita_id"]) is None:
            raise ValidationError("Canal inválido", field="canal_cita_id")
    for campo in ("canal_cita_id", "motivo", "fecha_preferida"):
        if campo in cambios and cambios[campo] is not None:
            setattr(c, campo, cambios[campo])
    if "observaciones" in cambios:
        c.observaciones = (cambios["observaciones"] or "").strip() or None
    c.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="cita", entidad_id=cid, despues=cambios)
    return _cita_out(db, c)


# ============================================================ ciclo de estados
def _transicion(db: Session, c: Cita, nuevo: str, *, actor: int, motivo: str | None = None) -> None:
    c.estado = nuevo
    c.actualizado_en = datetime.now(timezone.utc)
    repository.registrar_estado(db, cita_id=c.id, estado=nuevo, actor_usuario_id=actor, motivo=motivo)
    db.flush()
    registrar_cambio(db, actor=actor, accion=nuevo, entidad="cita", entidad_id=c.id,
                     despues={"estado": nuevo, **({"motivo": motivo} if motivo else {})})


def confirmar(db: Session, cid: int, *, fecha_confirmada: datetime | None, actor: int) -> ConfirmarOut:
    c = repository.obtener(db, cid, for_update=True)
    if c is None:
        raise NotFoundError("Cita no encontrada")
    if c.estado != "pendiente":
        raise ConflictError(f"Solo se confirma una cita pendiente (estado actual: {c.estado})")

    c.fecha_confirmada = fecha_confirmada or c.fecha_preferida
    _transicion(db, c, "confirmada", actor=actor)

    # advertencia (no bloqueo) de solape con otra confirmada de la misma sucursal
    ventana_min = int(get_parametro(db, "citas_ventana_solape_min", default=30) or 30)
    inicio = c.fecha_confirmada - timedelta(minutes=ventana_min)
    fin = c.fecha_confirmada + timedelta(minutes=ventana_min)
    otras = repository.solapadas(db, sucursal_id=c.sucursal_id, inicio=inicio, fin=fin, excluir_id=c.id)
    warning = (
        f"Ya hay {len(otras)} cita(s) confirmada(s) en esta sucursal en una franja de ±{ventana_min} min."
        if otras else None
    )
    # El recordatorio (014) NO se encola aquí: `citas_para_recordatorio()` más
    # abajo ya es el punto de integración que 007 dejó preparado para que 014
    # lo consulte por sondeo (mismo tick del worker de notificaciones) — evita
    # duplicar el mecanismo con un `encolar(programar_para=...)` aparte.
    return ConfirmarOut(cita=_cita_out(db, c), warning=warning)


def cancelar(db: Session, cid: int, *, motivo: str, actor: int) -> CitaOut:
    c = repository.obtener(db, cid, for_update=True)
    if c is None:
        raise NotFoundError("Cita no encontrada")
    if c.estado == "atendida":
        raise ConflictError("No se puede cancelar una cita ya atendida")
    if c.estado == "cancelada":
        raise ConflictError("La cita ya está cancelada")
    if not motivo or len(motivo.strip()) < 3:
        raise ValidationError("El motivo de la cancelación es obligatorio", field="motivo")
    c.motivo_cancelacion = motivo.strip()
    _transicion(db, c, "cancelada", actor=actor, motivo=motivo.strip())
    try:
        from notificaciones import cancelar_pendiente

        cancelar_pendiente(db, disparo_origen_tipo="cita", disparo_origen_id=c.id, motivo="cita_cancelada")
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se pudo cancelar el recordatorio pendiente de la cita %s: %s", c.id, exc)
    return _cita_out(db, c)


def atender(db: Session, cid: int, *, venta_id: int | None, orden_trabajo_id: int | None, actor: int) -> AtenderOut:
    c = repository.obtener(db, cid, for_update=True)
    if c is None:
        raise NotFoundError("Cita no encontrada")
    if c.estado not in ("pendiente", "confirmada"):
        raise ConflictError(f"No se atiende una cita en estado '{c.estado}'")

    if venta_id is not None:
        c.venta_id = venta_id
    if orden_trabajo_id is not None:
        c.orden_trabajo_id = orden_trabajo_id
    _transicion(db, c, "atendida", actor=actor)

    accion = None
    if not (c.venta_id or c.orden_trabajo_id):
        tipo = _ACCION_POR_MOTIVO.get(c.motivo)  # 'consulta' no genera transacción
        if tipo:
            accion = AccionCreacion(tipo=tipo, cliente_id=c.cliente_id, cita_id=c.id)
    return AtenderOut(cita=_cita_out(db, c), accion=accion)


def vincular(db: Session, cid: int, *, venta_id: int | None, orden_trabajo_id: int | None, actor: int) -> CitaOut:
    """Interno (008/009): ata la transacción generada a la cita ya atendida."""
    c = repository.obtener(db, cid, for_update=True)
    if c is None:
        raise NotFoundError("Cita no encontrada")
    if venta_id is not None:
        c.venta_id = venta_id
    if orden_trabajo_id is not None:
        c.orden_trabajo_id = orden_trabajo_id
    c.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=actor, accion="vincular", entidad="cita", entidad_id=cid,
                     despues={"venta_id": c.venta_id, "orden_trabajo_id": c.orden_trabajo_id})
    return _cita_out(db, c)


# ============================================================ agenda / reportes
def historial_estados(db: Session, cid: int) -> list[dict]:
    if repository.obtener(db, cid) is None:
        raise NotFoundError("Cita no encontrada")
    return [
        {"estado": h.estado, "actor_usuario_id": h.actor_usuario_id,
         "motivo": h.motivo, "timestamp": h.timestamp.isoformat()}
        for h in repository.historial(db, cid)
    ]


def agenda(db: Session, *, user, rango: str, fecha: datetime, sucursal_id: int | None) -> list[AgendaItemOut]:
    inicio = datetime(fecha.year, fecha.month, fecha.day, tzinfo=timezone.utc)
    if rango == "semana":
        inicio = inicio - timedelta(days=inicio.weekday())
        fin = inicio + timedelta(days=7)
    else:
        fin = inicio + timedelta(days=1)
    filas = repository.agenda(
        db, sucursales=_sucursales(user), sucursal_id=sucursal_id, desde=inicio, hasta=fin,
    )
    salida = []
    for c in filas:
        base = _cita_out(db, c).model_dump()
        salida.append(AgendaItemOut(**base, hora=c.fecha_confirmada or c.fecha_preferida))
    return salida


def conversion(db: Session, *, desde: datetime | None, hasta: datetime | None) -> ConversionOut:
    atendidas, con_tx = repository.contar_conversion(db, desde=desde, hasta=hasta)
    tasa = round(con_tx / atendidas, 4) if atendidas else 0.0
    return ConversionOut(atendidas=atendidas, con_transaccion=con_tx, tasa=tasa)


def _parse_antelacion(txt: str | None) -> timedelta:
    s = (txt or "24h").strip().lower()
    try:
        if s.endswith("h"):
            return timedelta(hours=float(s[:-1]))
        if s.endswith("d"):
            return timedelta(days=float(s[:-1]))
        return timedelta(hours=float(s))
    except ValueError:
        return timedelta(hours=24)


def citas_para_recordatorio(db: Session, *, antelacion: str | None) -> list[dict]:
    """Interno (014): citas confirmadas cuya hora cae dentro de [ahora, ahora+antelación]."""
    ahora = datetime.now(timezone.utc)
    hasta = ahora + _parse_antelacion(antelacion)
    salida = []
    for c in repository.confirmadas_en_ventana(db, desde=ahora, hasta=hasta):
        out = _cita_out(db, c)
        salida.append({
            "cita_id": c.id, "cliente_id": c.cliente_id, "cliente_nombre": out.cliente_nombre,
            "sucursal_id": c.sucursal_id, "sucursal_nombre": out.sucursal_nombre,
            "fecha_confirmada": (c.fecha_confirmada or c.fecha_preferida).isoformat(),
            "motivo": c.motivo,
        })
    return salida


# ============================================================ API pública (008/009)
def vincular_transaccion(db: Session, cita_id: int, *, venta_id: int | None = None,
                         orden_trabajo_id: int | None = None, actor: int | None = None) -> None:
    """008/009 llaman esto al confirmar la transacción que nació de una cita."""
    c = repository.obtener(db, cita_id, for_update=True)
    if c is None:
        return
    if venta_id is not None:
        c.venta_id = venta_id
    if orden_trabajo_id is not None:
        c.orden_trabajo_id = orden_trabajo_id
    db.flush()
