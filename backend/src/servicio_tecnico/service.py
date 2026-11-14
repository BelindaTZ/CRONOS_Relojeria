"""Lógica del módulo `servicio_tecnico` (feature 008).

Ciclo de estados de la OT (research D1):
  recibido --diagnostico--> en_diagnostico --presupuesto--> presupuesto
  presupuesto --aprobar(+ fecha estimada)--> en_reparacion --> listo --> entregado
Cualquier estado no terminal --cancelar--> cancelada.

- `en_reparacion` exige un presupuesto `aprobado` (FR-003d).
- `fecha_estimada_entrega` se fija al aprobar el presupuesto, nunca antes (FR-016).
- `entregado` exige `saldo(OT) == 0` o una autorización de crédito de Gerencia
  General (FR-016a) — la CxC la crea 010.
- Al entregar: costeo definitivo, PDF (OT + certificado) a `comprobantes-venta`,
  `evento_serie(servicio)` en el historial de serie (003), recálculo de nivel del
  cliente (006) y vínculo con la cita (007).
- Costo interno y margen: solo roles administrativos (FR-026); nunca en el PDF.
- Un técnico solo edita las OT asignadas a él (FR-025, scoping "solo las propias").
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from servicio_tecnico import costeo, repository
from servicio_tecnico.models import OrdenTrabajo
from servicio_tecnico.schemas import (
    CosteoOut,
    DanoPayloadOut,
    DescuentoAplicadoOut,
    InformeServicioOut,
    LineaPresupuestoOut,
    LubricacionOut,
    OrdenTrabajoDetalle,
    OrdenTrabajoOut,
    PagoRegistradoOut,
    PiezaUsadaOut,
    PresupuestoOut,
    RelojElegibleOut,
)
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from shared.parametros import get_parametro

logger = logging.getLogger("cronos.servicio_tecnico")

# Roles que ven costo interno / margen y el desglose de costeo (FR-026, §6).
_ROLES_VER_COSTOS = {"Gerencia General", "Gerente de Sucursal", "Contador", "Administrador", "Técnico Jefe"}
_ROLES_JEFE = {"Gerencia General", "Técnico Jefe"}

_TERMINALES = ("entregado", "cancelada")
_TRANSICIONES: dict[str, set[str]] = {
    "recibido": {"en_diagnostico", "cancelada"},
    "en_diagnostico": {"presupuesto", "en_diagnostico", "cancelada"},
    "presupuesto": {"en_reparacion", "en_diagnostico", "cancelada"},
    "en_reparacion": {"listo", "cancelada"},
    "listo": {"entregado", "en_reparacion", "cancelada"},
    "entregado": set(),
    "cancelada": set(),
}


class NoAutorizadoError(ConflictError):
    status_code = 403
    code = "no_autorizado"


def puede_ver_costos(user: CurrentUser) -> bool:
    return bool(_ROLES_VER_COSTOS & set(getattr(user, "roles", []) or []))


def _es_jefe(user: CurrentUser) -> bool:
    return bool(_ROLES_JEFE & set(getattr(user, "roles", []) or []))


def _sucursales(user: CurrentUser) -> list[int] | None:
    from inventario import sucursales_visibles

    return sucursales_visibles(user, None)


def _tecnico_del_usuario(db: Session, user: CurrentUser) -> int | None:
    from tecnicos import tecnico_de_usuario

    return tecnico_de_usuario(db, user.id)


def _solo_propias(db: Session, user: CurrentUser) -> int | None:
    """Devuelve el tecnico_id al que hay que restringir, o None si el usuario ve todo
    su alcance de sucursal (Gerencia / Técnico Jefe / roles administrativos)."""
    if user.es_gerencia or _es_jefe(user) or puede_ver_costos(user):
        return None
    return _tecnico_del_usuario(db, user)


def _asegurar_puede_editar(db: Session, user: CurrentUser, ot: OrdenTrabajo) -> None:
    restr = _solo_propias(db, user)
    if restr is not None and ot.tecnico_id != restr:
        raise NoAutorizadoError("Solo puedes trabajar sobre las órdenes asignadas a ti")


# ============================================================ salida
def _cliente(db: Session, cid: int) -> dict:
    from clientes import cliente_mini

    return cliente_mini(db, cid) or {}


def _reloj(db: Session, rid: int) -> dict:
    from inventario import reloj_para_ot

    return reloj_para_ot(db, rid) or {}


def _sucursal_nombre(db: Session, sid: int) -> str | None:
    from shared.models import Sucursal

    s = db.get(Sucursal, sid)
    return s.nombre if s else f"#{sid}"


def _tecnico_nombre(db: Session, tid: int | None) -> str | None:
    if tid is None:
        return None
    from tecnicos import datos_para_correo

    d = datos_para_correo(db, tid)
    return d["nombre"] if d else None


def _encargado_compras(db: Session, sucursal_id: int) -> dict | None:
    """A quién avisar cuando el técnico necesita una compra urgente: el
    responsable de la sucursal si está fijado, o si no cualquier usuario con
    rol «Gerencia General» (flujo principal, paso 6 — "el técnico solicita
    al encargado de compras que gestione una orden de compra urgente")."""
    from shared.models import Rol, Sucursal, Usuario, UsuarioRol

    s = db.get(Sucursal, sucursal_id)
    if s and s.responsable_usuario_id:
        u = db.get(Usuario, s.responsable_usuario_id)
        if u:
            return {"nombre": u.nombre, "email": u.email}
    u = db.execute(
        select(Usuario)
        .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
        .join(Rol, Rol.id == UsuarioRol.rol_id)
        .where(Rol.nombre == "Gerencia General")
        .limit(1)
    ).scalar_one_or_none()
    return {"nombre": u.nombre, "email": u.email} if u else None


def _saldo(db: Session, ot: OrdenTrabajo) -> Decimal | None:
    from shared.pagos import saldo

    if ot.precio_cobrado is None:
        return None
    return saldo(db, documento_tipo="orden_trabajo", documento_id=ot.id, total=ot.precio_cobrado)


def _ot_out(db: Session, ot: OrdenTrabajo, *, user: CurrentUser) -> OrdenTrabajoOut:
    cli = _cliente(db, ot.cliente_id)
    rel = _reloj(db, ot.reloj_id)
    vc = puede_ver_costos(user)
    return OrdenTrabajoOut(
        id=ot.id, numero=ot.numero, reloj_id=ot.reloj_id,
        reloj_serie=rel.get("numero_serie"), reloj_marca=rel.get("marca"),
        reloj_referencia=rel.get("referencia"),
        cliente_id=ot.cliente_id, cliente_nombre=cli.get("nombre"),
        cliente_afiliado=cli.get("numero_afiliado"),
        tecnico_id=ot.tecnico_id, tecnico_nombre=_tecnico_nombre(db, ot.tecnico_id),
        sucursal_id=ot.sucursal_id, sucursal_nombre=_sucursal_nombre(db, ot.sucursal_id),
        cita_id=ot.cita_id, ot_original_id=ot.ot_original_id,
        motivo=ot.motivo, diagnostico=ot.diagnostico, trabajo_realizado=ot.trabajo_realizado,
        tipo_reparacion=ot.tipo_reparacion, horas_trabajadas=ot.horas_trabajadas,
        fecha_ingreso=ot.fecha_ingreso, fecha_estimada_entrega=ot.fecha_estimada_entrega,
        fecha_real_entrega=ot.fecha_real_entrega, estado=ot.estado,
        garantia_periodo_dias=ot.garantia_periodo_dias, garantia_cobertura=ot.garantia_cobertura,
        reproceso=ot.reproceso,
        precio_cobrado=ot.precio_cobrado, saldo=_saldo(db, ot),
        costo_interno=ot.costo_interno if vc else None,
        margen_real=ot.margen_real if vc else None,
        costos_visibles=vc, creado_en=ot.creado_en,
    )


def _pieza_out(db: Session, pu, *, ver_costos: bool) -> PiezaUsadaOut:
    from piezas import datos_pieza

    d = datos_pieza(db, pu.pieza_id) or {}
    return PiezaUsadaOut(
        id=pu.id, pieza_id=pu.pieza_id, pieza_codigo=d.get("codigo"), descripcion=d.get("descripcion"),
        tipo_elegido=pu.tipo_elegido, cantidad=pu.cantidad,
        costo=Decimal(str(pu.costo)) if (ver_costos and pu.costo is not None) else None,
    )


def _presupuesto_out(db: Session, p, *, sucursal_id: int | None = None) -> PresupuestoOut:
    from piezas import datos_pieza, stock_en

    if sucursal_id is None:
        ot_rel = repository.obtener(db, p.orden_trabajo_id)
        sucursal_id = ot_rel.sucursal_id if ot_rel else None

    lineas = []
    for ln in p.lineas:
        orig = datos_pieza(db, ln.pieza_original_id) or {}
        noor = datos_pieza(db, ln.pieza_no_original_id) if ln.pieza_no_original_id else None
        dif = None
        if ln.precio_no_original is not None:
            dif = (Decimal(str(ln.precio_no_original)) - Decimal(str(ln.precio_original))).quantize(Decimal("0.01"))
        stock_orig = stock_en(db, ln.pieza_original_id, sucursal_id) if sucursal_id else 0
        stock_noor = stock_en(db, ln.pieza_no_original_id, sucursal_id) if (sucursal_id and ln.pieza_no_original_id) else None
        lineas.append(LineaPresupuestoOut(
            id=ln.id, pieza_original_id=ln.pieza_original_id, pieza_original=orig.get("codigo"),
            pieza_no_original_id=ln.pieza_no_original_id,
            pieza_no_original=(noor or {}).get("codigo") if noor else None,
            precio_original=Decimal(str(ln.precio_original)),
            precio_no_original=Decimal(str(ln.precio_no_original)) if ln.precio_no_original is not None else None,
            diferencia=dif, preferencia_cliente=ln.preferencia_cliente, cantidad=ln.cantidad,
            stock_original_suficiente=stock_orig >= ln.cantidad,
            stock_no_original_suficiente=(stock_noor >= ln.cantidad) if stock_noor is not None else True,
        ))
    return PresupuestoOut(
        id=p.id, orden_trabajo_id=p.orden_trabajo_id, precio_servicio=Decimal(str(p.precio_servicio)),
        estado=p.estado, confirmado_por=p.confirmado_por, medio_confirmacion=p.medio_confirmacion,
        fecha_confirmacion=p.fecha_confirmacion, lineas=lineas,
    )


def _detalle(db: Session, ot: OrdenTrabajo, *, user: CurrentUser) -> OrdenTrabajoDetalle:
    from lubricacion import registros_de_ot
    from shared.pagos import pagos_de

    vc = puede_ver_costos(user)
    base = _ot_out(db, ot, user=user).model_dump()
    presu = repository.presupuesto_activo(db, ot.id)
    lub = [LubricacionOut(**r) for r in registros_de_ot(db, ot.id)]
    pagos = [
        {"pago_id": p.id, "medio_pago": p.medio_pago_nombre, "monto": str(p.monto), "referencia": p.referencia}
        for p in pagos_de(db, documento_tipo="orden_trabajo", documento_id=ot.id)
    ]
    hist = [
        {"estado": h.estado, "actor_usuario_id": h.actor_usuario_id, "timestamp": h.timestamp.isoformat()}
        for h in repository.historial(db, ot.id)
    ]
    docs = [
        {"tipo": d.tipo, "objeto": d.objeto, "generado_en": d.generado_en.isoformat()}
        for d in repository.documentos_de(db, ot.id)
    ]
    return OrdenTrabajoDetalle(
        **base,
        piezas=[_pieza_out(db, pu, ver_costos=vc) for pu in repository.piezas_de(db, ot.id)],
        lubricacion=lub,
        presupuesto=_presupuesto_out(db, presu) if presu else None,
        pagos=pagos, historial=hist, documentos=docs,
    )


def _get(db: Session, oid: int, *, for_update: bool = False) -> OrdenTrabajo:
    ot = repository.obtener(db, oid, for_update=for_update)
    if ot is None:
        raise NotFoundError("Orden de trabajo no encontrada")
    return ot


# ============================================================ CRUD / tablero
def _sucursales_para_listado(db: Session, user: CurrentUser, *, solo_tecnico_id: int | None) -> list[int] | None:
    """El scoping por sucursal es para vistas agregadas de sucursal (Vendedor,
    Gerente de Sucursal); un técnico ve SUS órdenes asignadas, punto — sin
    intersectar con sucursal. Bug encontrado 2026-09-11 (reporte del usuario:
    "el técnico no ve su orden"): a un técnico de una sola sucursal se le asignaba
    una OT registrada en OTRA (p. ej. es el especialista de esa marca en toda la
    empresa) y el AND de ambos filtros la dejaba invisible en su propia lista —
    la OT existía y era suya, pero el filtro de sucursal la tapaba en silencio."""
    if solo_tecnico_id is not None:
        return None
    return _sucursales(user)


def listar(db, *, user, estado, tecnico_id, sucursal_id, numero_serie, offset, limit):
    reloj_ids = None
    if numero_serie and numero_serie.strip():
        from inventario import ids_relojes_por_serie

        reloj_ids = ids_relojes_por_serie(db, numero_serie)
    solo_tecnico_id = _solo_propias(db, user)
    filas, total = repository.buscar(
        db, sucursales=_sucursales_para_listado(db, user, solo_tecnico_id=solo_tecnico_id),
        solo_tecnico_id=solo_tecnico_id,
        estado=estado, tecnico_id=tecnico_id, sucursal_id=sucursal_id,
        reloj_ids=reloj_ids, offset=offset, limit=limit,
    )
    return [_ot_out(db, o, user=user) for o in filas], total


def obtener_detalle(db: Session, oid: int, *, user: CurrentUser) -> OrdenTrabajoDetalle:
    ot = _get(db, oid)
    return _detalle(db, ot, user=user)


def _garantia_por_tipo(db: Session, tipo_reparacion: str) -> int:
    v = get_parametro(db, "garantia_tienda_dias_default", ambito_tipo="tipo_servicio",
                      ambito_ref=tipo_reparacion.strip().lower(), default=None, fallback_global=False)
    if v is None:
        v = get_parametro(db, "garantia_tienda_dias_default", default=180)
    try:
        return int(v)
    except (TypeError, ValueError):
        return 180


def relojes_elegibles(db: Session, *, q: str | None) -> list[RelojElegibleOut]:
    """Previsualización para el formulario de alta (feedback del usuario, 2026-09-11:
    "el número de serie es texto libre, debería autollenar el cliente dueño"): catálogo
    real de unidades que pueden abrir una OT, con el cliente que la compró cuando hay
    una venta confirmada — para que el selector auto-rellene el cliente en vez de
    dejarlo a que el vendedor lo adivine o lo teclee mal."""
    from clientes import cliente_mini
    from inventario import relojes_elegibles_para_ot
    from ventas import propietario_de_reloj

    salida = []
    for r in relojes_elegibles_para_ot(db, q=q):
        prop = propietario_de_reloj(db, r["id"])
        cli = cliente_mini(db, prop["cliente_id"]) if prop else None
        salida.append(RelojElegibleOut(
            id=r["id"], numero_serie=r["numero_serie"], marca=r["marca"], referencia=r["referencia"],
            cliente_id=cli.get("id") if cli else None,
            cliente_nombre=cli.get("nombre") if cli else None,
            cliente_afiliado=cli.get("numero_afiliado") if cli else None,
        ))
    return salida


def tecnico_sugerido_para_serie(db: Session, *, numero_serie: str, sucursal_id: int | None) -> dict:
    """Previsualización para el formulario de alta: misma resolución que `crear_ot`
    pero de solo lectura y tolerante (nunca lanza si la serie aún no es válida —
    el vendedor puede seguir escribiendo)."""
    from inventario import calibres_por_ids, ids_relojes_por_serie, reloj_para_ot

    numero_serie = (numero_serie or "").strip()
    if not numero_serie:
        return {"tecnico_id": None, "tecnico_nombre": None}
    reloj = None
    for rid in ids_relojes_por_serie(db, numero_serie):
        r = reloj_para_ot(db, rid)
        if r and r["numero_serie"].strip().lower() == numero_serie.lower():
            reloj = r
            break
    if reloj is None:
        return {"tecnico_id": None, "tecnico_nombre": None}

    from tecnicos import sugerir_tecnico

    suc = sucursal_id or reloj.get("sucursal_actual_id")
    calibre_cod = calibres_por_ids(db, [reloj["calibre_id"]]).get(reloj["calibre_id"]) if reloj.get("calibre_id") else None
    tid = sugerir_tecnico(db, marca=reloj.get("marca"), calibre_codigo=calibre_cod, sucursal_id=suc)
    if tid is None:
        return {"tecnico_id": None, "tecnico_nombre": None}
    from tecnicos import datos_para_correo

    datos_t = datos_para_correo(db, tid) or {}
    return {"tecnico_id": tid, "tecnico_nombre": datos_t.get("nombre")}


def crear_ot(db: Session, datos, *, user: CurrentUser) -> OrdenTrabajoOut:
    from inventario import reloj_para_ot, serie_adquirida_en_tienda

    # cliente
    cli = _cliente(db, datos.cliente_id)
    if not cli:
        raise ValidationError("La OT debe atarse a un cliente registrado", field="cliente_id")

    # reloj por número de serie
    from inventario import ids_relojes_por_serie

    ids = [rid for rid in ids_relojes_por_serie(db, datos.numero_serie)]
    reloj = None
    for rid in ids:
        r = reloj_para_ot(db, rid)
        if r and r["numero_serie"].strip().lower() == datos.numero_serie.strip().lower():
            reloj = r
            break
    if reloj is None:
        raise ValidationError(
            "No hay ninguna unidad con ese número de serie en el inventario", field="numero_serie"
        )
    if reloj["disponibilidad"] == "en_transito":
        raise ConflictError("La unidad está en tránsito entre sucursales; no se puede abrir la OT ahora")

    # adquirido en la tienda (§2.1 / FR-002)
    adquirido = serie_adquirida_en_tienda(db, datos.numero_serie)
    if not adquirido and not (datos.override_adquisicion_motivo and datos.override_adquisicion_motivo.strip()):
        raise ValidationError(
            "No consta que esta unidad se haya adquirido en la tienda. Indica un motivo de "
            "autorización para continuar (override_adquisicion_motivo).",
            field="numero_serie",
        )

    sucursal_id = datos.sucursal_id or reloj.get("sucursal_actual_id")
    if sucursal_id is None:
        raise ValidationError("Indica la sucursal de la OT", field="sucursal_id")

    # técnico: si el vendedor lo indicó explícitamente (confirmando o corrigiendo la
    # sugerencia mostrada en el formulario), se usa ese; si no, se sugiere por
    # especialidad (marca primero, luego calibre) + sucursal — nunca queda en blanco
    # en silencio (FR: "no puede haber una OT sin técnico" salvo que de verdad no
    # haya ninguno activo, caso raro que se deja visible en el formulario).
    from inventario import calibres_por_ids
    from tecnicos import sugerir_tecnico, tecnico_activo

    if getattr(datos, "tecnico_id", None) is not None:
        if not tecnico_activo(db, datos.tecnico_id):
            raise ValidationError("El técnico indicado no está activo", field="tecnico_id")
        tecnico_id = datos.tecnico_id
    else:
        calibre_cod = calibres_por_ids(db, [reloj["calibre_id"]]).get(reloj["calibre_id"]) if reloj.get("calibre_id") else None
        tecnico_id = sugerir_tecnico(db, marca=reloj.get("marca"), calibre_codigo=calibre_cod, sucursal_id=sucursal_id)

    ot = repository.crear(
        db, numero=repository.siguiente_numero(db), reloj_id=reloj["id"], cliente_id=datos.cliente_id,
        tecnico_id=tecnico_id, sucursal_id=sucursal_id, cita_id=datos.cita_id,
        motivo=datos.motivo.strip(), tipo_reparacion=datos.tipo_reparacion.strip(),
        estado="recibido", adquirido_en_tienda_ok=adquirido,
        override_adquisicion_motivo=(datos.override_adquisicion_motivo or "").strip() or None,
        garantia_periodo_dias=_garantia_por_tipo(db, datos.tipo_reparacion),
        garantia_cobertura="Mano de obra y repuestos instalados en este servicio",
        reproceso=repository.reprocesos_sobre_reloj(db, reloj["id"], excluir_id=0) > 0,
        creado_por=user.id,
    )
    repository.registrar_estado(db, orden_trabajo_id=ot.id, estado="recibido", actor_usuario_id=user.id)
    registrar_cambio(db, actor=user.id, accion="crear", entidad="orden_trabajo", entidad_id=ot.id,
                     despues={"numero": ot.numero, "reloj_id": ot.reloj_id, "cliente_id": ot.cliente_id})

    # Nunca vendible mientras está en el taller (bug 2026-09-11): la unidad es del
    # cliente (comprada aquí o ajena con motivo de excepción), jamás stock propio.
    from inventario import marcar_reloj_en_servicio

    marcar_reloj_en_servicio(db, reloj["id"], orden_trabajo_id=ot.id, actor=user.id)

    if tecnico_id is not None:
        _avisar_tecnico_asignado(db, ot, cli)
        _avisar_tecnico_nueva_ot(db, ot, cliente=cli, reloj=reloj)
    return _ot_out(db, ot, user=user)


def _avisar_tecnico_nueva_ot(db: Session, ot: OrdenTrabajo, *, cliente: dict, reloj: dict) -> None:
    """Feedback del usuario (flujo principal, 2026-09-11): el técnico también
    recibe la OT por correo, no solo la ve en su portal."""
    from tecnicos import datos_para_correo

    datos = datos_para_correo(db, ot.tecnico_id) or {}
    email = datos.get("email")
    if not email:
        return
    try:
        from shared.correo import enviar

        enviar("tecnico_nueva_ot", email, {
            "tecnico_nombre": datos.get("nombre"),
            "ot_numero": ot.numero,
            "reloj_marca": reloj.get("marca"), "reloj_referencia": reloj.get("referencia"),
            "reloj_serie": reloj.get("numero_serie"),
            "cliente_nombre": cliente.get("nombre"),
            "motivo": ot.motivo,
        })
    except Exception as exc:  # noqa: BLE001  (el correo no bloquea la operación)
        logger.warning("no se pudo avisar al técnico de la nueva OT %s: %s", ot.id, exc)


def _avisar_tecnico_asignado(db: Session, ot: OrdenTrabajo, cliente: dict) -> None:
    """FR-003a: email al cliente con los datos generales del técnico."""
    email = cliente.get("email")
    if not email:
        return
    from tecnicos import datos_para_correo

    datos = datos_para_correo(db, ot.tecnico_id) or {}
    try:
        from shared.correo import enviar

        enviar("tecnico_asignado", email, {
            "cliente_nombre": cliente.get("nombre"),
            "ot_numero": ot.numero,
            "tecnico": datos,
            "contacto_email": get_parametro(db, "servicio_tecnico_contacto_email", default="taller@cronos.local"),
        })
    except Exception as exc:  # noqa: BLE001  (el correo no bloquea la operación — 014 lo hará robusto)
        logger.warning("no se pudo enviar el aviso de técnico asignado (OT %s): %s", ot.id, exc)


def actualizar(db: Session, oid: int, datos, *, user: CurrentUser) -> OrdenTrabajoOut:
    ot = _get(db, oid, for_update=True)
    if ot.estado in _TERMINALES:
        raise ConflictError(f"No se edita una OT en estado '{ot.estado}'")
    cambios = datos.model_dump(exclude_unset=True)

    if "tecnico_id" in cambios and cambios["tecnico_id"] != ot.tecnico_id:
        if not (user.es_gerencia or _es_jefe(user)):
            raise NoAutorizadoError("Asignar o cambiar el técnico requiere Técnico Jefe o Gerencia General")
        from tecnicos import tecnico_activo

        nuevo = cambios["tecnico_id"]
        if nuevo is not None and not tecnico_activo(db, nuevo):
            raise ValidationError("El técnico no está activo", field="tecnico_id")
        ot.tecnico_id = nuevo
        if nuevo is not None:
            _avisar_tecnico_asignado(db, ot, _cliente(db, ot.cliente_id))
            _avisar_tecnico_nueva_ot(db, ot, cliente=_cliente(db, ot.cliente_id), reloj=_reloj(db, ot.reloj_id))
    else:
        _asegurar_puede_editar(db, user, ot)

    if cambios.get("motivo"):
        ot.motivo = cambios["motivo"].strip()
    if cambios.get("tipo_reparacion"):
        ot.tipo_reparacion = cambios["tipo_reparacion"].strip()
    ot.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="orden_trabajo", entidad_id=oid,
                     despues=cambios)
    return _ot_out(db, ot, user=user)


