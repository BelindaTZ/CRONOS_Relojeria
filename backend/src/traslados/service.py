"""Lógica del módulo `traslados` (feature 004).

Máquina de estados de la transferencia:
  en_preparacion --enviar--> en_transito --recibir--> recibida | parcial
  en_preparacion | en_transito --cancelar--> cancelada

Efecto sobre el inventario (todo en la misma transacción):
- enviar:  relojes → `en_transito` (fuera de disponibilidad en origen);
           piezas → `movimiento_stock_pieza(transferencia_salida)` en origen.
- recibir: relojes → sucursal destino + `evento_serie(transferencia)`;
           piezas → `movimiento_stock_pieza(transferencia_entrada)` en destino.
           Faltante ⇒ `discrepancia_transferencia` (derivable a merma 011).
- cancelar: revierte todo a `disponible` en la sucursal origen.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.models import Sucursal
from traslados import repository
from traslados.models import Transferencia
from traslados.schemas import (
    AccionMerma,
    DiscrepanciaOut,
    ItemDisponibleOut,
    LineaTransferenciaOut,
    RecibirIn,
    TransferenciaIn,
    TransferenciaOut,
)

logger = logging.getLogger("cronos.traslados")

_CANCELABLE = ("en_preparacion", "en_transito")


# =========================================================== salida
def _sucursal_nombre(db: Session, sid: int) -> str:
    s = db.get(Sucursal, sid)
    return s.nombre if s else f"#{sid}"


def _etiqueta_linea(db: Session, l) -> str:
    if l.item_tipo == "reloj":
        from inventario import reloj_para_traslado

        r = reloj_para_traslado(db, l.reloj_id)
        return f"{r['marca']} {r['referencia']} · {r['numero_serie']}" if r else f"reloj #{l.reloj_id}"
    from piezas import datos_pieza

    p = datos_pieza(db, l.pieza_id)
    return f"{p['codigo']} · {p['descripcion']}" if p else f"pieza #{l.pieza_id}"


def _out(db: Session, t: Transferencia) -> TransferenciaOut:
    return TransferenciaOut(
        id=t.id, sucursal_origen_id=t.sucursal_origen_id, sucursal_destino_id=t.sucursal_destino_id,
        estado=t.estado, motivo=t.motivo, motivo_cancelacion=t.motivo_cancelacion,
        fecha_envio=t.fecha_envio, fecha_recepcion=t.fecha_recepcion,
        responsable_envio_id=t.responsable_envio_id, responsable_recepcion_id=t.responsable_recepcion_id,
        creado_en=t.creado_en,
        lineas=[
            LineaTransferenciaOut(
                id=l.id, item_tipo=l.item_tipo, reloj_id=l.reloj_id, pieza_id=l.pieza_id,
                etiqueta=_etiqueta_linea(db, l), cantidad_enviada=l.cantidad_enviada,
                cantidad_recibida=l.cantidad_recibida,
            )
            for l in t.lineas
        ],
        tiene_discrepancias=repository.tiene_discrepancias(db, t.id),
    )


# =========================================================== listar / ítems disponibles
def listar(db, *, user, sucursal_id, estado, numero_serie, offset, limit):
    from inventario import ids_relojes_por_serie, sucursales_visibles

    reloj_ids = ids_relojes_por_serie(db, numero_serie) if numero_serie else None
    filas, total = repository.buscar(
        db, sucursales=sucursales_visibles(user, None), sucursal_id=sucursal_id,
        estado=estado, reloj_ids=reloj_ids, offset=offset, limit=limit,
    )
    return [_out(db, t) for t in filas], total


def sucursales_activas(db: Session) -> list[dict]:
    return [
        {"id": s.id, "nombre": s.nombre}
        for s in db.scalars(select(Sucursal).where(Sucursal.estado == "activa").order_by(Sucursal.nombre))
    ]


def costo_referencial_venta(db: Session) -> dict:
    """Costo sugerido (parámetro `costo_traslado_venta`, feature 004/flujo
    principal) a informar al vendedor cuando un traslado lo pide el cliente
    directamente — el traslado rutinario de reabastecimiento sigue siendo
    gratuito, este cargo aplica solo a la solicitud puntual de un cliente."""
    from shared.parametros import get_parametro

    valor = get_parametro(db, "costo_traslado_venta")
    return {"costo_traslado_venta": valor}


def items_disponibles(db: Session, *, sucursal_id: int, item_tipo: str, q: str | None) -> list[ItemDisponibleOut]:
    if item_tipo == "reloj":
        from inventario import relojes_disponibles_en

        return [
            ItemDisponibleOut(id=r["id"], etiqueta=f"{r['marca']} {r['referencia']}", detalle=r["numero_serie"])
            for r in relojes_disponibles_en(db, sucursal_id, q=q)
        ]
    from piezas import piezas_disponibles_en

    return [
        ItemDisponibleOut(id=p["id"], etiqueta=p["codigo"], detalle=p["descripcion"], stock=p["stock"])
        for p in piezas_disponibles_en(db, sucursal_id, q=q)
    ]


# =========================================================== crear
def crear(db: Session, datos: TransferenciaIn, *, actor: int) -> TransferenciaOut:
    from inventario import reloj_para_traslado
    from piezas import stock_en

    if datos.sucursal_origen_id == datos.sucursal_destino_id:
        raise ValidationError("El origen y el destino deben ser sucursales distintas", field="sucursal_destino_id")

    origen = db.get(Sucursal, datos.sucursal_origen_id)
    destino = db.get(Sucursal, datos.sucursal_destino_id)
    if origen is None or destino is None:
        raise NotFoundError("Sucursal de origen o destino no encontrada")
    if origen.estado != "activa" or destino.estado != "activa":
        raise ValidationError("Ambas sucursales deben estar activas para iniciar una transferencia")
    if len(sucursales_activas(db)) < 2:
        raise ValidationError("Se necesita al menos otra sucursal activa como destino")

    # valida cada ítem: reloj disponible en origen; pieza con stock suficiente en origen
    for ln in datos.lineas:
        if ln.item_tipo == "reloj":
            if not ln.reloj_id:
                raise ValidationError("Falta el reloj de una línea", field="reloj_id")
            r = reloj_para_traslado(db, ln.reloj_id)
            if r is None:
                raise NotFoundError(f"Reloj #{ln.reloj_id} no encontrado")
            if r["sucursal_actual_id"] != datos.sucursal_origen_id:
                raise ValidationError(f"El reloj {r['numero_serie']} no está en la sucursal origen", field="reloj_id")
            if r["disponibilidad"] != "disponible":
                raise ConflictError(f"El reloj {r['numero_serie']} no está disponible ({r['disponibilidad']})")
        else:
            if not ln.pieza_id:
                raise ValidationError("Falta la pieza de una línea", field="pieza_id")
            disp = stock_en(db, ln.pieza_id, datos.sucursal_origen_id)
            if ln.cantidad_enviada > disp:
                raise ConflictError(
                    f"Stock insuficiente de la pieza #{ln.pieza_id} en origen: hay {disp}, pides {ln.cantidad_enviada}"
                )

    t = repository.crear(
        db, sucursal_origen_id=datos.sucursal_origen_id, sucursal_destino_id=datos.sucursal_destino_id,
        estado="en_preparacion", motivo=datos.motivo.strip(), creado_por=actor,
    )
    for ln in datos.lineas:
        repository.agregar_linea(
            db, transferencia_id=t.id, item_tipo=ln.item_tipo, reloj_id=ln.reloj_id,
            pieza_id=ln.pieza_id, cantidad_enviada=1 if ln.item_tipo == "reloj" else ln.cantidad_enviada,
        )
    db.refresh(t)
    registrar_cambio(db, actor=actor, accion="crear", entidad="transferencia", entidad_id=t.id,
                     despues={"origen": t.sucursal_origen_id, "destino": t.sucursal_destino_id, "lineas": len(t.lineas)})

    if datos.enviar_ahora:
        return enviar(db, t.id, responsable_envio_id=actor, actor=actor)
    return _out(db, t)


# =========================================================== enviar
def enviar(db: Session, tid: int, *, responsable_envio_id: int | None, actor: int) -> TransferenciaOut:
    from inventario import marcar_reloj_en_transito
    from piezas import mover_stock_traslado

    t = repository.obtener(db, tid, for_update=True)
    if t is None:
        raise NotFoundError("Transferencia no encontrada")
    if t.estado != "en_preparacion":
        raise ConflictError(f"Solo se envía una transferencia en preparación (estado: {t.estado})")

    for l in t.lineas:
        if l.item_tipo == "reloj":
            marcar_reloj_en_transito(db, l.reloj_id, transferencia_id=t.id, actor=actor)
        else:
            mover_stock_traslado(
                db, pieza_id=l.pieza_id, sucursal_id=t.sucursal_origen_id, tipo="transferencia_salida",
                cantidad=l.cantidad_enviada, transferencia_id=t.id, actor=actor,
            )
    t.estado = "en_transito"
    t.fecha_envio = datetime.now(timezone.utc)
    t.responsable_envio_id = responsable_envio_id or actor
    db.flush()
    registrar_cambio(db, actor=actor, accion="enviar", entidad="transferencia", entidad_id=t.id,
                     antes={"estado": "en_preparacion"}, despues={"estado": "en_transito"})
    return _out(db, t)


# =========================================================== recibir
def recibir(db: Session, tid: int, datos: RecibirIn, *, actor: int) -> TransferenciaOut:
    from inventario import recibir_reloj_transferido
    from piezas import mover_stock_traslado

    t = repository.obtener(db, tid, for_update=True)
    if t is None:
        raise NotFoundError("Transferencia no encontrada")
    if t.estado in ("recibida", "cancelada"):
        raise ConflictError(f"La transferencia ya está '{t.estado}'")
    if t.estado not in ("en_transito", "parcial"):
        raise ConflictError(f"No se puede recibir una transferencia en estado '{t.estado}'")

    recibido = {r.linea_transferencia_id: r.cantidad_recibida for r in datos.lineas}
    origen_nombre = _sucursal_nombre(db, t.sucursal_origen_id)
    destino_nombre = _sucursal_nombre(db, t.sucursal_destino_id)

    completa = True
    for l in t.lineas:
        if l.cantidad_recibida is not None:  # ya procesada en una recepción parcial previa
            continue
        cant = recibido.get(l.id)
        if cant is None:
            completa = False
            continue
        if cant > l.cantidad_enviada:
            raise ValidationError(
                f"No se puede recibir más de lo enviado en la línea #{l.id}", field="cantidad_recibida"
            )
        l.cantidad_recibida = cant

        if l.item_tipo == "reloj":
            if cant >= 1:
                recibir_reloj_transferido(
                    db, l.reloj_id, sucursal_destino_id=t.sucursal_destino_id, transferencia_id=t.id,
                    origen=origen_nombre, destino=destino_nombre, motivo=t.motivo, actor=actor,
                )
            else:
                repository.crear_discrepancia(db, linea_transferencia_id=l.id, cantidad_faltante=1)
                completa = False
        else:
            if cant > 0:
                mover_stock_traslado(
                    db, pieza_id=l.pieza_id, sucursal_id=t.sucursal_destino_id, tipo="transferencia_entrada",
                    cantidad=cant, transferencia_id=t.id, actor=actor,
                )
            faltante = l.cantidad_enviada - cant
            if faltante > 0:
                repository.crear_discrepancia(db, linea_transferencia_id=l.id, cantidad_faltante=faltante)
                completa = False
        db.flush()

    t.estado = "recibida" if completa else "parcial"
    t.fecha_recepcion = datetime.now(timezone.utc)
    t.responsable_recepcion_id = datos.responsable_recepcion_id or actor
    db.flush()
    registrar_cambio(db, actor=actor, accion="recibir", entidad="transferencia", entidad_id=t.id,
                     despues={"estado": t.estado})
    return _out(db, t)


# =========================================================== cancelar
def cancelar(db: Session, tid: int, *, motivo: str, actor: int) -> TransferenciaOut:
    from inventario import revertir_reloj_transferencia
    from piezas import mover_stock_traslado

    t = repository.obtener(db, tid, for_update=True)
    if t is None:
        raise NotFoundError("Transferencia no encontrada")
    if t.estado not in _CANCELABLE:
        raise ConflictError(f"No se puede cancelar una transferencia en estado '{t.estado}'")
    if not motivo or len(motivo.strip()) < 3:
        raise ValidationError("El motivo de cancelación es obligatorio", field="motivo")

    if t.estado == "en_transito":
        for l in t.lineas:
            if l.item_tipo == "reloj":
                revertir_reloj_transferencia(db, l.reloj_id, transferencia_id=t.id, actor=actor)
            else:
                mover_stock_traslado(
                    db, pieza_id=l.pieza_id, sucursal_id=t.sucursal_origen_id, tipo="transferencia_entrada",
                    cantidad=l.cantidad_enviada, transferencia_id=t.id, actor=actor,
                )

    t.estado = "cancelada"
    t.motivo_cancelacion = motivo.strip()
    db.flush()
    registrar_cambio(db, actor=actor, accion="cancelar", entidad="transferencia", entidad_id=t.id,
                     despues={"estado": "cancelada", "motivo": motivo.strip()})
    return _out(db, t)


# =========================================================== discrepancias
def discrepancias(db: Session, tid: int) -> list[DiscrepanciaOut]:
    if repository.obtener(db, tid) is None:
        raise NotFoundError("Transferencia no encontrada")
    salida = []
    for d, l in repository.discrepancias_de(db, tid):
        salida.append(DiscrepanciaOut(
            id=d.id, linea_transferencia_id=l.id, item_tipo=l.item_tipo,
            etiqueta=_etiqueta_linea(db, l), cantidad_faltante=d.cantidad_faltante,
            resuelta=d.resuelta, merma_id=d.merma_id,
            accion_merma=AccionMerma(
                item_tipo=l.item_tipo, reloj_id=l.reloj_id, pieza_id=l.pieza_id,
                cantidad=d.cantidad_faltante, referencia=_etiqueta_linea(db, l),
            ),
        ))
    return salida


def obtener_detalle(db: Session, tid: int, *, user) -> TransferenciaOut:
    t = repository.obtener(db, tid)
    if t is None:
        raise NotFoundError("Transferencia no encontrada")
    return _out(db, t)


def discrepancia_para_merma(db: Session, did: int) -> dict | None:
    """Público (011): payload prellenado de `POST /mermas` para una discrepancia
    de recepción — causa `dano_transito`."""
    fila = repository.discrepancia_por_id(db, did)
    if fila is None:
        return None
    d, l, t = fila
    return {
        "transferencia_id": t.id, "item_tipo": l.item_tipo, "reloj_id": l.reloj_id,
        "pieza_id": l.pieza_id, "cantidad": d.cantidad_faltante, "causa": "dano_transito",
        "sucursal_id": t.sucursal_destino_id,
    }


def vincular_merma(db: Session, did: int, *, merma_id: int) -> None:
    """Público (011): al crearse la merma derivada de una discrepancia, queda
    vinculada y la discrepancia se marca resuelta."""
    fila = repository.discrepancia_por_id(db, did)
    if fila is None:
        return
    d, _l, _t = fila
    d.merma_id = merma_id
    d.resuelta = True
    db.flush()
