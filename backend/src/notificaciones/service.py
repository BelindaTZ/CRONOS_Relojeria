"""Lógica del módulo `notificaciones` (feature 014).

Los disparadores (006/007/008/001) solo llaman `encolar()` — un `INSERT` local
y barato dentro de su propia transacción; el envío real ocurre después, en el
worker (`procesar_cola`), desacoplado del camino transaccional (Spec §FR-017,
research D3). `encolar()` NUNCA lanza por un fallo de destinatario/opt-out —
esos casos son estados válidos del `envio` (`sin_destinatario`/`cancelado`),
no errores.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from notificaciones import repository
from notificaciones.models import Envio, PreferenciaComunicacion
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from shared.models import PlantillaEmail
from shared.parametros import get_parametro

logger = logging.getLogger("cronos.notificaciones")

# Tipos que ignoran el opt-out del cliente (Spec §FR-011, data-model regla 3):
# correos operativos críticos, no de marketing/fidelización.
_TIPOS_CRITICOS = {"password_temporal", "usuario_bienvenida", "ot_entregado", "ot_cancelada"}

# Los 15 tipos de correo que gestiona el sistema (10 ya existían como archivo
# Jinja2 desde 001/008/009/010/011; 014 agrega 5 disparadores automáticos
# nuevos: ot_entregado, ot_cancelada, cupon, nivel, recordatorio_cita).
TIPOS_CONOCIDOS = {
    "password_temporal", "inactivacion_sucursal", "cancelacion_orden", "usuario_bienvenida",
    "tecnico_asignado", "factura_venta", "tecnico_nueva_ot", "diagnostico_cliente",
    "servicio_listo_retiro", "compra_urgente_solicitada",
    "ot_entregado", "ot_cancelada", "cupon", "nivel", "recordatorio_cita",
}


# ------------------------------------------------------------------- encolar
def _clave_idempotencia(tipo: str, disparo_origen_tipo: str, disparo_origen_id: int, hito: str) -> str:
    return f"{tipo}:{disparo_origen_tipo}:{disparo_origen_id}:{hito}"[:80]


def _destinatario(db: Session, *, cliente_id: int | None, usuario_id: int | None) -> str | None:
    if cliente_id:
        from clientes import cliente_mini

        cli = cliente_mini(db, cliente_id)
        return (cli or {}).get("email")
    if usuario_id:
        from shared.models import Usuario

        u = db.get(Usuario, usuario_id)
        return u.email if u else None
    return None


def encolar(
    db: Session, *, tipo: str, disparo_origen_tipo: str, disparo_origen_id: int, hito: str, contexto: dict,
    cliente_id: int | None = None, usuario_id: int | None = None, destinatario_email: str | None = None,
    programar_para: datetime | None = None,
) -> Envio:
    """Encola un envío — idempotente por (tipo, disparo, hito). Respeta
    opt-out (salvo tipos críticos). `destinatario_email` explícito sirve para
    correos a personal interno sin `cliente_id`/`usuario_id` (p. ej. el
    responsable de sucursal en `inactivacion_sucursal`)."""
    clave = _clave_idempotencia(tipo, disparo_origen_tipo, disparo_origen_id, hito)
    existente = repository.por_clave_idempotencia(db, clave)
    if existente:
        return existente

    email = destinatario_email or _destinatario(db, cliente_id=cliente_id, usuario_id=usuario_id)
    estado = "encolado"
    motivo: str | None = None

    if tipo not in _TIPOS_CRITICOS and cliente_id:
        pref = repository.preferencia(db, cliente_id, tipo)
        if pref is not None and not pref.opt_in:
            estado, motivo = "cancelado", "opt_out"

    if estado == "encolado" and not email:
        estado, motivo = "sin_destinatario", "sin_destinatario"

    max_reint = int(get_parametro(db, "max_reintentos_email", default=5))
    campos = dict(
        tipo=tipo, destinatario_email=email, cliente_id=cliente_id, usuario_id=usuario_id,
        disparo_origen_tipo=disparo_origen_tipo, disparo_origen_id=disparo_origen_id, hito=hito,
        clave_idempotencia=clave, contexto=contexto, estado=estado, motivo_estado=motivo,
        max_reintentos=max_reint, proxima_ejecucion=programar_para or datetime.now(timezone.utc),
    )
    try:
        return repository.crear_envio(db, **campos)
    except IntegrityError:
        # Carrera: otro disparo con la misma clave ganó entre el check y el insert.
        db.rollback()
        return repository.por_clave_idempotencia(db, clave)


def cancelar_pendiente(db: Session, *, disparo_origen_tipo: str, disparo_origen_id: int, motivo: str) -> int:
    """Cancela los `envio` `encolado` de un disparo (p. ej. cita cancelada/
    reprogramada antes de que salga su recordatorio — Spec §FR-010)."""
    from sqlalchemy import select

    afectados = 0
    for e in db.scalars(
        select(Envio).where(
            Envio.disparo_origen_tipo == disparo_origen_tipo,
            Envio.disparo_origen_id == disparo_origen_id,
            Envio.estado == "encolado",
        )
    ):
        e.estado = "cancelado"
        e.motivo_estado = motivo
        e.actualizado_en = datetime.now(timezone.utc)
        afectados += 1
    if afectados:
        db.flush()
    return afectados


# --------------------------------------------------------------------- worker
def _procesar_uno(db: Session, envio: Envio, *, backoff_min: int) -> None:
    from shared.correo import enviar as enviar_correo

    envio.estado = "enviando"
    db.flush()
    try:
        message_id = enviar_correo(envio.tipo, envio.destinatario_email, envio.contexto, envio_id=envio.id)
        envio.estado = "enviado"
        envio.proveedor_message_id = message_id
        envio.motivo_estado = None
        envio.intentos += 1
    except Exception as exc:  # noqa: BLE001 — un envío fallido no debe tumbar el poller
        envio.intentos += 1
        detalle = str(exc)[:120]
        if envio.intentos >= envio.max_reintentos:
            envio.estado = "fallido"
        else:
            envio.estado = "encolado"
            envio.proxima_ejecucion = datetime.now(timezone.utc) + timedelta(minutes=backoff_min * envio.intentos)
        envio.motivo_estado = detalle
        logger.warning("Envío %s (%s) falló intento %d: %s", envio.id, envio.tipo, envio.intentos, detalle)
    envio.actualizado_en = datetime.now(timezone.utc)
    db.flush()


def generar_recordatorios_cita(db: Session) -> int:
    """US3: sondea `citas.citas_para_recordatorio()` — el punto de integración
    que 007 dejó preparado explícitamente para 014 ("Interno (014)" en su
    propio código) — y encola el recordatorio de cada cita confirmada que ya
    entró en su ventana de antelación. `encolar()` deduplica por
    (tipo, cita, fecha_confirmada) — sondear cada minuto no reenvía nada."""
    try:
        from citas import citas_para_recordatorio
    except Exception as exc:  # noqa: BLE001 — 007 podría no estar disponible en algún entorno
        logger.warning("no se pudo consultar citas_para_recordatorio: %s", exc)
        return 0

    antelacion_h = int(get_parametro(db, "antelacion_recordatorio_cita_horas", default=24) or 24)
    generados = 0
    for c in citas_para_recordatorio(db, antelacion=f"{antelacion_h}h"):
        suc = None
        try:
            from sucursales import datos_contacto

            suc = datos_contacto(db, c["sucursal_id"])
        except Exception:  # noqa: BLE001
            pass
        envio = encolar(
            db, tipo="recordatorio_cita", disparo_origen_tipo="cita", disparo_origen_id=c["cita_id"],
            hito=c["fecha_confirmada"], cliente_id=c["cliente_id"],
            contexto={
                "cliente_nombre": c["cliente_nombre"], "motivo": c["motivo"],
                "fecha_texto": c["fecha_confirmada"], "sucursal_nombre": c.get("sucursal_nombre") or (suc or {}).get("nombre"),
                "sucursal_direccion": (suc or {}).get("direccion"),
            },
        )
        if envio.estado == "encolado":
            generados += 1
    if generados:
        db.commit()
    return generados


def procesar_cola(db: Session, *, limite: int = 20) -> int:
    backoff_min = int(get_parametro(db, "backoff_email_minutos", default=10))
    pendientes = repository.pendientes(db, ahora=datetime.now(timezone.utc), limite=limite)
    for envio in pendientes:
        _procesar_uno(db, envio, backoff_min=backoff_min)
    db.commit()
    return len(pendientes)


def reintentar(db: Session, envio_id: int, *, user: CurrentUser) -> Envio:
    envio = repository.obtener_envio(db, envio_id)
    if envio is None:
        raise NotFoundError("Envío no encontrado")
    if envio.estado not in ("fallido", "rebotado"):
        raise ConflictError(f"Un envío en estado '{envio.estado}' no se puede reintentar")
    envio.estado = "encolado"
    envio.proxima_ejecucion = datetime.now(timezone.utc)
    envio.motivo_estado = None
    envio.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="reintentar", entidad="envio", entidad_id=envio.id, despues={"estado": "encolado"})
    return envio


# --------------------------------------------------------------------- envíos
def listar(db: Session, *, tipo, estado, cliente_id, disparo_origen_id, offset, limit):
    return repository.listar_envios(
        db, tipo=tipo, estado=estado, cliente_id=cliente_id, disparo_origen_id=disparo_origen_id,
        offset=offset, limit=limit,
    )


# ------------------------------------------------------------------- webhook
_EVENTOS_ENTREGA = {"delivered": "entregado", "bounce": "rebotado", "dropped": "rebotado"}


def procesar_webhook(db: Session, eventos: list[dict]) -> int:
    from notificaciones.models import EventoWebhookEmail

    procesados = 0
    for ev in eventos:
        message_id = ev.get("sg_message_id") or ev.get("message_id")
        tipo_evento = ev.get("event")
        db.add(EventoWebhookEmail(proveedor_message_id=message_id, evento=tipo_evento or "desconocido", payload=ev))
        nuevo_estado = _EVENTOS_ENTREGA.get(tipo_evento)
        if nuevo_estado and message_id:
            envio = repository.por_proveedor_message_id_prefijo(db, message_id)
            if envio and envio.estado in ("enviado", "entregado"):
                envio.estado = nuevo_estado
                envio.motivo_estado = tipo_evento
                envio.actualizado_en = datetime.now(timezone.utc)
        procesados += 1
    db.commit()
    return procesados


# ----------------------------------------------------------------- opt-out
def get_preferencias(db: Session, cliente_id: int) -> list[dict]:
    return [{"tipo_comunicacion": p.tipo_comunicacion, "opt_in": p.opt_in} for p in repository.preferencias_de(db, cliente_id)]


def set_preferencia(db: Session, cliente_id: int, tipo_comunicacion: str, opt_in: bool) -> dict:
    if tipo_comunicacion in _TIPOS_CRITICOS:
        raise ValidationError(f"'{tipo_comunicacion}' es un tipo crítico — no admite opt-out", field="tipo_comunicacion")
    pref = repository.preferencia(db, cliente_id, tipo_comunicacion)
    if pref is None:
        pref = PreferenciaComunicacion(cliente_id=cliente_id, tipo_comunicacion=tipo_comunicacion, opt_in=opt_in)
        db.add(pref)
    else:
        pref.opt_in = opt_in
        pref.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    return {"tipo_comunicacion": pref.tipo_comunicacion, "opt_in": pref.opt_in}


def puede_enviar(db: Session, cliente_id: int | None, tipo: str) -> bool:
    """Lectura rápida de opt-out para código que sigue enviando SÍNCRONO fuera
    de la cola (008 ya tiene 4 correos propios probados — no se movieron a la
    cola, ver `CONVENCIONES.md` §27). Abre en `True` ante cualquier duda."""
    if tipo in _TIPOS_CRITICOS or not cliente_id:
        return True
    try:
        pref = repository.preferencia(db, cliente_id, tipo)
        return pref is None or pref.opt_in
    except Exception:  # noqa: BLE001
        return True


# ----------------------------------------------------------------- plantillas
def _plantilla_out(p: PlantillaEmail) -> dict:
    return {
        "tipo": p.tipo, "asunto": p.asunto, "cuerpo": p.cuerpo, "variables": p.variables,
        "version": p.version, "activa": p.activa, "actualizado_en": p.actualizado_en,
    }


def listar_plantillas(db: Session) -> list[dict]:
    salida = []
    for tipo in sorted(TIPOS_CONOCIDOS):
        activa = repository.plantilla_activa(db, tipo)
        salida.append(_plantilla_out(activa) if activa else {
            "tipo": tipo, "asunto": None, "cuerpo": None, "variables": None,
            "version": 0, "activa": False, "actualizado_en": None,
        })
    return salida


def get_plantilla(db: Session, tipo: str) -> dict:
    if tipo not in TIPOS_CONOCIDOS:
        raise NotFoundError(f"Tipo de plantilla desconocido: {tipo}")
    activa = repository.plantilla_activa(db, tipo)
    historial = repository.historial_plantilla(db, tipo)
    return {
        "actual": _plantilla_out(activa) if activa else None,
        "historial": [_plantilla_out(p) for p in historial],
    }


def set_plantilla(db: Session, tipo: str, *, asunto: str, cuerpo: str, user: CurrentUser) -> dict:
    if tipo not in TIPOS_CONOCIDOS:
        raise NotFoundError(f"Tipo de plantilla desconocido: {tipo}")
    if not asunto.strip() or not cuerpo.strip():
        raise ValidationError("Asunto y cuerpo son obligatorios")

    anterior = repository.plantilla_activa(db, tipo)
    if anterior:
        anterior.activa = False
    nueva_version = (anterior.version + 1) if anterior else 1
    nueva = PlantillaEmail(
        tipo=tipo, asunto=asunto, cuerpo=cuerpo, version=nueva_version, activa=True, actualizado_por=user.id,
    )
    db.add(nueva)
    db.flush()
    registrar_cambio(
        db, actor=user.id, accion="editar", entidad="plantilla_email", entidad_id=nueva.id,
        antes={"version": anterior.version} if anterior else None, despues={"version": nueva_version, "tipo": tipo},
    )
    return _plantilla_out(nueva)


def preview_plantilla(tipo: str, contexto: dict) -> dict:
    if tipo not in TIPOS_CONOCIDOS:
        raise NotFoundError(f"Tipo de plantilla desconocido: {tipo}")
    from shared.correo.service import asunto_de, render

    html, texto = render(tipo, contexto)
    return {"asunto": asunto_de(tipo, contexto), "html": html, "texto": texto}