# ============================================================ transiciones
def _transicionar(db: Session, ot: OrdenTrabajo, nuevo: str, *, actor: int) -> None:
    if nuevo not in _TRANSICIONES.get(ot.estado, set()):
        raise ConflictError(f"Transición inválida: {ot.estado} → {nuevo}")
    ot.estado = nuevo
    ot.actualizado_en = datetime.now(timezone.utc)
    repository.registrar_estado(db, orden_trabajo_id=ot.id, estado=nuevo, actor_usuario_id=actor)
    db.flush()
    registrar_cambio(db, actor=actor, accion=nuevo, entidad="orden_trabajo", entidad_id=ot.id,
                     despues={"estado": nuevo})


def registrar_diagnostico(db: Session, oid: int, datos, *, user: CurrentUser) -> OrdenTrabajoOut:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    if ot.estado not in ("recibido", "en_diagnostico"):
        raise ConflictError(f"No se registra diagnóstico en estado '{ot.estado}'")
    ot.diagnostico = datos.diagnostico.strip()
    if ot.estado == "recibido":
        _transicionar(db, ot, "en_diagnostico", actor=user.id)
    else:
        db.flush()
        registrar_cambio(db, actor=user.id, accion="editar", entidad="orden_trabajo", entidad_id=oid,
                         despues={"diagnostico": True})
    return _ot_out(db, ot, user=user)


