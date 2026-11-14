"""Lógica del módulo `piezas` (feature 003).

- CRUD de piezas/repuestos con calibres compatibles y marca `perecedera`.
- Stock por sucursal materializado; **invariante `stock_actual >= 0`** garantizado
  con `SELECT ... FOR UPDATE` sobre la fila de stock (FR-015, SC-007).
- `movimiento_stock_pieza` es APPEND-ONLY (trigger en DB).
- Perecederos: cada ingreso crea/incrementa un `lote_pieza`; el consumo descuenta
  por **FEFO** (first-expire-first-out); lote vencido advierte y ofrece merma (011).
- Tras cada movimiento se recalculan las alertas de stock (módulo `inventario`).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from piezas import repository
from piezas.models import Pieza
from piezas.schemas import (
    LoteCaducidadOut,
    LoteOut,
    MovimientoIn,
    MovimientoOut,
    PiezaDetalle,
    PiezaIn,
    PiezaOut,
    PiezaPatch,
    StockSucursalOut,
    ValorPiezasOut,
)
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.parametros import get_parametro

logger = logging.getLogger("cronos.piezas")

# signo del movimiento por tipo (para 'ajuste' se respeta el signo recibido)
_SIGNO = {
    "ingreso": 1,
    "transferencia_entrada": 1,
    "consumo_ot": -1,
    "venta_suelta": -1,
    "merma": -1,
    "transferencia_salida": -1,
}
_ROLES_VER_COSTOS = {"Gerencia General", "Gerente de Sucursal", "Contador", "Administrador"}


def puede_ver_costos(user) -> bool:
    return bool(_ROLES_VER_COSTOS & set(getattr(user, "roles", []) or []))


# =========================================================== salida
def _pieza_out(db: Session, p: Pieza, *, ver_costos: bool, stock_total: int | None = None) -> PiezaOut:
    if stock_total is None:
        stock_total = repository.stock_total_por_pieza(db, [p.id]).get(p.id, 0)
    return PiezaOut(
        id=p.id, codigo=p.codigo, descripcion=p.descripcion, tipo=p.tipo, proveedor_id=p.proveedor_id,
        costos_visibles=ver_costos,
        costo_adquisicion=p.costo_adquisicion if ver_costos else None,
        precio_venta_suelta=p.precio_venta_suelta, stock_minimo=p.stock_minimo,
        unidad_medida=p.unidad_medida, marca_compatible=p.marca_compatible,
        perecedera=p.perecedera, activo=p.activo,
        calibres_compatibles=repository.calibres_de(db, p.id),
        stock_total=stock_total, bajo_minimo=stock_total <= p.stock_minimo,
    )


def _sucursales_visibles(user):
    from inventario import sucursales_visibles

    return sucursales_visibles(user, None)


def listar(db, *, user, q, calibre_id, bajo_minimo, offset, limit):
    filas, total, totales = repository.buscar_piezas(
        db, q=q, calibre_id=calibre_id, bajo_minimo=bajo_minimo, solo_activas=False,
        offset=offset, limit=limit, sucursales=_sucursales_visibles(user),
    )
    vc = puede_ver_costos(user)
    return [_pieza_out(db, p, ver_costos=vc, stock_total=totales.get(p.id, 0)) for p in filas], total


def _lote_out(lote) -> LoteOut:
    dias = (lote.fecha_caducidad - date.today()).days
    return LoteOut(
        id=lote.id, sucursal_id=lote.sucursal_id, numero_lote=lote.numero_lote,
        fecha_caducidad=lote.fecha_caducidad, cantidad=lote.cantidad, estado=lote.estado,
        dias_restantes=dias,
    )


def obtener_detalle(db: Session, pid: int, *, user) -> PiezaDetalle:
    p = repository.obtener(db, pid)
    if p is None:
        raise NotFoundError("Pieza no encontrada")
    visibles = _sucursales_visibles(user)
    stock_rows = [
        s for s in repository.stock_por_sucursal(db, pid)
        if visibles is None or s.sucursal_id in visibles
    ]
    total = sum(s.stock_actual for s in stock_rows)
    base = _pieza_out(db, p, ver_costos=puede_ver_costos(user), stock_total=total).model_dump()
    return PiezaDetalle(
        **base,
        stock_por_sucursal=[
            StockSucursalOut(sucursal_id=s.sucursal_id, stock_actual=s.stock_actual,
                             bajo_minimo=s.stock_actual <= p.stock_minimo)
            for s in stock_rows
        ],
        lotes=[_lote_out(l) for l in repository.lotes_de(db, pid, solo_con_saldo=True)] if p.perecedera else [],
    )


# =========================================================== CRUD
def crear(db: Session, datos: PiezaIn, *, actor: int) -> PiezaOut:
    if repository.por_codigo(db, datos.codigo):
        raise ConflictError("Ya existe una pieza con ese código", field="codigo")
    _validar_calibres(db, datos.calibres_compatibles)
    p = repository.crear(
        db, codigo=datos.codigo, descripcion=datos.descripcion, tipo=datos.tipo,
        proveedor_id=datos.proveedor_id, costo_adquisicion=datos.costo_adquisicion,
        precio_venta_suelta=datos.precio_venta_suelta, stock_minimo=datos.stock_minimo,
        unidad_medida=datos.unidad_medida, marca_compatible=datos.marca_compatible,
        perecedera=datos.perecedera,
    )
    if datos.calibres_compatibles:
        repository.set_calibres(db, p.id, datos.calibres_compatibles)
    registrar_cambio(db, actor=actor, accion="crear", entidad="pieza", entidad_id=p.id,
                     despues=datos.model_dump(exclude_none=True))
    return _pieza_out(db, p, ver_costos=True, stock_total=0)


def actualizar(db: Session, pid: int, datos: PiezaPatch, *, actor: int) -> PiezaOut:
    p = repository.obtener(db, pid)
    if p is None:
        raise NotFoundError("Pieza no encontrada")
    cambios = datos.model_dump(exclude_unset=True)
    antes = _pieza_out(db, p, ver_costos=True).model_dump()
    if "calibres_compatibles" in cambios and cambios["calibres_compatibles"] is not None:
        _validar_calibres(db, cambios["calibres_compatibles"])
        repository.set_calibres(db, pid, cambios.pop("calibres_compatibles"))
    for campo in ("descripcion", "tipo", "proveedor_id", "costo_adquisicion",
                  "precio_venta_suelta", "stock_minimo", "unidad_medida", "marca_compatible",
                  "perecedera", "activo"):
        if campo in cambios:
            setattr(p, campo, cambios[campo])
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="pieza", entidad_id=pid,
                     antes=antes, despues=_pieza_out(db, p, ver_costos=True).model_dump())
    return _pieza_out(db, p, ver_costos=True)


def inactivar(db: Session, pid: int, *, actor: int) -> PiezaOut:
    p = repository.obtener(db, pid)
    if p is None:
        raise NotFoundError("Pieza no encontrada")
    p.activo = False
    db.flush()
    registrar_cambio(db, actor=actor, accion="inactivar", entidad="pieza", entidad_id=pid)
    return _pieza_out(db, p, ver_costos=True)


def _validar_calibres(db: Session, ids: list[int]) -> None:
    if not ids:
        return
    from inventario import calibres_por_ids

    existentes = calibres_por_ids(db, ids)
    faltan = [i for i in ids if i not in existentes]
    if faltan:
        raise ValidationError(f"Calibres inexistentes: {faltan}", field="calibres_compatibles")


# =========================================================== movimientos / stock
class StockInsuficienteError(ConflictError):
    code = "stock_insuficiente"


def _recalcular_estado_lotes(db: Session, pieza_id: int, sucursal_id: int) -> tuple[int, int]:
    """Actualiza `estado` de los lotes de la pieza y devuelve (vencidos, por_vencer)."""
    umbral = int(get_parametro(db, "umbral_caducidad_dias", default=30) or 30)
    hoy = date.today()
    vencidos = por_vencer = 0
    for lote in repository.lotes_de(db, pieza_id):
        dias = (lote.fecha_caducidad - hoy).days
        if lote.cantidad <= 0:
            lote.estado = "vencido" if dias < 0 else "vigente"
            continue
        if dias < 0:
            lote.estado = "vencido"
            vencidos += 1
        elif dias <= umbral:
            lote.estado = "proximo_vencer"
            por_vencer += 1
        else:
            lote.estado = "vigente"
    db.flush()
    return vencidos, por_vencer


def aplicar_movimiento(
    db: Session,
    *,
    pieza: Pieza,
    sucursal_id: int,
    tipo: str,
    delta: int,
    lote_id: int | None = None,
    documento_tipo: str | None = None,
    documento_id: int | None = None,
    nota: str | None = None,
    actor: int | None = None,
) -> int:
    """Aplica un movimiento con bloqueo de fila. Devuelve el `stock_actual` resultante.
    Aborta (StockInsuficiente) si el resultado sería negativo — el stock NUNCA queda < 0."""
    row = repository.stock_row(db, pieza_id=pieza.id, sucursal_id=sucursal_id, for_update=True)
    if row is None:
        row = repository.crear_stock_row(db, pieza_id=pieza.id, sucursal_id=sucursal_id)
        row = repository.stock_row(db, pieza_id=pieza.id, sucursal_id=sucursal_id, for_update=True)

    nuevo = row.stock_actual + delta
    if nuevo < 0:
        raise StockInsuficienteError(
            f"Stock insuficiente: hay {row.stock_actual} y el movimiento retiraría {-delta}",
            field="cantidad",
        )
    row.stock_actual = nuevo
    db.flush()

    repository.registrar_movimiento(
        db, pieza_id=pieza.id, sucursal_id=sucursal_id, tipo=tipo, cantidad=delta,
        lote_id=lote_id, documento_tipo=documento_tipo, documento_id=documento_id,
        nota=nota, creado_por=actor,
    )
    return nuevo


def registrar_movimiento(db: Session, pid: int, datos: MovimientoIn, *, actor: int) -> MovimientoOut:
    p = repository.obtener(db, pid)
    if p is None:
        raise NotFoundError("Pieza no encontrada")

    if datos.tipo == "ajuste":
        delta = int(datos.cantidad)
        if delta == 0:
            raise ValidationError("El ajuste no puede ser cero", field="cantidad")
    else:
        magnitud = abs(int(datos.cantidad))
        if magnitud == 0:
            raise ValidationError("La cantidad debe ser mayor que cero", field="cantidad")
        delta = magnitud * _SIGNO[datos.tipo]

    lote_id: int | None = None
    aviso_vencido = False

    if p.perecedera and datos.tipo == "ingreso":
        if not datos.lote or not datos.fecha_caducidad:
            raise ValidationError(
                "La pieza es perecedera: lote y fecha de caducidad son obligatorios en un ingreso",
                field="lote",
            )
        lote = repository.lote_por_numero(
            db, pieza_id=pid, sucursal_id=datos.sucursal_id, numero=datos.lote
        )
        if lote is None:
            lote = repository.crear_lote(
                db, pieza_id=pid, sucursal_id=datos.sucursal_id, numero=datos.lote,
                caducidad=datos.fecha_caducidad, cantidad=abs(delta),
            )
        else:
            lote.cantidad += abs(delta)
            db.flush()
        lote_id = lote.id

    resultado = aplicar_movimiento(
        db, pieza=p, sucursal_id=datos.sucursal_id, tipo=datos.tipo, delta=delta,
        lote_id=lote_id, documento_tipo=datos.documento_tipo, documento_id=datos.documento_id,
        nota=datos.nota, actor=actor,
    )

    # FEFO: para perecederas, un consumo descuenta de los lotes que vencen antes.
    if p.perecedera and delta < 0:
        aviso_vencido = _descontar_fefo(db, pieza_id=pid, sucursal_id=datos.sucursal_id, cantidad=-delta)

    vencidos, por_vencer = _recalcular_estado_lotes(db, pid, datos.sucursal_id)
    _sincronizar_alertas(db, p, datos.sucursal_id, resultado, vencidos, por_vencer)

    registrar_cambio(db, actor=actor, accion="crear", entidad="movimiento_stock_pieza", entidad_id=pid,
                     despues={"tipo": datos.tipo, "delta": delta, "stock_resultante": resultado})

    mv = MovimientoOut(
        id=0, pieza_id=pid, sucursal_id=datos.sucursal_id, tipo=datos.tipo, cantidad=delta,
        lote_id=lote_id, documento_tipo=datos.documento_tipo, documento_id=datos.documento_id,
        nota=datos.nota, creado_por=actor, creado_en=datetime.now(timezone.utc),
    )
    if aviso_vencido:
        mv.nota = (mv.nota or "") + " · ⚠ se consumió stock de un lote vencido: considera darlo de baja por merma (011)."
    return mv


def _descontar_fefo(db: Session, *, pieza_id: int, sucursal_id: int, cantidad: int) -> bool:
    """Descuenta `cantidad` de los lotes por caducidad ascendente. Devuelve True si
    tocó algún lote ya vencido."""
    restante = cantidad
    toco_vencido = False
    for lote in repository.lotes_fefo(db, pieza_id=pieza_id, sucursal_id=sucursal_id):
        if restante <= 0:
            break
        quita = min(lote.cantidad, restante)
        if (lote.fecha_caducidad - date.today()).days < 0 and quita > 0:
            toco_vencido = True
        lote.cantidad -= quita
        restante -= quita
    db.flush()
    return toco_vencido


def _sincronizar_alertas(db, p: Pieza, sucursal_id: int, stock_actual: int, vencidos: int, por_vencer: int) -> None:
    from inventario import recalcular_alertas_pieza

    recalcular_alertas_pieza(
        db, pieza_id=p.id, pieza_codigo=p.codigo, sucursal_id=sucursal_id,
        stock_actual=stock_actual, stock_minimo=p.stock_minimo,
        lotes_vencidos=vencidos, lotes_por_vencer=por_vencer,
    )


# =========================================================== traslados (004)
def stock_en(db: Session, pieza_id: int, sucursal_id: int) -> int:
    """Público (004): stock actual de una pieza en una sucursal."""
    row = repository.stock_row(db, pieza_id=pieza_id, sucursal_id=sucursal_id)
    return row.stock_actual if row else 0


def datos_pieza(db: Session, pieza_id: int) -> dict | None:
    """Público: datos de una pieza para consumir desde otro módulo (002 al armar la OC)."""
    p = repository.obtener(db, pieza_id)
    if p is None:
        return None
    return {
        "id": p.id, "codigo": p.codigo, "descripcion": p.descripcion, "tipo": p.tipo,
        "unidad_medida": p.unidad_medida, "marca_compatible": p.marca_compatible,
        "perecedera": p.perecedera,
    }


def buscar_o_crear_por_codigo(
    db: Session, *, codigo: str, descripcion: str | None = None, tipo: str = "original",
    unidad_medida: str = "unidad", marca_compatible: str | None = None, perecedera: bool = False,
    proveedor_id: int | None = None, costo: float | None = None,
) -> int:
    """Público (002 → recepción): devuelve el id de la pieza con ese código, creándola si no existe."""
    p = repository.por_codigo(db, codigo)
    if p is None:
        from decimal import Decimal as _D

        p = repository.crear(
            db, codigo=codigo, descripcion=(descripcion or codigo), tipo=tipo,
            unidad_medida=unidad_medida or "unidad", marca_compatible=marca_compatible,
            perecedera=perecedera, proveedor_id=proveedor_id,
            costo_adquisicion=_D(str(costo)) if costo else None,
        )
    return p.id


def piezas_disponibles_en(db: Session, sucursal_id: int, *, q: str | None = None, limit: int = 50) -> list[dict]:
    """Público (004): piezas con stock > 0 en una sucursal, para armar una transferencia."""
    filas, _, totales = repository.buscar_piezas(
        db, q=q, calibre_id=None, bajo_minimo=False, solo_activas=True, offset=0, limit=limit,
    )
    salida = []
    for p in filas:
        s = stock_en(db, p.id, sucursal_id)
        if s > 0:
            salida.append({"id": p.id, "codigo": p.codigo, "descripcion": p.descripcion, "stock": s})
    return salida


def consumir_en_ot(
    db: Session, *, pieza_id: int, sucursal_id: int, cantidad: int,
    orden_trabajo_id: int, actor: int | None = None,
) -> Decimal:
    """Público (008): descuenta `cantidad` de una pieza por una orden de trabajo
    (FEFO para perecederas; nunca stock negativo) y devuelve el costo total
    (`costo_adquisicion × cantidad`, 0 si no hay costo cargado)."""
    p = repository.obtener(db, pieza_id)
    if p is None:
        raise NotFoundError("Pieza no encontrada")
    cantidad = abs(int(cantidad))
    if cantidad == 0:
        raise ValidationError("La cantidad debe ser mayor que cero", field="cantidad")
    resultado = aplicar_movimiento(
        db, pieza=p, sucursal_id=sucursal_id, tipo="consumo_ot", delta=-cantidad,
        documento_tipo="orden_trabajo", documento_id=orden_trabajo_id, actor=actor,
    )
    if p.perecedera:
        _descontar_fefo(db, pieza_id=pieza_id, sucursal_id=sucursal_id, cantidad=cantidad)
    vencidos, por_vencer = _recalcular_estado_lotes(db, pieza_id, sucursal_id)
    _sincronizar_alertas(db, p, sucursal_id, resultado, vencidos, por_vencer)
    unidad = Decimal(str(p.costo_adquisicion)) if p.costo_adquisicion is not None else Decimal("0")
    return (unidad * cantidad).quantize(Decimal("0.01"))


def costo_pieza(db: Session, pieza_id: int) -> Decimal:
    """Público (008): costo de adquisición unitario de una pieza (0 si no consta)."""
    p = repository.obtener(db, pieza_id)
    if p is None or p.costo_adquisicion is None:
        return Decimal("0")
    return Decimal(str(p.costo_adquisicion))


def datos_pieza_venta(db: Session, pieza_id: int) -> dict | None:
    """Público (009): datos de una pieza para una línea de venta suelta."""
    p = repository.obtener(db, pieza_id)
    if p is None:
        return None
    return {
        "id": p.id, "codigo": p.codigo, "descripcion": p.descripcion, "tipo": p.tipo,
        "precio_venta_suelta": p.precio_venta_suelta, "activo": p.activo,
        "_costo": p.costo_adquisicion,
    }


def vender_pieza(
    db: Session, *, pieza_id: int, sucursal_id: int, cantidad: int,
    orden_venta_id: int, actor: int | None = None,
) -> Decimal:
    """Público (009): descuenta `cantidad` de una pieza por una venta suelta (FEFO para
    perecederas; nunca negativo) y devuelve el costo total (`costo_adquisicion × cantidad`)."""
    p = repository.obtener(db, pieza_id)
    if p is None:
        raise NotFoundError("Pieza no encontrada")
    cantidad = abs(int(cantidad))
    if cantidad == 0:
        raise ValidationError("La cantidad debe ser mayor que cero", field="cantidad")
    resultado = aplicar_movimiento(
        db, pieza=p, sucursal_id=sucursal_id, tipo="venta_suelta", delta=-cantidad,
        documento_tipo="orden_venta", documento_id=orden_venta_id, actor=actor,
    )
    if p.perecedera:
        _descontar_fefo(db, pieza_id=pieza_id, sucursal_id=sucursal_id, cantidad=cantidad)
    vencidos, por_vencer = _recalcular_estado_lotes(db, pieza_id, sucursal_id)
    _sincronizar_alertas(db, p, sucursal_id, resultado, vencidos, por_vencer)
    unidad = Decimal(str(p.costo_adquisicion)) if p.costo_adquisicion is not None else Decimal("0")
    return (unidad * cantidad).quantize(Decimal("0.01"))


def revertir_venta_pieza(
    db: Session, *, pieza_id: int, sucursal_id: int, cantidad: int,
    orden_venta_id: int, actor: int | None = None,
) -> None:
    """Público (009): al anular una venta — reingresa la pieza como ajuste positivo."""
    p = repository.obtener(db, pieza_id)
    if p is None:
        return
    aplicar_movimiento(
        db, pieza=p, sucursal_id=sucursal_id, tipo="ajuste", delta=abs(int(cantidad)),
        documento_tipo="orden_venta", documento_id=orden_venta_id,
        nota="reingreso por anulación de venta", actor=actor,
    )
    resultado = stock_en(db, pieza_id, sucursal_id)
    vencidos, por_vencer = _recalcular_estado_lotes(db, pieza_id, sucursal_id)
    _sincronizar_alertas(db, p, sucursal_id, resultado, vencidos, por_vencer)


def dar_baja_pieza(
    db: Session, *, pieza_id: int, sucursal_id: int, cantidad: int,
    documento_id: int, actor: int | None = None,
) -> Decimal:
    """Público (011): descuenta `cantidad` de una pieza por una merma (FEFO para
    perecederas; nunca stock negativo — FR-019) y devuelve el costo total."""
    p = repository.obtener(db, pieza_id)
    if p is None:
        raise NotFoundError("Pieza no encontrada")
    cantidad = abs(int(cantidad))
    if cantidad == 0:
        raise ValidationError("La cantidad debe ser mayor que cero", field="cantidad")
    resultado = aplicar_movimiento(
        db, pieza=p, sucursal_id=sucursal_id, tipo="merma", delta=-cantidad,
        documento_tipo="merma", documento_id=documento_id, actor=actor,
    )
    if p.perecedera:
        _descontar_fefo(db, pieza_id=pieza_id, sucursal_id=sucursal_id, cantidad=cantidad)
    vencidos, por_vencer = _recalcular_estado_lotes(db, pieza_id, sucursal_id)
    _sincronizar_alertas(db, p, sucursal_id, resultado, vencidos, por_vencer)
    unidad = Decimal(str(p.costo_adquisicion)) if p.costo_adquisicion is not None else Decimal("0")
    return unidad * cantidad


def reingresar_pieza(
    db: Session, *, pieza_id: int, sucursal_id: int, cantidad: int,
    documento_id: int, actor: int | None = None,
) -> None:
    """Público (011): "reparado y reingresado a stock" — reingresa la pieza
    como ajuste positivo."""
    p = repository.obtener(db, pieza_id)
    if p is None:
        return
    aplicar_movimiento(
        db, pieza=p, sucursal_id=sucursal_id, tipo="ajuste", delta=abs(int(cantidad)),
        documento_tipo="merma", documento_id=documento_id,
        nota="reingreso por merma reparada", actor=actor,
    )
    resultado = stock_en(db, pieza_id, sucursal_id)
    vencidos, por_vencer = _recalcular_estado_lotes(db, pieza_id, sucursal_id)
    _sincronizar_alertas(db, p, sucursal_id, resultado, vencidos, por_vencer)


def mover_stock_traslado(
    db: Session, *, pieza_id: int, sucursal_id: int, tipo: str, cantidad: int,
    transferencia_id: int, actor: int,
) -> int:
    """Público (004): mueve stock de una pieza por una transferencia.
    `tipo` ∈ {transferencia_salida, transferencia_entrada}. Devuelve el stock resultante."""
    p = repository.obtener(db, pieza_id)
    if p is None:
        raise NotFoundError("Pieza no encontrada")
    delta = -abs(cantidad) if tipo == "transferencia_salida" else abs(cantidad)
    resultado = aplicar_movimiento(
        db, pieza=p, sucursal_id=sucursal_id, tipo=tipo, delta=delta,
        documento_tipo="transferencia", documento_id=transferencia_id, actor=actor,
    )
    if tipo == "transferencia_salida" and p.perecedera and delta < 0:
        _descontar_fefo(db, pieza_id=pieza_id, sucursal_id=sucursal_id, cantidad=-delta)
    vencidos, por_vencer = _recalcular_estado_lotes(db, pieza_id, sucursal_id)
    _sincronizar_alertas(db, p, sucursal_id, resultado, vencidos, por_vencer)
    return resultado


def movimientos(db: Session, pid: int, *, offset: int, limit: int):
    if repository.obtener(db, pid) is None:
        raise NotFoundError("Pieza no encontrada")
    filas, total = repository.movimientos_de(db, pid, offset=offset, limit=limit)
    return [
        MovimientoOut(
            id=m.id, pieza_id=m.pieza_id, sucursal_id=m.sucursal_id, tipo=m.tipo, cantidad=m.cantidad,
            lote_id=m.lote_id, documento_tipo=m.documento_tipo, documento_id=m.documento_id,
            nota=m.nota, creado_por=m.creado_por, creado_en=m.creado_en,
        )
        for m in filas
    ], total


def lotes(db: Session, pid: int) -> list[LoteOut]:
    if repository.obtener(db, pid) is None:
        raise NotFoundError("Pieza no encontrada")
    _recalcular_estado_lotes_todas_sucursales(db, pid)
    return [_lote_out(l) for l in repository.lotes_de(db, pid)]


def _recalcular_estado_lotes_todas_sucursales(db: Session, pid: int) -> None:
    sucs = {l.sucursal_id for l in repository.lotes_de(db, pid)}
    for s in sucs:
        _recalcular_estado_lotes(db, pid, s)


def listar_lotes_caducidad(
    db: Session, *, user, estado: str | None, sucursal_id: int | None
) -> list[LoteCaducidadOut]:
    visibles = _sucursales_visibles(user)
    salida = []
    for lote, pieza in repository.todos_los_lotes(db, estado=estado, sucursal_id=sucursal_id):
        if visibles is not None and lote.sucursal_id not in visibles:
            continue
        base = _lote_out(lote)
        salida.append(LoteCaducidadOut(
            **base.model_dump(), pieza_id=pieza.id, pieza_codigo=pieza.codigo,
            pieza_descripcion=pieza.descripcion,
        ))
    return salida


def valor_piezas(db: Session, *, user) -> ValorPiezasOut:
    refs, a_precio, a_costo = repository.valor_piezas(db, sucursales=_sucursales_visibles(user))
    return ValorPiezasOut(
        referencias=refs, a_precio_venta=Decimal(str(a_precio)),
        a_costo=Decimal(str(a_costo)) if puede_ver_costos(user) else None,
    )


# =========================================================== recepción de compra (002 → 003)
def recibir_de_compra(db: Session, orden, propagacion: list[tuple]) -> None:
    """Receptor registrado en `proveedores`: al recibir una OC, las líneas de pieza
    suben stock (y lote si son perecederas). Las de reloj se fichan aparte (necesitan
    número de serie), quedan como 'pendientes de fichar' en Inventario."""
    sucursal_id = getattr(orden, "sucursal_destino_id", None)
    if sucursal_id is None:
        return
    for linea, cantidad, lote_num, caducidad in propagacion:
        if getattr(linea, "item_tipo", None) != "pieza" or cantidad <= 0:
            continue
        # pieza del catálogo, o crear con los datos de la línea (código, tipo, unidad, marca compatible)
        p = repository.obtener(db, linea.pieza_id) if getattr(linea, "pieza_id", None) else None
        if p is None:
            codigo = linea.item_ref
            p = repository.por_codigo(db, codigo)
        if p is None:
            tipo = getattr(linea, "pieza_tipo", None) or "original"
            p = repository.crear(
                db, codigo=linea.item_ref, descripcion=linea.descripcion or linea.item_ref,
                tipo=tipo if tipo in ("original", "no_original_equivalente") else "original",
                unidad_medida=getattr(linea, "unidad_medida", None) or "unidad",
                marca_compatible=getattr(linea, "marca_compatible", None),
                proveedor_id=getattr(orden, "proveedor_id", None),
                costo_adquisicion=Decimal(str(linea.costo_unitario or 0)),
                perecedera=bool(getattr(linea, "es_perecedero", False)),
            )
        lote_id = None
        if p.perecedera and lote_num and caducidad:
            lote = repository.lote_por_numero(db, pieza_id=p.id, sucursal_id=sucursal_id, numero=lote_num)
            if lote is None:
                lote = repository.crear_lote(
                    db, pieza_id=p.id, sucursal_id=sucursal_id, numero=lote_num,
                    caducidad=caducidad, cantidad=cantidad,
                )
            else:
                lote.cantidad += cantidad
                db.flush()
            lote_id = lote.id
        resultado = aplicar_movimiento(
            db, pieza=p, sucursal_id=sucursal_id, tipo="ingreso", delta=cantidad,
            lote_id=lote_id, documento_tipo="recepcion_compra",
            documento_id=getattr(orden, "id", None),
        )
        vencidos, por_vencer = _recalcular_estado_lotes(db, p.id, sucursal_id)
        _sincronizar_alertas(db, p, sucursal_id, resultado, vencidos, por_vencer)
