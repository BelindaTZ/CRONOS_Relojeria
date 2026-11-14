"""Mermas y pérdidas (feature 011, Esp. §4.12): registro/costeo a costo de
adquisición, ciclo de estados con umbral de autorización de Gerencia General,
baja del inventario activo + asiento de pérdida extraordinaria en 010, y
reingreso ("reparado y reingresado")."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from mermas import repository
from mermas.models import Merma
from mermas.schemas import (
    AutorizacionBajaOut,
    DocumentoSoporteOut,
    HistorialEstadoOut,
    MermaOut,
    ReclamoOut,
    ReporteMermaItem,
)
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from shared.parametros import get_parametro
from shared.storage import get_object_url, put_object

_BUCKET = "documentos"
_ROLES_VER_COSTOS = {"Gerencia General", "Gerente de Sucursal", "Contador", "Administrador"}
_ESTADOS_TERMINALES = {"dado_de_baja", "reparado_reingresado"}


class NoAutorizadoError(ConflictError):
    status_code = 403
    code = "no_autorizado"


def puede_ver_costos(user: CurrentUser) -> bool:
    return bool(_ROLES_VER_COSTOS & set(getattr(user, "roles", []) or []))


def _sucursales(user: CurrentUser) -> list[int] | None:
    from inventario import sucursales_visibles

    return sucursales_visibles(user, None)


def _nombre_usuario(db: Session, usuario_id: int | None) -> str | None:
    if usuario_id is None:
        return None
    from shared.models import Usuario

    u = db.get(Usuario, usuario_id)
    return u.nombre if u else None


def _nombre_sucursal(db: Session, sucursal_id: int) -> str | None:
    from shared.models import Sucursal

    s = db.get(Sucursal, sucursal_id)
    return s.nombre if s else None


def _nombre_tecnico(db: Session, tecnico_id: int | None) -> str | None:
    if tecnico_id is None:
        return None
    from tecnicos import datos_para_correo

    datos = datos_para_correo(db, tecnico_id)
    return datos["nombre"] if datos else None


def _nombre_proveedor(db: Session, proveedor_id: int | None) -> str | None:
    if proveedor_id is None:
        return None
    from proveedores import proveedor_nombre

    return proveedor_nombre(db, proveedor_id)


def _merma_out(db: Session, m: Merma, *, user: CurrentUser) -> MermaOut:
    ver_costos = puede_ver_costos(user)
    reloj_serie = None
    pieza_codigo = None
    if m.reloj_id:
        from inventario import reloj_para_merma

        r = reloj_para_merma(db, m.reloj_id)
        reloj_serie = r["numero_serie"] if r else None
    if m.pieza_id:
        from piezas import datos_pieza

        p = datos_pieza(db, m.pieza_id)
        pieza_codigo = p["codigo"] if p else None

    categoria_nombre = None
    if m.categoria_merma_id:
        from shared.models import CategoriaMerma

        cat = db.get(CategoriaMerma, m.categoria_merma_id)
        categoria_nombre = cat.nombre if cat else None

    autorizacion = None
    if m.autorizacion_baja_id:
        from mermas.models import AutorizacionBaja

        a = db.get(AutorizacionBaja, m.autorizacion_baja_id)
        if a:
            autorizacion = AutorizacionBajaOut(
                autorizador_nombre=_nombre_usuario(db, a.autorizador_usuario_id) or "—",
                fecha=a.fecha, observacion=a.observacion,
            )

    return MermaOut(
        id=m.id, numero=m.numero, bien_tipo=m.bien_tipo, reloj_id=m.reloj_id, reloj_serie=reloj_serie,
        pieza_id=m.pieza_id, pieza_codigo=pieza_codigo, lote_id=m.lote_id, cantidad=m.cantidad,
        causa=m.causa, categoria_merma_id=m.categoria_merma_id, categoria_merma_nombre=categoria_nombre,
        descripcion=m.descripcion, fecha_evento=m.fecha_evento, sucursal_id=m.sucursal_id,
        sucursal_nombre=_nombre_sucursal(db, m.sucursal_id),
        responsable_nombre=_nombre_usuario(db, m.responsable_usuario_id),
        costo_perdida=Decimal(str(m.costo_perdida)) if ver_costos else None, costo_visible=ver_costos,
        estado=m.estado, orden_trabajo_id=m.orden_trabajo_id, tecnico_id=m.tecnico_id,
        tecnico_nombre=_nombre_tecnico(db, m.tecnico_id), transferencia_id=m.transferencia_id,
        autorizacion=autorizacion, asiento_id=m.asiento_id,
        documentos=[
            DocumentoSoporteOut(id=d.id, tipo=d.tipo, nombre=d.nombre, url=get_object_url(_BUCKET, d.objeto))
            for d in m.documentos
        ],
        reclamos=[
            ReclamoOut(
                id=r.id, destino=r.destino, proveedor_id=r.proveedor_id,
                proveedor_nombre=_nombre_proveedor(db, r.proveedor_id),
                aseguradora=r.aseguradora, estado=r.estado,
                monto_recuperado=Decimal(str(r.monto_recuperado)),
            )
            for r in m.reclamos
        ],
        historial=[
            HistorialEstadoOut(
                estado=h.estado, actor_nombre=_nombre_usuario(db, h.actor_usuario_id), creado_en=h.creado_en,
            )
            for h in m.historial
        ],
        creado_en=m.creado_en,
    )


# ==================================================================== US1 crear
def crear_merma(db: Session, datos, *, user: CurrentUser, discrepancia_id: int | None = None) -> MermaOut:
    from inventario import ids_relojes_por_serie, reloj_para_merma
    from piezas import costo_pieza, datos_pieza, stock_en

    reloj_id = datos.reloj_id
    if reloj_id is None and datos.numero_serie:
        ids = ids_relojes_por_serie(db, datos.numero_serie)
        reloj_id = ids[0] if ids else None

    if datos.categoria_merma_id is not None:
        from shared.models import CategoriaMerma

        cat = db.get(CategoriaMerma, datos.categoria_merma_id)
        if cat is None:
            raise ValidationError("Categoría de merma inexistente", field="categoria_merma_id")
        if cat.causa != datos.causa:
            raise ValidationError(
                f"«{cat.nombre}» es una categoría de «{cat.causa}», no de «{datos.causa}»",
                field="categoria_merma_id",
            )

    if datos.bien_tipo == "reloj":
        if reloj_id is None:
            raise ValidationError("Indica el reloj (id o número de serie)", field="reloj_id")
        r = reloj_para_merma(db, reloj_id)
        if r is None:
            raise NotFoundError("Unidad no encontrada")
        if r["disponibilidad"] in ("vendido", "dado_de_baja"):
            raise ConflictError(
                f"La unidad {r['numero_serie']} no puede reportarse en merma (estado: {r['disponibilidad']})"
            )
        costo_perdida = Decimal(str(r["costo_adquisicion"] or 0))
        cantidad = 1
        pieza_id = None
    else:
        if datos.pieza_id is None:
            raise ValidationError("Indica la pieza", field="pieza_id")
        p = datos_pieza(db, datos.pieza_id)
        if p is None:
            raise NotFoundError("Pieza no encontrada")
        cantidad = max(1, int(datos.cantidad or 1))
        disponible = stock_en(db, datos.pieza_id, datos.sucursal_id)
        if cantidad > disponible:
            raise ValidationError(
                f"La merma ({cantidad}) supera el stock disponible ({disponible}) de {p['codigo']}",
                field="cantidad",
            )
        costo_perdida = costo_pieza(db, datos.pieza_id) * cantidad
        reloj_id = None
        pieza_id = datos.pieza_id

    numero = repository.siguiente_numero(db)
    m = repository.crear(
        db, numero=numero, bien_tipo=datos.bien_tipo, reloj_id=reloj_id, pieza_id=pieza_id,
        lote_id=datos.lote_id, cantidad=cantidad, causa=datos.causa,
        categoria_merma_id=datos.categoria_merma_id, descripcion=(datos.descripcion or "").strip() or None,
        fecha_evento=datos.fecha_evento,
        sucursal_id=datos.sucursal_id, responsable_usuario_id=user.id, costo_perdida=costo_perdida,
        estado="en_evaluacion", orden_trabajo_id=datos.orden_trabajo_id, tecnico_id=datos.tecnico_id,
        transferencia_id=datos.transferencia_id,
    )
    repository.agregar_historial(db, merma_id=m.id, estado="en_evaluacion", actor_usuario_id=user.id)
    registrar_cambio(db, actor=user.id, accion="crear", entidad="merma", entidad_id=m.id,
                     despues={"numero": numero, "causa": datos.causa, "bien_tipo": datos.bien_tipo})

    if discrepancia_id:
        from traslados import vincular_merma

        vincular_merma(db, discrepancia_id, merma_id=m.id)

    return _merma_out(db, m, user=user)


def subir_documento(
    db: Session, mid: int, *, tipo: str, nombre: str, data: bytes, actor: int,
) -> DocumentoSoporteOut:
    m = repository.obtener(db, mid)
    if m is None:
        raise NotFoundError("Merma no encontrada")
    clave = f"mermas/{mid}/{uuid.uuid4().hex}-{nombre[:60]}"
    put_object(_BUCKET, clave, data, content_type="application/octet-stream")
    tipo_valido = tipo if tipo in {"acta", "fotografia", "denuncia", "otro"} else "otro"
    d = repository.agregar_documento(db, merma_id=mid, tipo=tipo_valido, objeto=clave, nombre=nombre, subido_por=actor)
    registrar_cambio(db, actor=actor, accion="crear", entidad="documento_soporte_merma", entidad_id=d.id,
                     despues={"merma_id": mid, "tipo": tipo_valido})
    return DocumentoSoporteOut(id=d.id, tipo=d.tipo, nombre=d.nombre, url=get_object_url(_BUCKET, clave))


# ============================================================ US2 autorización
def autorizar_baja(db: Session, mid: int, datos, *, user: CurrentUser) -> MermaOut:
    m = repository.obtener(db, mid, for_update=True)
    if m is None:
        raise NotFoundError("Merma no encontrada")
    a = repository.crear_autorizacion(
        db, merma_id=mid, autorizador_usuario_id=user.id, observacion=(datos.observacion or "").strip() or None,
    )
    m.autorizacion_baja_id = a.id
    db.flush()
    registrar_cambio(db, actor=user.id, accion="autorizar_baja", entidad="merma", entidad_id=mid,
                     despues={"autorizacion_baja_id": a.id, "observacion": a.observacion})
    return _merma_out(db, m, user=user)


# ================================================================ US3 estados
def cambiar_estado(db: Session, mid: int, datos, *, user: CurrentUser) -> MermaOut:
    m = repository.obtener(db, mid, for_update=True)
    if m is None:
        raise NotFoundError("Merma no encontrada")
    if m.estado in _ESTADOS_TERMINALES:
        raise ConflictError(f"La merma ya está en un estado terminal ({m.estado})")

    if datos.estado == "dado_de_baja":
        _dar_de_baja(db, m, user=user)
    elif datos.estado == "reparado_reingresado":
        _reingresar(db, m, user=user)
    else:
        m.estado = datos.estado
        db.flush()
        repository.agregar_historial(db, merma_id=m.id, estado=datos.estado, actor_usuario_id=user.id)
        registrar_cambio(db, actor=user.id, accion="cambiar_estado", entidad="merma", entidad_id=m.id,
                         despues={"estado": datos.estado})
    db.expire(m, ["historial", "documentos", "reclamos"])
    return _merma_out(db, m, user=user)


def _dar_de_baja(db: Session, m: Merma, *, user: CurrentUser) -> None:
    umbral = Decimal(str(get_parametro(db, "umbral_merma_autorizacion", default=0) or 0))
    costo = Decimal(str(m.costo_perdida))
    if costo > umbral and m.autorizacion_baja_id is None:
        raise ConflictError(
            f"La merma ({costo}) supera el umbral de autorización ({umbral}) — requiere autorización de Gerencia General"
        )

    if m.reloj_id:
        from inventario import marcar_reloj_baja

        marcar_reloj_baja(db, m.reloj_id, documento_id=m.id, actor=user.id)
    else:
        from piezas import dar_baja_pieza

        dar_baja_pieza(db, pieza_id=m.pieza_id, sucursal_id=m.sucursal_id, cantidad=m.cantidad,
                       documento_id=m.id, actor=user.id)

    try:
        from contabilidad import generar_asiento

        asiento = generar_asiento(
            db, evento="merma_confirmada", monto=costo, glosa=f"Merma {m.numero} — {m.causa}",
            origen="merma", origen_id=m.id, actor=user.id,
        )
        if asiento is not None:
            m.asiento_id = asiento.id
    except Exception:  # noqa: BLE001 — la baja del inventario nunca la bloquea la contabilidad
        pass

    m.estado = "dado_de_baja"
    db.flush()
    repository.agregar_historial(db, merma_id=m.id, estado="dado_de_baja", actor_usuario_id=user.id)
    registrar_cambio(db, actor=user.id, accion="dar_de_baja", entidad="merma", entidad_id=m.id,
                     despues={"asiento_id": m.asiento_id})


def _reingresar(db: Session, m: Merma, *, user: CurrentUser) -> None:
    if m.reloj_id:
        from inventario import revertir_reloj_baja

        revertir_reloj_baja(db, m.reloj_id, documento_id=m.id, actor=user.id)
    else:
        from piezas import reingresar_pieza

        reingresar_pieza(db, pieza_id=m.pieza_id, sucursal_id=m.sucursal_id, cantidad=m.cantidad,
                         documento_id=m.id, actor=user.id)

    m.estado = "reparado_reingresado"
    db.flush()
    repository.agregar_historial(db, merma_id=m.id, estado="reparado_reingresado", actor_usuario_id=user.id)
    registrar_cambio(db, actor=user.id, accion="reingresar", entidad="merma", entidad_id=m.id)


# ================================================================== US4 reclamo
def crear_reclamo(db: Session, mid: int, datos, *, user: CurrentUser) -> MermaOut:
    m = repository.obtener(db, mid)
    if m is None:
        raise NotFoundError("Merma no encontrada")
    r = repository.crear_reclamo(
        db, merma_id=mid, destino=datos.destino, proveedor_id=datos.proveedor_id,
        aseguradora=(datos.aseguradora or "").strip() or None, estado="abierto",
    )
    m.estado = "en_reclamo_proveedor" if datos.destino == "proveedor" else "en_reclamo_seguro"
    db.flush()
    repository.agregar_historial(db, merma_id=m.id, estado=m.estado, actor_usuario_id=user.id)
    registrar_cambio(db, actor=user.id, accion="crear", entidad="reclamo_merma", entidad_id=r.id,
                     despues={"merma_id": mid, "destino": datos.destino})
    db.expire(m, ["historial", "reclamos"])
    return _merma_out(db, m, user=user)


def actualizar_reclamo(db: Session, mid: int, datos, *, actor: int) -> ReclamoOut:
    r = repository.reclamo_de_merma(db, mid)
    if r is None:
        raise NotFoundError("La merma no tiene un reclamo registrado")
    antes = {"estado": r.estado, "monto_recuperado": str(r.monto_recuperado)}
    if datos.estado is not None:
        r.estado = datos.estado
    if datos.monto_recuperado is not None:
        r.monto_recuperado = datos.monto_recuperado
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="reclamo_merma", entidad_id=r.id,
                     antes=antes, despues={"estado": r.estado, "monto_recuperado": str(r.monto_recuperado)})
    return ReclamoOut(
        id=r.id, destino=r.destino, proveedor_id=r.proveedor_id,
        proveedor_nombre=_nombre_proveedor(db, r.proveedor_id), aseguradora=r.aseguradora,
        estado=r.estado, monto_recuperado=Decimal(str(r.monto_recuperado)),
    )


# =================================================================== listados
def listar(
    db: Session, *, user: CurrentUser, causa: str | None, estado: str | None, sucursal_id: int | None,
    desde: date | None, hasta: date | None, offset: int, limit: int,
) -> tuple[list[MermaOut], int]:
    filas, total = repository.buscar(
        db, sucursales=_sucursales(user), sucursal_id=sucursal_id, causa=causa, estado=estado,
        desde=desde, hasta=hasta, offset=offset, limit=limit,
    )
    return [_merma_out(db, m, user=user) for m in filas], total


def obtener(db: Session, mid: int, *, user: CurrentUser) -> MermaOut:
    m = repository.obtener(db, mid)
    if m is None:
        raise NotFoundError("Merma no encontrada")
    return _merma_out(db, m, user=user)


def reporte_mermas(
    db: Session, *, user: CurrentUser, causa: str | None, sucursal_id: int | None,
    desde: date | None, hasta: date | None,
) -> list[ReporteMermaItem]:
    sucursales = _sucursales(user)
    if sucursal_id:
        sucursales = [sucursal_id] if sucursales is None or sucursal_id in sucursales else []
    filas = repository.para_reporte(db, sucursales=sucursales, causa=causa, desde=desde, hasta=hasta)
    agrupado: dict[str, list[Decimal]] = {}
    for m in filas:
        agrupado.setdefault(m.causa, []).append(Decimal(str(m.costo_perdida)))
    return [
        ReporteMermaItem(causa=c, frecuencia=len(montos), monto_total=sum(montos))
        for c, montos in sorted(agrupado.items())
    ]