def registrar_horas(db: Session, oid: int, datos, *, user: CurrentUser) -> OrdenTrabajoOut:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    if ot.estado in _TERMINALES:
        raise ConflictError("La OT ya está cerrada")
    ot.horas_trabajadas = datos.horas
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="orden_trabajo", entidad_id=oid,
                     despues={"horas_trabajadas": str(datos.horas)})
    _recalcular_costeo(db, ot)
    return _ot_out(db, ot, user=user)


def registrar_trabajo(db: Session, oid: int, texto: str, *, user: CurrentUser) -> OrdenTrabajoOut:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    ot.trabajo_realizado = (texto or "").strip() or None
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="orden_trabajo", entidad_id=oid,
                     despues={"trabajo_realizado": True})
    return _ot_out(db, ot, user=user)


# ============================================================ presupuesto
def crear_presupuesto(db: Session, oid: int, datos, *, user: CurrentUser) -> PresupuestoOut:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    if ot.estado not in ("en_diagnostico", "presupuesto"):
        raise ConflictError("El presupuesto se arma tras el diagnóstico")
    if not ot.diagnostico:
        raise ValidationError("Registra primero el diagnóstico", field="diagnostico")

    from piezas import datos_pieza, datos_pieza_venta

    def _precio_pieza(pieza_id: int, precio_indicado: Decimal | None) -> Decimal:
        # El precio de un presupuesto lo fija el catálogo (`precio_venta_suelta`),
        # nunca el costo interno de adquisición — feedback del usuario (2026-09-11):
        # "las piezas van a estar sin precio... no nos vamos a inventar uno para el
        # cliente". Antes, dejar el campo vacío caía silenciosamente al COSTO
        # (`costo_pieza`), mostrándole al cliente el precio de compra interno.
        if precio_indicado is not None:
            return precio_indicado
        dp = datos_pieza_venta(db, pieza_id)
        precio_catalogo = dp.get("precio_venta_suelta") if dp else None
        if precio_catalogo is None:
            raise ValidationError(
                f"La pieza «{(dp or {}).get('codigo', pieza_id)}» no tiene precio de venta en el catálogo. "
                "Cárgalo en Piezas o indícalo manualmente en esta línea.",
                field="lineas",
            )
        return Decimal(str(precio_catalogo))

    p = repository.crear_presupuesto(
        db, orden_trabajo_id=oid, precio_servicio=datos.precio_servicio, estado="borrador",
    )
    for ln in datos.lineas:
        if datos_pieza(db, ln.pieza_original_id) is None:
            raise ValidationError(f"Pieza original inexistente: {ln.pieza_original_id}", field="lineas")
        if ln.pieza_no_original_id is not None and datos_pieza(db, ln.pieza_no_original_id) is None:
            raise ValidationError(f"Pieza no original inexistente: {ln.pieza_no_original_id}", field="lineas")
        repository.agregar_linea_presupuesto(
            db, presupuesto_id=p.id, pieza_original_id=ln.pieza_original_id,
            pieza_no_original_id=ln.pieza_no_original_id,
            precio_original=_precio_pieza(ln.pieza_original_id, ln.precio_original),
            precio_no_original=(
                _precio_pieza(ln.pieza_no_original_id, ln.precio_no_original)
                if ln.pieza_no_original_id else None
            ),
            cantidad=ln.cantidad,
        )
    if ot.estado == "en_diagnostico":
        _transicionar(db, ot, "presupuesto", actor=user.id)
    db.refresh(p)
    registrar_cambio(db, actor=user.id, accion="crear", entidad="presupuesto", entidad_id=p.id,
                     despues={"orden_trabajo_id": oid, "lineas": len(datos.lineas)})
    salida = _presupuesto_out(db, p, sucursal_id=ot.sucursal_id)
    _avisar_diagnostico_cliente(db, ot, salida)
    return salida


