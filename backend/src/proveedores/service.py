"""Lógica del módulo `proveedores` (feature 002).

- Ficha de proveedor con campos restringidos a rol elevado (razón social, RUC/NIT).
- Órdenes de compra: borrador → emitida → parcial → recibida (o cancelada).
- Recepción total/parcial: sobre-entrega, `desfase_dias`, lote/caducidad para
  perecederos, propagación a Inventario (003) vía receptores registrados.
- Calificación: `nota_plazos` DERIVADA del cumplimiento de plazos; calidad/soporte manuales.
- Compras programadas + generación de borradores por frecuencia.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from proveedores import repository
from proveedores.models import LineaOrdenCompra, OrdenCompra, RecepcionLinea
from shared.correo import enviar
from proveedores.schemas import (
    CalificacionOut,
    CompraProgramadaIn,
    CompraProgramadaOut,
    CorreccionIn,
    LineaIn,
    LineaOut,
    OrdenCompraIn,
    OrdenCompraOut,
    PrellenarIn,
    PrellenarOut,
    ProveedorDetalle,
    ProveedorIn,
    ProveedorOut,
    ProveedorPatch,
    RecepcionIn,
)
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, DomainError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from shared.parametros import get_parametro
from shared.storage import get_object_url, put_object

logger = logging.getLogger("cronos.proveedores")

_BUCKET_DOCS = "documentos"
_ROLES_ELEVADOS = {"Gerencia General", "Gerente de Sucursal"}

# Inventario (003) registra aquí un receptor: fn(db, orden, [(linea, cant, lote, cad)])
ReceptorInventario = Callable[[Session, OrdenCompra, list[tuple]], None]
_RECEPTORES_INVENTARIO: list[ReceptorInventario] = []


def registrar_receptor_inventario(fn: ReceptorInventario) -> None:
    _RECEPTORES_INVENTARIO.append(fn)


# Contabilidad (010) registra aquí un receptor: fn(db, orden) — se llama cuando la
# orden queda completamente recibida (crea la CxP por `importe_a_pagar`).
ReceptorCxp = Callable[[Session, OrdenCompra], None]
_RECEPTORES_CXP: list[ReceptorCxp] = []


def registrar_receptor_cxp(fn: ReceptorCxp) -> None:
    _RECEPTORES_CXP.append(fn)


def es_rol_elevado(user: CurrentUser) -> bool:
    return bool(_ROLES_ELEVADOS & set(user.roles))


class NoAutorizadoError(DomainError):
    status_code = 403
    code = "rol_no_elevado"


# ============================================================ proveedor
def _condicion_label(db: Session, condicion_pago_id: int | None) -> str | None:
    if not condicion_pago_id:
        return None
    from shared.models import CondicionPago

    c = db.get(CondicionPago, condicion_pago_id)
    return c.nombre if c else None


def _prov_out(db: Session, p) -> ProveedorOut:
    marca_ids = repository.marcas_autorizadas_de(db, p.id)
    nombres = repository.nombres_marca(db, marca_ids)
    return ProveedorOut(
        id=p.id,
        razon_social=p.razon_social,
        nombre_comercial=p.nombre_comercial,
        contacto_nombre=p.contacto_nombre,
        telefono=p.telefono,
        email=p.email,
        ruc_nit=p.ruc_nit,
        certificacion_autorizada=p.certificacion_autorizada,
        marcas_autorizadas=marca_ids,
        marcas_autorizadas_nombres=[nombres.get(i, f"#{i}") for i in marca_ids],
        condicion_pago_id=p.condicion_pago_id,
        condicion_pago=_condicion_label(db, p.condicion_pago_id),
        plazo_entrega_dias=p.plazo_entrega_dias,
        indicador_plazos_dias=p.indicador_plazos_dias,
        estado=p.estado,
        tipos=repository.tipos_de(db, p.id),
    )


def listar(db, *, q, tipo, estado, offset, limit) -> tuple[list[ProveedorOut], int]:
    filas, total = repository.buscar(db, q=q, tipo=tipo, estado=estado, offset=offset, limit=limit)
    return [_prov_out(db, p) for p in filas], total


def crear(db: Session, datos: ProveedorIn, *, actor: int) -> ProveedorOut:
    if datos.ruc_nit and repository.por_ruc(db, datos.ruc_nit):
        raise ConflictError("Ya existe un proveedor con ese RUC/NIT", field="ruc_nit")
    from proveedores.models import Proveedor

    p = Proveedor(
        razon_social=datos.razon_social,
        nombre_comercial=datos.nombre_comercial,
        contacto_nombre=datos.contacto_nombre,
        telefono=datos.telefono,
        email=datos.email,
        ruc_nit=datos.ruc_nit,
        certificacion_autorizada=datos.certificacion_autorizada,
        condicion_pago_id=datos.condicion_pago_id,
        plazo_entrega_dias=datos.plazo_entrega_dias,
        estado="activo",
    )
    db.add(p)
    db.flush()
    if datos.tipos:
        repository.set_tipos(db, p.id, datos.tipos)
    if datos.certificacion_autorizada and datos.marcas_autorizadas:
        repository.set_marcas_autorizadas(db, p.id, datos.marcas_autorizadas)
    registrar_cambio(db, actor=actor, accion="crear", entidad="proveedor", entidad_id=p.id,
                     despues=datos.model_dump(exclude_none=True))
    return _prov_out(db, p)


def obtener_detalle(db: Session, pid: int) -> ProveedorDetalle:
    p = repository.obtener(db, pid)
    if p is None:
        raise NotFoundError("Proveedor no encontrado")
    cal = repository.calificacion_vigente(db, pid)
    base = _prov_out(db, p).model_dump()
    return ProveedorDetalle(
        **base,
        calificacion_vigente=(
            CalificacionOut(
                nota_plazos=cal.nota_plazos,
                nota_calidad=cal.nota_calidad,
                nota_soporte=cal.nota_soporte,
                nota_agregada=cal.nota_agregada,
                creado_en=cal.creado_en,
            )
            if cal
            else None
        ),
        historial_compras=[_orden_out(db, o) for o in repository.ordenes_de_proveedor(db, pid)],
    )


def actualizar(db: Session, pid: int, datos: ProveedorPatch, *, user: CurrentUser) -> ProveedorOut:
    p = repository.obtener(db, pid)
    if p is None:
        raise NotFoundError("Proveedor no encontrado")

    restringidos = {"razon_social", "ruc_nit"}
    cambios = datos.model_dump(exclude_unset=True)
    if restringidos & cambios.keys() and not es_rol_elevado(user):
        raise NoAutorizadoError("Razón social y RUC/NIT solo los cambia un rol elevado")

    antes = _prov_out(db, p).model_dump()
    if "ruc_nit" in cambios and cambios["ruc_nit"] and cambios["ruc_nit"] != p.ruc_nit:
        if repository.por_ruc(db, cambios["ruc_nit"]):
            raise ConflictError("Ese RUC/NIT ya está en uso", field="ruc_nit")

    for campo in (
        "razon_social", "ruc_nit", "nombre_comercial", "contacto_nombre", "telefono",
        "email", "condicion_pago_id", "certificacion_autorizada", "plazo_entrega_dias",
    ):
        if campo in cambios:
            setattr(p, campo, cambios[campo])
    if "tipos" in cambios and cambios["tipos"] is not None:
        repository.set_tipos(db, p.id, cambios["tipos"])
    if "marcas_autorizadas" in cambios and cambios["marcas_autorizadas"] is not None:
        repository.set_marcas_autorizadas(db, p.id, cambios["marcas_autorizadas"])
    if p.certificacion_autorizada is False:
        repository.set_marcas_autorizadas(db, p.id, [])
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="proveedor", entidad_id=pid,
                     antes=antes, despues=_prov_out(db, p).model_dump())
    return _prov_out(db, p)


def inactivar(db: Session, pid: int, *, actor: int) -> ProveedorOut:
    p = repository.obtener(db, pid)
    if p is None:
        raise NotFoundError("Proveedor no encontrado")
    p.estado = "inactivo"
    db.flush()
    registrar_cambio(db, actor=actor, accion="inactivar", entidad="proveedor", entidad_id=pid)
    return _prov_out(db, p)


def subir_documento(
    db: Session, pid: int, *, tipo: str, nombre: str, data: bytes, actor: int
) -> dict:
    if repository.obtener(db, pid) is None:
        raise NotFoundError("Proveedor no encontrado")
    clave = f"proveedor/{pid}/{uuid.uuid4().hex}-{nombre[:60]}"
    put_object(_BUCKET_DOCS, clave, data, content_type="application/octet-stream")
    d = repository.agregar_documento(
        db, proveedor_id=pid, tipo=tipo if tipo in {"certificado", "ruc", "contrato", "otro"} else "otro",
        objeto=clave, nombre=nombre, subido_por=actor,
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="proveedor_documento", entidad_id=d.id,
                     despues={"proveedor_id": pid, "tipo": d.tipo})
    return {"id": d.id, "tipo": d.tipo, "nombre": d.nombre, "url": get_object_url(_BUCKET_DOCS, clave)}


def listar_documentos(db: Session, pid: int) -> list[dict]:
    return [
        {"id": d.id, "tipo": d.tipo, "nombre": d.nombre, "url": get_object_url(_BUCKET_DOCS, d.objeto)}
        for d in repository.documentos_de(db, pid)
    ]


# ============================================================ calificación
def _nota_plazos_desde_indicador(indicador: float | None) -> Decimal | None:
    if indicador is None:
        return None
    for umbral, nota in ((0, "5.0"), (2, "4.0"), (5, "3.0"), (10, "2.0")):
        if indicador <= umbral:
            return Decimal(nota)
    return Decimal("1.0")


def _promedio(*valores) -> Decimal | None:
    xs = [Decimal(str(v)) for v in valores if v is not None]
    if not xs:
        return None
    return (sum(xs) / len(xs)).quantize(Decimal("0.1"))


def calificar(db: Session, pid: int, *, nota_calidad, nota_soporte, actor: int):
    p = repository.obtener(db, pid)
    if p is None:
        raise NotFoundError("Proveedor no encontrado")

    vigente = repository.calificacion_vigente(db, pid)
    calidad = nota_calidad if nota_calidad is not None else (vigente.nota_calidad if vigente else None)
    soporte = nota_soporte if nota_soporte is not None else (vigente.nota_soporte if vigente else None)
    nota_plazos = _nota_plazos_desde_indicador(
        float(p.indicador_plazos_dias) if p.indicador_plazos_dias is not None else None
    )
    agregada = _promedio(nota_plazos, calidad, soporte)

    c = repository.agregar_calificacion(
        db, proveedor_id=pid, nota_plazos=nota_plazos, nota_calidad=calidad,
        nota_soporte=soporte, nota_agregada=agregada, autor_usuario_id=actor,
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="calificacion_proveedor", entidad_id=c.id,
                     despues={"proveedor_id": pid, "nota_calidad": str(calidad), "nota_soporte": str(soporte)})
    return CalificacionOut(
        nota_plazos=c.nota_plazos, nota_calidad=c.nota_calidad, nota_soporte=c.nota_soporte,
        nota_agregada=c.nota_agregada, creado_en=c.creado_en,
    )


def _recalcular_indicador(db: Session, proveedor_id: int) -> None:
    n = int(get_parametro(db, "proveedores_n_recepciones_indicador", default=10) or 10)
    desfases = repository.desfases_recientes(db, proveedor_id, n)
    p = repository.obtener(db, proveedor_id)
    if not desfases:
        return
    p.indicador_plazos_dias = Decimal(str(sum(desfases) / len(desfases))).quantize(Decimal("0.01"))
    # retroalimenta la nota de plazos de la calificación vigente (sin tocar las manuales)
    vigente = repository.calificacion_vigente(db, proveedor_id)
    if vigente:
        vigente.nota_plazos = _nota_plazos_desde_indicador(float(p.indicador_plazos_dias))
        vigente.nota_agregada = _promedio(vigente.nota_plazos, vigente.nota_calidad, vigente.nota_soporte)
    db.flush()


# ============================================================ órdenes de compra
def _orden_out(db: Session, o: OrdenCompra) -> OrdenCompraOut:
    recibido = repository.recibido_por_linea(db, o.id)
    reales = repository.costo_real_por_linea(db, o.id)
    factura = repository.ultima_factura(db, o.id)
    return OrdenCompraOut(
        id=o.id, proveedor_id=o.proveedor_id, sucursal_destino_id=o.sucursal_destino_id,
        tipo=o.tipo, urgente=o.urgente, estado=o.estado, fecha_emision=o.fecha_emision,
        fecha_confirmacion=o.fecha_confirmacion, fecha_pactada=o.fecha_pactada,
        importe_a_pagar=o.importe_a_pagar, condiciones_pago=o.condiciones_pago,
        retencion_aplicable=o.retencion_aplicable,
        numero_factura=factura.get("numero_factura"), numero_guia=factura.get("numero_guia"),
        lineas=[
            LineaOut(
                id=l.id, item_tipo=l.item_tipo, item_ref=l.item_ref, marca=l.marca,
                calibre_codigo=l.calibre_codigo, anio=l.anio, numero_serie=l.numero_serie,
                pieza_id=l.pieza_id, pieza_tipo=l.pieza_tipo, unidad_medida=l.unidad_medida,
                marca_compatible=l.marca_compatible, descripcion=l.descripcion,
                observaciones=l.observaciones,
                cantidad=l.cantidad, costo_unitario=l.costo_unitario, es_perecedero=l.es_perecedero,
                cantidad_recibida=recibido.get(l.id, 0),
                costo_unitario_real=Decimal(str(reales[l.id])) if l.id in reales else None,
            )
            for l in o.lineas
        ],
    )


def _pieza_catalogo_info(db: Session, pieza_id: int) -> dict | None:
    from piezas import datos_pieza

    return datos_pieza(db, pieza_id)


def ultimo_precio(db: Session, *, item_tipo, marca, referencia, pieza_id):
    from proveedores.schemas import UltimoPrecioOut

    r = repository.ultimo_precio_item(
        db, item_tipo=item_tipo, marca=marca, referencia=referencia, pieza_id=pieza_id
    )
    if r is None:
        return UltimoPrecioOut()
    return UltimoPrecioOut(costo=Decimal(str(r["costo"])), fecha=r["fecha"], fuente=r["fuente"])


def _importe(lineas: list[LineaIn] | list[LineaOrdenCompra]) -> Decimal:
    return sum(
        (Decimal(str(l.costo_unitario or 0)) * l.cantidad for l in lineas), Decimal("0")
    )


def _recomputar_importe(db: Session, o: OrdenCompra) -> None:
    """Importe = costo real por línea (si ya se informó al recibir) o el estimado."""
    reales = repository.costo_real_por_linea(db, o.id)
    total = Decimal("0")
    for l in o.lineas:
        unit = reales.get(l.id, float(l.costo_unitario or 0))
        total += Decimal(str(unit)) * l.cantidad
    o.importe_a_pagar = total
    db.flush()


def crear_orden(db: Session, datos: OrdenCompraIn, *, actor: int, tipo: str = "puntual",
                compra_programada_id: int | None = None) -> OrdenCompraOut:
    prov = repository.obtener(db, datos.proveedor_id)
    if prov is None:
        raise NotFoundError("Proveedor no encontrado")
    o = repository.crear_orden(
        db, proveedor_id=datos.proveedor_id, sucursal_destino_id=datos.sucursal_destino_id,
        tipo=tipo, urgente=datos.urgente, compra_programada_id=compra_programada_id, estado="borrador",
        fecha_pactada=datos.fecha_pactada,
        condiciones_pago=datos.condiciones_pago or _condicion_label(db, prov.condicion_pago_id),
        retencion_aplicable=datos.retencion_aplicable,
        importe_a_pagar=_importe(datos.lineas), creado_por=actor,
    )
    for l in datos.lineas:
        campos_linea = dict(
            orden_compra_id=o.id, item_tipo=l.item_tipo, item_ref=l.item_ref,
            marca=l.marca, calibre_codigo=l.calibre_codigo, anio=l.anio, numero_serie=l.numero_serie,
            pieza_id=l.pieza_id, pieza_tipo=l.pieza_tipo, unidad_medida=l.unidad_medida,
            marca_compatible=l.marca_compatible, descripcion=l.descripcion,
            observaciones=l.observaciones,
            cantidad=l.cantidad, costo_unitario=l.costo_unitario, es_perecedero=l.es_perecedero,
        )
        # pieza del catálogo: hereda descripción/tipo/unidad/perecedero para la recepción
        if l.item_tipo == "pieza" and l.pieza_id:
            info = _pieza_catalogo_info(db, l.pieza_id)
            if info:
                campos_linea["item_ref"] = campos_linea["item_ref"] or info["codigo"]
                campos_linea["pieza_tipo"] = campos_linea["pieza_tipo"] or info["tipo"]
                campos_linea["unidad_medida"] = campos_linea["unidad_medida"] or info["unidad_medida"]
                campos_linea["marca_compatible"] = campos_linea["marca_compatible"] or info["marca_compatible"]
                campos_linea["es_perecedero"] = campos_linea["es_perecedero"] or info["perecedera"]
        db.add(LineaOrdenCompra(**campos_linea))
    db.flush()
    db.refresh(o)
    registrar_cambio(db, actor=actor, accion="crear", entidad="orden_compra", entidad_id=o.id,
                     despues={"proveedor_id": o.proveedor_id, "tipo": tipo})
    return _orden_out(db, o)


def listar_ordenes(db, *, proveedor_id, tipo, estado, offset, limit):
    filas, total = repository.buscar_ordenes(
        db, proveedor_id=proveedor_id, tipo=tipo, estado=estado, offset=offset, limit=limit
    )
    return [_orden_out(db, o) for o in filas], total


def emitir_orden(db: Session, oid: int, *, actor: int) -> OrdenCompraOut:
    o = repository.obtener_orden(db, oid)
    if o is None:
        raise NotFoundError("Orden no encontrada")
    if o.estado != "borrador":
        raise ConflictError(f"Solo se emite una orden en borrador (estado actual: {o.estado})")
    if not o.lineas:
        raise ValidationError("La orden no tiene líneas", field="lineas")
    o.estado = "emitida"
    o.fecha_emision = date.today()
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="orden_compra", entidad_id=oid,
                     antes={"estado": "borrador"}, despues={"estado": "emitida"})
    return _orden_out(db, o)


def confirmar_orden(db: Session, oid: int, *, user: CurrentUser) -> OrdenCompraOut:
    """Un rol elevado marca que el proveedor ACEPTÓ el pedido (acordado por otro
    canal). Solo desde `emitida`. Requisito para poder recibir."""
    if not es_rol_elevado(user):
        raise NoAutorizadoError("Confirmar la aceptación del proveedor requiere rol elevado")
    o = repository.obtener_orden(db, oid)
    if o is None:
        raise NotFoundError("Orden no encontrada")
    if o.estado != "emitida":
        raise ConflictError(f"Solo se confirma una orden emitida (estado actual: {o.estado})")
    o.estado = "confirmada"
    o.fecha_confirmacion = datetime.now(timezone.utc)
    o.confirmada_por = user.id
    db.flush()
    registrar_cambio(db, actor=user.id, accion="confirmar", entidad="orden_compra", entidad_id=oid,
                     antes={"estado": "emitida"}, despues={"estado": "confirmada"})
    return _orden_out(db, o)


def cancelar_orden(db: Session, oid: int, *, motivo: str, actor: int) -> OrdenCompraOut:
    o = repository.obtener_orden(db, oid)
    if o is None:
        raise NotFoundError("Orden no encontrada")
    if o.estado in ("recibida", "cancelada"):
        raise ConflictError(f"No se cancela una orden en estado '{o.estado}'")
    if not motivo or len(motivo.strip()) < 5:
        raise ValidationError("El motivo de cancelación es obligatorio", field="motivo")

    # Regla de negocio: no cancelar si faltan menos de N horas para la fecha pactada.
    if o.fecha_pactada:
        horas_min = int(get_parametro(db, "oc_horas_min_cancelacion", default=24) or 24)
        limite = datetime.combine(o.fecha_pactada, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=horas_min)
        if datetime.now(timezone.utc) >= limite:
            raise ConflictError(
                f"No se puede cancelar: faltan menos de {horas_min} h para la fecha pactada "
                f"({o.fecha_pactada}). Contacta al proveedor."
            )

    prov = repository.obtener(db, o.proveedor_id)
    o.estado = "cancelada"
    db.flush()

    if prov and prov.email:
        try:
            enviar(
                "cancelacion_orden",
                prov.email,
                {
                    "proveedor": prov.razon_social,
                    "orden": o.id,
                    "motivo": motivo.strip(),
                    "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                },
            )
        except Exception:  # noqa: BLE001
            logger.exception("Fallo al avisar al proveedor de la cancelación de la orden %s", oid)

    registrar_cambio(db, actor=actor, accion="cancelar", entidad="orden_compra", entidad_id=oid,
                     despues={"estado": "cancelada", "motivo": motivo.strip()})
    return _orden_out(db, o)


def registrar_recepcion(db: Session, oid: int, datos: RecepcionIn, *, actor: int) -> OrdenCompraOut:
    o = repository.obtener_orden(db, oid)
    if o is None:
        raise NotFoundError("Orden no encontrada")
    if o.estado not in ("confirmada", "parcial"):
        raise ConflictError(
            f"No se puede recibir una orden en estado '{o.estado}'. "
            "Debe estar confirmada (el proveedor aceptó el pedido)."
        )

    lineas_por_id = {l.id: l for l in o.lineas}
    recibido_prev = repository.recibido_por_linea(db, oid)

    desfase = (datos.fecha_real - o.fecha_pactada).days if o.fecha_pactada else None
    rec = repository.crear_recepcion(
        db, orden_compra_id=oid, fecha_real=datos.fecha_real,
        responsable_usuario_id=actor, desfase_dias=desfase,
        numero_factura=(datos.numero_factura or "").strip() or None,
        numero_guia=(datos.numero_guia or "").strip() or None,
    )

    propagacion: list[tuple] = []
    for rl in datos.lineas:
        linea = lineas_por_id.get(rl.linea_orden_compra_id)
        if linea is None:
            raise ValidationError(f"Línea {rl.linea_orden_compra_id} no pertenece a la orden", field="lineas")
        if linea.es_perecedero and (not rl.lote or not rl.fecha_caducidad):
            raise ValidationError(
                f"El ítem '{linea.item_ref}' es perecedero: lote y fecha de caducidad son obligatorios",
                field="lote",
            )
        pendiente = linea.cantidad - recibido_prev.get(linea.id, 0)
        sobre = rl.cantidad_recibida > pendiente
        db.add(RecepcionLinea(
            recepcion_compra_id=rec.id, linea_orden_compra_id=linea.id,
            cantidad_recibida=rl.cantidad_recibida, costo_unitario=rl.costo_unitario,
            lote=rl.lote, fecha_caducidad=rl.fecha_caducidad, sobre_entrega=sobre,
        ))
        propagacion.append((linea, rl.cantidad_recibida, rl.lote, rl.fecha_caducidad))
    db.flush()
    _recomputar_importe(db, o)

    # ¿completa?
    recibido_ahora = repository.recibido_por_linea(db, oid)
    completa = all(recibido_ahora.get(l.id, 0) >= l.cantidad for l in o.lineas)
    o.estado = "recibida" if completa else "parcial"
    db.flush()

    # propaga a Inventario (003) — receptores registrados
    for fn in _RECEPTORES_INVENTARIO:
        try:
            fn(db, o, propagacion)
        except Exception:  # noqa: BLE001
            logger.exception("Receptor de inventario falló para orden %s", oid)

    # orden completa ⇒ la obligación de pago es real: avisa a Contabilidad (010)
    if completa:
        for fn in _RECEPTORES_CXP:
            try:
                fn(db, o)
            except Exception:  # noqa: BLE001
                logger.exception("Receptor de CxP falló para orden %s", oid)

    _recalcular_indicador(db, o.proveedor_id)
    registrar_cambio(db, actor=actor, accion="crear", entidad="recepcion_compra", entidad_id=rec.id,
                     despues={"orden": oid, "estado_orden": o.estado, "desfase_dias": desfase})
    return _orden_out(db, o)


def corregir_orden(db: Session, oid: int, datos: CorreccionIn, *, user: CurrentUser) -> OrdenCompraOut:
    if not es_rol_elevado(user):
        raise NoAutorizadoError("Corregir una compra recibida requiere rol elevado")
    o = repository.obtener_orden(db, oid)
    if o is None:
        raise NotFoundError("Orden no encontrada")
    if o.estado != "recibida":
        raise ConflictError("Solo se corrige una orden ya recibida")

    lineas_por_id = {l.id: l for l in o.lineas}
    antes = _orden_out(db, o).model_dump()
    for c in datos.lineas:
        linea = lineas_por_id.get(c.id)
        if linea is None:
            raise ValidationError(f"Línea {c.id} no pertenece a la orden", field="lineas")
        if c.cantidad is not None:
            linea.cantidad = c.cantidad
        if c.costo_unitario is not None:
            linea.costo_unitario = c.costo_unitario
        if c.item_ref is not None:
            linea.item_ref = c.item_ref
    o.importe_a_pagar = _importe(o.lineas)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="corregir", entidad="orden_compra", entidad_id=oid,
                     antes=antes, despues={**_orden_out(db, o).model_dump(), "motivo": datos.motivo})
    return _orden_out(db, o)


def prellenar_orden(db: Session, datos: PrellenarIn) -> PrellenarOut:
    proveedor_id = datos.proveedor_id
    requiere = False
    if proveedor_id is None:
        # heurística: proveedor habitual = el de la última orden con ese ítem
        from sqlalchemy import select

        proveedor_id = db.scalar(
            select(OrdenCompra.proveedor_id)
            .join(LineaOrdenCompra, LineaOrdenCompra.orden_compra_id == OrdenCompra.id)
            .where(LineaOrdenCompra.item_ref == datos.item_ref, LineaOrdenCompra.item_tipo == datos.item_tipo)
            .order_by(OrdenCompra.creado_en.desc())
            .limit(1)
        )
        requiere = proveedor_id is None

    return PrellenarOut(
        proveedor_id=proveedor_id,
        requiere_elegir_proveedor=requiere,
        lineas=[LineaIn(
            item_tipo=datos.item_tipo, item_ref=datos.item_ref,
            descripcion=None, cantidad=datos.cantidad_sugerida, costo_unitario=Decimal("0"),
        )],
    )


# ============================================================ compras programadas
def _avanzar(fecha: datetime, frecuencia: str) -> datetime:
    if frecuencia == "semanal":
        return fecha + timedelta(weeks=1)
    if frecuencia == "trimestral":
        return fecha + timedelta(days=91)
    return fecha + timedelta(days=30)  # mensual


def _prog_out(p) -> CompraProgramadaOut:
    return CompraProgramadaOut(
        id=p.id, proveedor_id=p.proveedor_id, sucursal_destino_id=p.sucursal_destino_id,
        frecuencia=p.frecuencia, estado=p.estado, proxima_generacion=p.proxima_generacion,
        plantilla_lineas=p.plantilla_lineas,
    )


def crear_programada(db: Session, datos: CompraProgramadaIn, *, actor: int) -> CompraProgramadaOut:
    if repository.obtener(db, datos.proveedor_id) is None:
        raise NotFoundError("Proveedor no encontrado")
    prox = datos.proxima_generacion or datetime.now(timezone.utc)
    p = repository.crear_programada(
        db, proveedor_id=datos.proveedor_id, sucursal_destino_id=datos.sucursal_destino_id,
        frecuencia=datos.frecuencia, proxima_generacion=prox, estado="activa",
        plantilla_lineas=[l.model_dump(mode="json") for l in datos.plantilla_lineas], creado_por=actor,
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="compra_programada", entidad_id=p.id,
                     despues={"frecuencia": p.frecuencia})
    return _prog_out(p)


def listar_programadas(db: Session) -> list[CompraProgramadaOut]:
    return [_prog_out(p) for p in repository.listar_programadas(db)]


def set_estado_programada(db: Session, pid: int, estado: str, *, actor: int) -> CompraProgramadaOut:
    p = repository.obtener_programada(db, pid)
    if p is None:
        raise NotFoundError("Compra programada no encontrada")
    p.estado = estado
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="compra_programada", entidad_id=pid,
                     despues={"estado": estado})
    return _prog_out(p)


def _recalcular_todos_los_indicadores(db: Session, _clave: str) -> int:
    """Consumidor de `shared/parametros`: al cambiar N, recalcula el indicador de
    todos los proveedores con recepciones."""
    from sqlalchemy import select as _select

    from proveedores.models import Proveedor

    n = 0
    for pid in db.scalars(_select(Proveedor.id)):
        _recalcular_indicador(db, pid)
        n += 1
    return n


def registrar_consumidores() -> None:
    from shared.parametros import registrar_consumidor

    registrar_consumidor(
        "proveedores_n_recepciones_indicador",
        _recalcular_todos_los_indicadores,
        nombre="proveedores.indicador_plazos",
    )


def generar_programadas_vencidas(db: Session, *, actor: int | None = None) -> int:
    """Crea una orden `borrador` por cada compra programada activa y vencida,
    y avanza `proxima_generacion`. Devuelve cuántas generó."""
    generadas = 0
    for prog in repository.programadas_vencidas(db):
        o = repository.crear_orden(
            db, proveedor_id=prog.proveedor_id, sucursal_destino_id=prog.sucursal_destino_id,
            tipo="programada", compra_programada_id=prog.id, estado="borrador",
            condiciones_pago=None, importe_a_pagar=None, creado_por=actor,
        )
        for l in prog.plantilla_lineas:
            db.add(LineaOrdenCompra(
                orden_compra_id=o.id, item_tipo=l["item_tipo"], item_ref=l["item_ref"],
                descripcion=l.get("descripcion"), observaciones=l.get("observaciones"),
                marca=l.get("marca"), calibre_codigo=l.get("calibre_codigo"), anio=l.get("anio"),
                numero_serie=l.get("numero_serie"), pieza_id=l.get("pieza_id"),
                pieza_tipo=l.get("pieza_tipo"), unidad_medida=l.get("unidad_medida"),
                marca_compatible=l.get("marca_compatible"), cantidad=int(l["cantidad"]),
                costo_unitario=(Decimal(str(l["costo_unitario"])) if l.get("costo_unitario") is not None else None),
                es_perecedero=bool(l.get("es_perecedero")),
            ))
        from sqlalchemy import select as _select

        o_lineas = list(db.scalars(_select(LineaOrdenCompra).where(LineaOrdenCompra.orden_compra_id == o.id)))
        o.importe_a_pagar = _importe(o_lineas)
        prog.proxima_generacion = _avanzar(prog.proxima_generacion, prog.frecuencia)
        db.flush()
        registrar_cambio(db, actor=actor, accion="crear", entidad="orden_compra", entidad_id=o.id,
                         despues={"origen": "compra_programada", "compra_programada_id": prog.id})
        generadas += 1
    return generadas