def _avisar_diagnostico_cliente(db: Session, ot: OrdenTrabajo, presupuesto: PresupuestoOut) -> None:
    """Feedback del usuario (flujo principal, 2026-09-11): el técnico envía el
    diagnóstico al cliente; si hay piezas de por medio, pregunta original vs.
    buena calidad e informa el costo ADICIONAL de la pieza (aparte del costo
    del servicio, que ya incluye mano de obra + margen — regla existente)."""
    cliente = _cliente(db, ot.cliente_id)
    email = cliente.get("email")
    if not email:
        return
    lineas = [
        {
            "descripcion": ln.pieza_original or f"Pieza #{ln.pieza_original_id}",
            "precio_original": ln.precio_original, "precio_no_original": ln.precio_no_original,
            "cantidad": ln.cantidad,
        }
        for ln in presupuesto.lineas
    ]
    try:
        from shared.correo import enviar

        enviar("diagnostico_cliente", email, {
            "cliente_nombre": cliente.get("nombre"), "ot_numero": ot.numero, "diagnostico": ot.diagnostico,
            "requiere_piezas": len(lineas) > 0, "lineas": lineas,
            "contacto_email": get_parametro(db, "servicio_tecnico_contacto_email", default="taller@cronos.local"),
        })
    except Exception as exc:  # noqa: BLE001  (el correo no bloquea la operación)
        logger.warning("no se pudo enviar el diagnóstico al cliente (OT %s): %s", ot.id, exc)


def aprobar_presupuesto(db: Session, oid: int, datos, *, user: CurrentUser) -> OrdenTrabajoDetalle:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    if ot.estado != "presupuesto":
        raise ConflictError("No hay un presupuesto pendiente de aprobación")
    p = repository.presupuesto_activo(db, oid)
    if p is None:
        raise ValidationError("La OT no tiene presupuesto", field="presupuesto")

    prefs = {pr.linea_id: pr.preferencia for pr in datos.preferencias}
    for ln in p.lineas:
        if ln.id not in prefs:
            continue
        elegida = prefs[ln.id]
        if elegida == "no_original" and ln.pieza_no_original_id is None:
            raise ValidationError(
                f"La línea de presupuesto #{ln.id} no ofrece una opción no original", field="preferencias",
            )
        ln.preferencia_cliente = elegida
    p.estado = "aprobado"
    p.confirmado_por = datos.confirmado_por.strip()
    p.medio_confirmacion = (datos.medio_confirmacion or "").strip() or None
    p.fecha_confirmacion = datetime.now(timezone.utc)

    if datos.fecha_estimada_entrega < date.today():
        raise ValidationError("La fecha estimada de entrega no puede ser pasada", field="fecha_estimada_entrega")
    ot.fecha_estimada_entrega = datos.fecha_estimada_entrega
    if p.precio_servicio and (ot.precio_cobrado is None):
        ot.precio_cobrado = p.precio_servicio
    _transicionar(db, ot, "en_reparacion", actor=user.id)
    registrar_cambio(db, actor=user.id, accion="aprobar", entidad="presupuesto", entidad_id=p.id,
                     despues={"confirmado_por": p.confirmado_por, "fecha_estimada": str(ot.fecha_estimada_entrega)})
    _recalcular_costeo(db, ot)
    return _detalle(db, ot, user=user)


# ============================================================ piezas / lubricación
def agregar_pieza_ot(db: Session, oid: int, datos, *, user: CurrentUser) -> PiezaUsadaOut:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    if ot.estado != "en_reparacion":
        raise ConflictError("Las piezas se registran con la OT en reparación")
    from piezas import consumir_en_ot

    costo = consumir_en_ot(
        db, pieza_id=datos.pieza_id, sucursal_id=ot.sucursal_id, cantidad=datos.cantidad,
        orden_trabajo_id=oid, actor=user.id,
    )
    pu = repository.agregar_pieza(
        db, orden_trabajo_id=oid, pieza_id=datos.pieza_id, tipo_elegido=datos.tipo_elegido,
        cantidad=datos.cantidad, costo=costo,
    )
    registrar_cambio(db, actor=user.id, accion="crear", entidad="pieza_usada_ot", entidad_id=pu.id,
                     despues={"orden_trabajo_id": oid, "pieza_id": datos.pieza_id, "cantidad": datos.cantidad})
    _recalcular_costeo(db, ot)
    return _pieza_out(db, pu, ver_costos=puede_ver_costos(user))


def solicitar_compra_urgente(db: Session, oid: int, datos, *, user: CurrentUser) -> dict:
    """El técnico avisa por correo al encargado de compras cuando una pieza
    necesaria para la reparación no tiene stock (flujo principal, paso 6). No
    crea la orden de compra — eso lo gestiona el encargado, con `urgente=True`
    disponible en 002 para priorizarla."""
    ot = _get(db, oid)
    _asegurar_puede_editar(db, user, ot)
    from piezas import datos_pieza

    pieza = datos_pieza(db, datos.pieza_id) or {}
    destinatario = _encargado_compras(db, ot.sucursal_id)
    if destinatario and destinatario.get("email"):
        try:
            from shared.correo import enviar

            enviar(
                "compra_urgente_solicitada",
                destinatario["email"],
                {
                    "encargado_nombre": destinatario["nombre"],
                    "ot_numero": ot.numero,
                    "pieza_codigo": pieza.get("codigo"),
                    "pieza_descripcion": pieza.get("descripcion"),
                    "cantidad": datos.cantidad,
                    "sucursal_nombre": _sucursal_nombre(db, ot.sucursal_id),
                    "nota": datos.nota or None,
                },
            )
        except Exception as exc:  # pragma: no cover - fallo de correo no bloquea
            logger.warning("No se pudo enviar compra_urgente_solicitada: %s", exc)
    registrar_cambio(
        db, actor=user.id, accion="solicitar_compra_urgente", entidad="orden_trabajo", entidad_id=oid,
        despues={"pieza_id": datos.pieza_id, "cantidad": datos.cantidad},
    )
    return {"notificado": bool(destinatario and destinatario.get("email"))}


def registrar_lubricacion_ot(db: Session, oid: int, datos, *, user: CurrentUser) -> LubricacionOut:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    if ot.estado != "en_reparacion":
        raise ConflictError("La lubricación se registra con la OT en reparación")
    from lubricacion import registrar_en_ot

    reg, _costo = registrar_en_ot(
        db, orden_trabajo_id=oid, sucursal_id=ot.sucursal_id,
        producto_usado_codigo=datos.producto_usado_codigo,
        punto_lubricacion_id=datos.punto_lubricacion_id, punto_nombre=datos.punto_nombre,
        calibre_id=_reloj(db, ot.reloj_id).get("calibre_id"),
        tecnico_id=ot.tecnico_id, actor=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="crear", entidad="registro_lubricacion_ot", entidad_id=reg.id,
                     despues={"orden_trabajo_id": oid, "punto": reg.punto_nombre, "desviacion": reg.desviacion})
    _recalcular_costeo(db, ot)
    from lubricacion import repository as _lubrepo

    usa = _lubrepo.producto(db, reg.producto_usado_id)
    rec = _lubrepo.producto(db, reg.producto_recomendado_id) if reg.producto_recomendado_id else None
    return LubricacionOut(
        id=reg.id, punto_nombre=reg.punto_nombre,
        producto_recomendado=rec.codigo if rec else None,
        producto_usado=usa.codigo if usa else "—",
        desviacion=reg.desviacion, fecha=reg.fecha,
    )


# ============================================================ costeo / descuento
def _recalcular_costeo(db: Session, ot: OrdenTrabajo) -> None:
    if ot.estado in ("entregado", "cancelada"):
        return
    c = costeo.costear(db, ot)
    ot.costo_interno = c.costo_interno
    if ot.precio_cobrado is None:
        ot.precio_cobrado = c.precio_sugerido
    ot.margen_real = (Decimal(str(ot.precio_cobrado)) - c.costo_interno) if ot.precio_cobrado is not None else None
    db.flush()


def get_costeo(db: Session, oid: int, *, user: CurrentUser) -> CosteoOut:
    if not puede_ver_costos(user):
        raise NoAutorizadoError("El costeo del servicio es visible solo para roles administrativos")
    ot = _get(db, oid)
    c = costeo.costear(db, ot)
    return CosteoOut(
        costo_mano_obra=c.costo_mano_obra, costo_piezas=c.costo_piezas, costo_insumos=c.costo_insumos,
        costo_interno=c.costo_interno, bono_prorrateado=c.bono_prorrateado,
        margen_objetivo=c.margen_objetivo, precio_sugerido=c.precio_sugerido,
        precio_cobrado=ot.precio_cobrado, margen_real=c.margen_real, base_mano_obra=c.base_mano_obra,
    )


def aplicar_descuento(db: Session, oid: int, datos, *, user: CurrentUser) -> DescuentoAplicadoOut:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    if ot.estado in _TERMINALES:
        raise ConflictError("La OT ya está cerrada")
    c = costeo.costear(db, ot)
    precio_lista = Decimal(str(ot.precio_cobrado)) if ot.precio_cobrado is not None else c.precio_sugerido

    from shared.descuentos import BeneficioAplicable, aplicar as _aplicar

    beneficio = BeneficioAplicable(tipo=datos.tipo, valor=datos.valor)
    rel = _reloj(db, ot.reloj_id)
    r = _aplicar(
        db, item_ref=f"OT-{ot.numero}", costo=c.costo_interno, precio_lista=precio_lista,
        marca=rel.get("marca"),
        descuento=None if datos.es_cupon else beneficio,
        cupon=beneficio if datos.es_cupon else None,
    )
    if r.decision == "bloquear":
        raise ConflictError(
            "El descuento deja el margen por debajo del mínimo protegido y la política es bloquear"
        )
    if r.decision == "requiere_autorizacion":
        raise NoAutorizadoError(
            "El descuento deja el margen bajo el mínimo protegido: requiere autorización de Gerencia General"
        )

    if datos.es_cupon and datos.codigo_cupon:
        from clientes import consumir_cupon

        consumir_cupon(db, codigo=datos.codigo_cupon, documento_tipo="orden_trabajo",
                       documento_id=ot.id, actor=user.id)

    ot.precio_cobrado = r.precio_final
    ot.margen_real = r.margen_resultante
    ot.descuento_aplicado = {
        "tipo": datos.tipo, "valor": float(datos.valor), "es_cupon": datos.es_cupon,
        "monto_descontado": float(r.monto_descontado), "decision": r.decision,
    }
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="orden_trabajo", entidad_id=oid,
                     despues={"descuento": ot.descuento_aplicado})
    return DescuentoAplicadoOut(
        precio_final=r.precio_final, monto_descontado=r.monto_descontado,
        margen_resultante=r.margen_resultante, decision=r.decision,
    )


# ============================================================ pagos
def registrar_pago_ot(db: Session, oid: int, datos, *, user: CurrentUser) -> PagoRegistradoOut:
    ot = _get(db, oid, for_update=True)
    if ot.estado in ("cancelada",):
        raise ConflictError("La OT está cancelada")
    if ot.precio_cobrado is None:
        raise ValidationError("La OT aún no tiene precio: aprueba el presupuesto o fija el precio", field="monto")

    from shared.models import MedioPago
    from shared.pagos import registrar_pago, saldo

    medio = db.scalars(
        select(MedioPago).where(MedioPago.clave == datos.medio_pago.strip())
    ).first()
    if medio is None:
        raise ValidationError(f"Medio de pago desconocido: {datos.medio_pago}", field="medio_pago")

    p = registrar_pago(
        db, documento_tipo="orden_trabajo", documento_id=oid, medio_pago_id=medio.id,
        monto=datos.monto, referencia=datos.referencia, actor=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="crear", entidad="pago", entidad_id=p.id,
                     despues={"documento": f"orden_trabajo#{oid}", "monto": str(datos.monto), "medio": medio.clave})
    s = saldo(db, documento_tipo="orden_trabajo", documento_id=oid, total=ot.precio_cobrado)
    return PagoRegistradoOut(pago_id=p.id, medio_pago=medio.nombre, monto=Decimal(str(datos.monto)), saldo=s)


# ============================================================ estado manual / entrega
def cambiar_estado(db: Session, oid: int, nuevo: str, *, user: CurrentUser) -> OrdenTrabajoOut:
    ot = _get(db, oid, for_update=True)
    _asegurar_puede_editar(db, user, ot)
    if nuevo == "entregado":
        raise ConflictError("Usa la acción «Entregar» para cerrar y cobrar la OT")
    if nuevo == "en_reparacion" and ot.estado == "presupuesto":
        raise ConflictError("Aprueba el presupuesto para pasar a reparación")
    _transicionar(db, ot, nuevo, actor=user.id)
    if nuevo == "cancelada":
        from inventario import revertir_reloj_servicio

        revertir_reloj_servicio(db, ot.reloj_id, orden_trabajo_id=ot.id, actor=user.id)
        registrar_cambio(db, actor=user.id, accion="cancelar", entidad="orden_trabajo", entidad_id=oid)
        _avisar_ot_estado(db, ot, tipo="ot_cancelada", hito="cancelada")
    if nuevo == "listo":
        _avisar_listo_para_retiro(db, ot)
    return _ot_out(db, ot, user=user)


def _avisar_ot_estado(db: Session, ot: OrdenTrabajo, *, tipo: str, hito: str) -> None:
    """feature 014: disparadores encolados (no síncronos como los de 008 ya
    existentes) para los estados que hasta ahora quedaban mudos — 'cancelada'
    y 'entregado' (nunca se avisaba nada en ninguno de los dos)."""
    try:
        from notificaciones import encolar

        cliente = _cliente(db, ot.cliente_id)
        encolar(
            db, tipo=tipo, disparo_origen_tipo="orden_trabajo", disparo_origen_id=ot.id, hito=hito,
            cliente_id=ot.cliente_id,
            contexto={
                "cliente_nombre": cliente.get("nombre"), "ot_numero": ot.numero,
                "motivo": ot.motivo if tipo == "ot_cancelada" else None,
                "reloj_marca": _reloj(db, ot.reloj_id).get("marca") if tipo == "ot_entregado" else None,
                "reloj_referencia": _reloj(db, ot.reloj_id).get("referencia") if tipo == "ot_entregado" else None,
                "precio_cobrado": str(ot.precio_cobrado) if ot.precio_cobrado else None,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se encoló el aviso '%s' de la OT %s: %s", tipo, ot.id, exc)


def _avisar_listo_para_retiro(db: Session, ot: OrdenTrabajo) -> None:
    """Feedback del usuario (flujo principal, 2026-09-11): al llegar a "listo",
    el cliente recibe el aviso de retiro con el horario de la sucursal."""
    cliente = _cliente(db, ot.cliente_id)
    email = cliente.get("email")
    if not email:
        return
    from sucursales import datos_contacto, horario_texto

    suc = datos_contacto(db, ot.sucursal_id) or {}
    try:
        from shared.correo import enviar

        enviar("servicio_listo_retiro", email, {
            "cliente_nombre": cliente.get("nombre"), "ot_numero": ot.numero,
            "sucursal_nombre": suc.get("nombre") or _sucursal_nombre(db, ot.sucursal_id),
            "sucursal_direccion": suc.get("direccion"),
            "horario": horario_texto(db, ot.sucursal_id),
        })
    except Exception as exc:  # noqa: BLE001  (el correo no bloquea la operación)
        logger.warning("no se pudo avisar al cliente que la OT %s está lista: %s", ot.id, exc)


def entregar(db: Session, oid: int, datos, *, user: CurrentUser) -> OrdenTrabajoDetalle:
    ot = _get(db, oid, for_update=True)
    if ot.estado != "listo":
        raise ConflictError("Solo se entrega una OT en estado 'listo'")

    # costeo definitivo
    c = costeo.costear(db, ot)
    ot.costo_interno = c.costo_interno
    if ot.precio_cobrado is None:
        ot.precio_cobrado = c.precio_sugerido
    ot.margen_real = (Decimal(str(ot.precio_cobrado)) - c.costo_interno).quantize(Decimal("0.01"))

    from shared.pagos import saldo

    s = saldo(db, documento_tipo="orden_trabajo", documento_id=oid, total=ot.precio_cobrado)
    if s > 0:
        if datos.autorizacion_credito_id is None:
            raise ConflictError(
                f"Saldo pendiente de {s}. Registra el pago o adjunta una autorización de crédito de Gerencia General"
            )
        from clientes import autorizacion_por_id

        aut = autorizacion_por_id(db, datos.autorizacion_credito_id)
        if aut is None:
            raise ValidationError("Autorización de crédito inexistente", field="autorizacion_credito_id")
        ot.autorizacion_credito_id = aut["id"]
        try:
            from ventas import crear_cxc_externa

            crear_cxc_externa(db, origen_tipo="orden_trabajo", origen_id=oid, cliente_id=ot.cliente_id, monto=s)
        except Exception as exc:  # noqa: BLE001  (009 podría no estar disponible en algún entorno)
            logger.warning("no se creó la CxC de la OT %s a crédito: %s", oid, exc)

    ot.fecha_real_entrega = datetime.now(timezone.utc)
    _transicionar(db, ot, "entregado", actor=user.id)

    # Sale del taller: vuelve a `vendido` (es del cliente), nunca a `disponible`
    # (bug 2026-09-11) — ver `inventario.marcar_reloj_en_servicio`.
    from inventario import revertir_reloj_servicio

    revertir_reloj_servicio(db, ot.reloj_id, orden_trabajo_id=ot.id, actor=user.id)

    # historial de serie (003) + nivel del cliente (006) + cita (007)
    rel = _reloj(db, ot.reloj_id)
    try:
        from inventario import registrar_evento_externo

        registrar_evento_externo(
            db, numero_serie=rel.get("numero_serie", ""), tipo="servicio",
            documento_tipo="orden_trabajo", documento_id=oid,
            detalle={"trabajo": ot.trabajo_realizado, "tecnico_id": ot.tecnico_id}, actor=user.id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se registró evento_serie de servicio (OT %s): %s", oid, exc)
    try:
        from clientes import recalcular_nivel

        recalcular_nivel(db, cliente_id=ot.cliente_id, hecho="servicio_entregado", documento_id=oid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se recalculó el nivel del cliente (OT %s): %s", oid, exc)
    if ot.cita_id:
        try:
            from citas import vincular_transaccion

            vincular_transaccion(db, ot.cita_id, orden_trabajo_id=oid, actor=user.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("no se vinculó la cita %s a la OT %s: %s", ot.cita_id, oid, exc)

    _avisar_ot_estado(db, ot, tipo="ot_entregado", hito="entregado")

    _generar_documentos(db, ot, rel, saldo_final=s if s > 0 else Decimal("0"))

    try:
        from contabilidad import generar_asiento

        generar_asiento(db, evento="ot_entregada", monto=ot.precio_cobrado, glosa=f"Servicio {ot.numero}",
                       origen="ot", origen_id=oid, actor=user.id)
        pagado = Decimal(str(ot.precio_cobrado)) - Decimal(str(s))
        if pagado > 0:
            generar_asiento(db, evento="cobro_cxc", monto=pagado, glosa=f"Cobro al entregar {ot.numero}",
                           origen="ot", origen_id=oid, actor=user.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se generó el asiento contable de la OT %s: %s", oid, exc)

    db.flush()
    registrar_cambio(db, actor=user.id, accion="entregar", entidad="orden_trabajo", entidad_id=oid,
                     despues={"fecha_real_entrega": ot.fecha_real_entrega.isoformat(),
                              "margen_real": str(ot.margen_real)})
    return _detalle(db, ot, user=user)


def _generar_documentos(db: Session, ot: OrdenTrabajo, rel: dict, *, saldo_final: Decimal) -> None:
    cli = _cliente(db, ot.cliente_id)
    piezas = [
        {"descripcion": (_pd(db, pu.pieza_id) or {}).get("descripcion", "—"),
         "tipo": pu.tipo_elegido, "cantidad": pu.cantidad}
        for pu in repository.piezas_de(db, ot.id)
    ]
    hasta = None
    if ot.fecha_real_entrega and ot.garantia_periodo_dias:
        hasta = (ot.fecha_real_entrega + timedelta(days=ot.garantia_periodo_dias)).date()
    ctx = {
        "numero": ot.numero,
        "cliente_nombre": cli.get("nombre"), "cliente_afiliado": cli.get("numero_afiliado"),
        "sucursal_nombre": _sucursal_nombre(db, ot.sucursal_id),
        "fecha_ingreso": ot.fecha_ingreso, "fecha_real_entrega": ot.fecha_real_entrega,
        "reloj_marca": rel.get("marca"), "reloj_referencia": rel.get("referencia"),
        "reloj_serie": rel.get("numero_serie"),
        "tecnico_nombre": _tecnico_nombre(db, ot.tecnico_id),
        "diagnostico": ot.diagnostico, "trabajo_realizado": ot.trabajo_realizado,
        "repuestos": piezas,
        "precio_cobrado": ot.precio_cobrado, "saldo": saldo_final,
        "garantia_cobertura": ot.garantia_cobertura, "garantia_periodo_dias": ot.garantia_periodo_dias,
        "garantia_hasta": hasta,
    }
    try:
        from shared.pdf import certificado_garantia, documento_orden_trabajo, guardar_comprobante

        doc = guardar_comprobante(f"ordenes-trabajo/{ot.numero}-ot.pdf", documento_orden_trabajo(ctx))
        cert = guardar_comprobante(f"ordenes-trabajo/{ot.numero}-garantia.pdf", certificado_garantia(ctx))
        repository.agregar_documento(db, orden_trabajo_id=ot.id, tipo="orden_trabajo", objeto=doc)
        repository.agregar_documento(db, orden_trabajo_id=ot.id, tipo="certificado_garantia", objeto=cert)
    except Exception as exc:  # noqa: BLE001  (MinIO no disponible en algunos entornos de test)
        logger.warning("no se generó/almacenó el PDF de la OT %s: %s", ot.id, exc)


def _pd(db: Session, pieza_id: int):
    from piezas import datos_pieza

    return datos_pieza(db, pieza_id)


def documento_url(db: Session, oid: int, tipo: str, *, user: CurrentUser) -> str:
    _get(db, oid)
    for d in repository.documentos_de(db, oid):
        if d.tipo == tipo:
            from shared.storage import get_object_url

            return get_object_url("comprobantes-venta", d.objeto)
    raise NotFoundError("Documento no encontrado para esta OT")


# ============================================================ garantía / daño
def reabrir_por_garantia(db: Session, oid: int, datos, *, user: CurrentUser) -> OrdenTrabajoOut:
    orig = _get(db, oid)
    if orig.estado != "entregado":
        raise ConflictError("Solo se reabre por garantía una OT ya entregada")
    ot = repository.crear(
        db, numero=repository.siguiente_numero(db), reloj_id=orig.reloj_id, cliente_id=orig.cliente_id,
        tecnico_id=orig.tecnico_id, sucursal_id=orig.sucursal_id, ot_original_id=orig.id,
        motivo=datos.motivo.strip(),
        tipo_reparacion=(datos.tipo_reparacion or orig.tipo_reparacion).strip(),
        estado="recibido", adquirido_en_tienda_ok=orig.adquirido_en_tienda_ok,
        garantia_periodo_dias=orig.garantia_periodo_dias, garantia_cobertura=orig.garantia_cobertura,
        reproceso=True, creado_por=user.id,
    )
    orig.reproceso = True
    repository.registrar_estado(db, orden_trabajo_id=ot.id, estado="recibido", actor_usuario_id=user.id)
    registrar_cambio(db, actor=user.id, accion="crear", entidad="orden_trabajo", entidad_id=ot.id,
                     despues={"reapertura_de": orig.id, "numero": ot.numero})
    return _ot_out(db, ot, user=user)


def reportar_dano(db: Session, oid: int, datos, *, user: CurrentUser) -> DanoPayloadOut:
    ot = _get(db, oid)
    _asegurar_puede_editar(db, user, ot)
    payload = DanoPayloadOut(
        orden_trabajo_id=oid, tecnico_id=ot.tecnico_id, descripcion=datos.descripcion.strip(),
        pieza_id=datos.pieza_id, reloj_serie=datos.reloj_serie or _reloj(db, ot.reloj_id).get("numero_serie"),
    )
    registrar_cambio(db, actor=user.id, accion="reportar_dano", entidad="orden_trabajo", entidad_id=oid,
                     despues=payload.model_dump())
    logger.info("daño en servicio reportado (OT %s) — pendiente de merma en 011", oid)
    return payload


# ============================================================ reportes
def ot_en_curso(db: Session, *, user: CurrentUser) -> list[OrdenTrabajoOut]:
    restr = _solo_propias(db, user)
    filas = repository.en_curso(db, sucursales=_sucursales_para_listado(db, user, solo_tecnico_id=restr))
    if restr is not None:
        filas = [o for o in filas if o.tecnico_id == restr]
    return [_ot_out(db, o, user=user) for o in filas]


def informe_servicios(
    db: Session, *, user: CurrentUser, cliente_id: int | None, tecnico_id: int | None,
    numero_serie: str | None, desde: date | None, hasta: date | None,
) -> list[InformeServicioOut]:
    reloj_ids = None
    if numero_serie and numero_serie.strip():
        from inventario import ids_relojes_por_serie

        reloj_ids = ids_relojes_por_serie(db, numero_serie)
    filas = repository.cerradas_entre(
        db, desde=desde, hasta=hasta, tecnico_id=tecnico_id, cliente_id=cliente_id, reloj_ids=reloj_ids,
    )
    restr = _solo_propias(db, user)
    sucs = _sucursales_para_listado(db, user, solo_tecnico_id=restr)
    salida = []
    for o in filas:
        if sucs is not None and o.sucursal_id not in sucs:
            continue
        if restr is not None and o.tecnico_id != restr:
            continue
        cli = _cliente(db, o.cliente_id)
        rel = _reloj(db, o.reloj_id)
        repuestos = [
            f"{(_pd(db, pu.pieza_id) or {}).get('codigo', pu.pieza_id)} ×{pu.cantidad} ({pu.tipo_elegido})"
            for pu in repository.piezas_de(db, o.id)
        ]
        salida.append(InformeServicioOut(
            orden_trabajo_id=o.id, numero=o.numero, cliente=cli.get("nombre"),
            tecnico=_tecnico_nombre(db, o.tecnico_id),
            fecha=o.fecha_real_entrega.date() if o.fecha_real_entrega else None,
            numero_serie=rel.get("numero_serie"), trabajo_realizado=o.trabajo_realizado,
            repuestos=repuestos, precio_arreglo=o.precio_cobrado,
        ))
    return salida


# ============================================================ proveedores a 005/006
def _proveedor_ot(db: Session, inicio: date, fin: date, tecnico_id: int | None):
    """005: OT entregadas del rango → indicadores y bono del técnico."""
    from tecnicos import OrdenTrabajoInfo

    salida = []
    for o in repository.ots_de_tecnico_cerradas(db, tecnico_id=tecnico_id, inicio=inicio, fin=fin):
        if o.tecnico_id is None:
            continue
        dentro = True
        if o.fecha_estimada_entrega and o.fecha_real_entrega:
            dentro = o.fecha_real_entrega.date() <= o.fecha_estimada_entrega
        salida.append(OrdenTrabajoInfo(
            orden_trabajo_id=o.id, tecnico_id=o.tecnico_id,
            fecha_cierre=o.fecha_real_entrega.date() if o.fecha_real_entrega else fin,
            margen_real=Decimal(str(o.margen_real or 0)),
            horas_registradas=float(o.horas_trabajadas) if o.horas_trabajadas is not None else None,
            tipo_reparacion=o.tipo_reparacion, dentro_de_tiempo=dentro, es_reproceso=o.reproceso,
        ))
    return salida


def _proveedor_transacciones(db: Session, cliente_id: int):
    """006: servicios entregados del cliente → motor de nivel y reportes."""
    from clientes import TransaccionCliente

    salida = []
    for o in repository.cerradas_entre(db, desde=None, hasta=None, tecnico_id=None,
                                       cliente_id=cliente_id, reloj_ids=None):
        salida.append(TransaccionCliente(
            cliente_id=cliente_id,
            fecha=o.fecha_real_entrega.date() if o.fecha_real_entrega else o.fecha_ingreso.date(),
            monto=Decimal(str(o.precio_cobrado or 0)), tipo="servicio",
            documento_id=o.id, detalle=f"Servicio {o.numero}: {o.trabajo_realizado or o.motivo}",
            sucursal_id=o.sucursal_id,
        ))
    return salida


def resumen_periodo(db: Session, *, sucursal_id: int, desde: date, hasta: date) -> dict:
    """Público (010): ingresos y costos de las OT entregadas de una sucursal en un
    rango de fechas, para la rentabilidad neta por sucursal (versión operativa)."""
    filas = repository.buscar(
        db, sucursales=[sucursal_id], solo_tecnico_id=None, estado="entregado",
        tecnico_id=None, sucursal_id=sucursal_id, reloj_ids=None, offset=0, limit=100000,
    )[0]
    ingresos = Decimal("0")
    costos = Decimal("0")
    for o in filas:
        if not (o.fecha_real_entrega and desde <= o.fecha_real_entrega.date() <= hasta):
            continue
        precio = Decimal(str(o.precio_cobrado or 0))
        costo = Decimal(str(o.costo_interno)) if o.costo_interno is not None else Decimal("0")
        ingresos += precio
        costos += costo
    return {"ingresos": ingresos.quantize(Decimal("0.01")), "costos": costos.quantize(Decimal("0.01"))}


# ============================================================ API pública (009)
def tiene_ot_activa_para_reloj(db: Session, reloj_id: int) -> bool:
    """Público (009): ¿hay una OT no entregada/cancelada sobre esta unidad? (bloquea la
    anulación de la venta hasta resolver el servicio)."""
    return any(
        o.reloj_id == reloj_id for o in repository.ots_no_entregadas(db)
    )


# ============================================================ consumidores 001
_consumidores_registrados = False
_proveedores_registrados = False


def _recalcular_por_parametro(db: Session, clave: str) -> int:
    """`margen_objetivo_servicio` cambió → recalcula el costeo de las OT no entregadas."""
    n = 0
    for o in repository.ots_no_entregadas(db):
        _recalcular_costeo(db, o)
        n += 1
    logger.info("recálculo de costeo de servicio (%s): %d OT abiertas", clave, n)
    return n


def registrar_consumidores() -> None:
    global _consumidores_registrados
    if _consumidores_registrados:
        return
    from shared.parametros import registrar_consumidor

    registrar_consumidor("margen_objetivo_servicio", _recalcular_por_parametro,
                         nombre="servicio_tecnico.recalculo_costeo")
    _consumidores_registrados = True


def registrar_proveedores() -> None:
    global _proveedores_registrados
    if _proveedores_registrados:
        return
    from clientes import registrar_proveedor_transacciones
    from tecnicos import registrar_proveedor_ot

    registrar_proveedor_ot(_proveedor_ot)
    registrar_proveedor_transacciones(_proveedor_transacciones)
    _proveedores_registrados = True
