"""Lógica del módulo `ventas` (feature 009).

Orden de venta de relojes (por número de serie) y piezas sueltas (Principio II):
`borrador → confirmada → anulada`.

- `confirmar` es **atómico**: baja de stock (relojes → `vendido` + `evento_serie(venta)`;
  piezas → `movimiento_stock_pieza(venta_suelta)`), garantías (fábrica/tienda),
  pagos multimedios (`shared/pagos`), CxC por el saldo, PDF (comprobante +
  certificado) a `comprobantes-venta`, recálculo de nivel del cliente (006),
  vínculo con la cita (007).
- Descuentos/cupones vía `shared/descuentos` (006) con **margen mínimo protegido**.
- **Margen y costo**: solo roles administrativos; nunca en los comprobantes.
- **Consumidor final**: solo para venta de piezas sueltas cuyo total sea menor que
  `monto_max_consumidor_final`. Venta de reloj o total alto ⇒ cliente identificado.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from shared.parametros import get_parametro
from ventas import margen as margen_mod
from ventas import repository
from ventas.models import OrdenVenta
from ventas.schemas import (
    CuentaPorCobrarOut,
    DescuentoAplicadoOut,
    GarantiaVentaOut,
    LineaVentaOut,
    PagoRegistradoOut,
    PagoVentaOut,
    VentaDetalle,
    VentaOut,
    VentasDiaOut,
)

logger = logging.getLogger("cronos.ventas")

_ROLES_VER_COSTOS = {"Gerencia General", "Gerente de Sucursal", "Contador", "Administrador"}
_CENT = Decimal("0.01")


class NoAutorizadoError(ConflictError):
    status_code = 403
    code = "no_autorizado"


def puede_ver_costos(user: CurrentUser) -> bool:
    return bool(_ROLES_VER_COSTOS & set(getattr(user, "roles", []) or []))


def _sucursales(user: CurrentUser) -> list[int] | None:
    from inventario import sucursales_visibles

    return sucursales_visibles(user, None)


def _q(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(_CENT)


def _iva_pct(db: Session) -> Decimal:
    try:
        return Decimal(str(get_parametro(db, "iva_porcentaje", default=0.15)))
    except Exception:  # noqa: BLE001
        return Decimal("0.15")


def _sucursal_para_venta(db: Session, user: CurrentUser, sucursal_id: int | None) -> int:
    """La venta se registra en la sucursal del **vendedor** (§4.9 / FR-014). Si el
    usuario tiene una sola sucursal, se usa esa; si tiene varias, elige entre las
    suyas; Gerencia General (sin sucursal) debe indicar cuál (override explícito)."""
    from shared.models import Sucursal

    propias = list(getattr(user, "sucursal_ids", []) or [])
    if len(propias) == 1:
        elegida = propias[0]
    elif propias:
        if sucursal_id is None:
            raise ValidationError("Indica en cuál de tus sucursales se registra la venta", field="sucursal_id")
        if sucursal_id not in propias:
            raise NoAutorizadoError("Solo puedes registrar ventas en tus sucursales asignadas")
        elegida = sucursal_id
    else:  # Gerencia General u otro rol sin sucursal asignada
        if sucursal_id is None:
            raise ValidationError(
                "No tienes una sucursal asignada: indica en cuál se registra la venta", field="sucursal_id"
            )
        elegida = sucursal_id
    suc = db.get(Sucursal, elegida)
    if suc is None or suc.estado != "activa":
        raise ValidationError("Sucursal inválida o inactiva", field="sucursal_id")
    return elegida


# ============================================================ salida
def _cliente(db: Session, cid: int) -> dict:
    from clientes import cliente_mini

    return cliente_mini(db, cid) or {}


def _sucursal_nombre(db: Session, sid: int) -> str | None:
    from shared.models import Sucursal

    s = db.get(Sucursal, sid)
    return s.nombre if s else f"#{sid}"


def _saldo(db: Session, v: OrdenVenta) -> tuple[Decimal, Decimal]:
    from shared.pagos import pagado, saldo

    pg = pagado(db, documento_tipo="venta", documento_id=v.id)
    sd = saldo(db, documento_tipo="venta", documento_id=v.id, total=v.total)
    return pg, sd


def _vendedor_nombre(db: Session, uid: int | None) -> str | None:
    if uid is None:
        return None
    from shared.models import Usuario

    u = db.get(Usuario, uid)
    return u.nombre if u else None


def _venta_out(db: Session, v: OrdenVenta, *, user: CurrentUser, lineas: list | None = None) -> VentaOut:
    cli = _cliente(db, v.cliente_id)
    vc = puede_ver_costos(user)
    pg, sd = _saldo(db, v)

    # El desglose de IVA/descuento solo queda GRABADO al confirmar (es el valor
    # fiscal histórico de la factura). Mientras la venta está en borrador esas
    # columnas son NULL — pero el vendedor necesita verlas para decidir antes de
    # confirmar (feedback del usuario 2026-09-11: "no veo el desglose del IVA").
    # Se calculan en vivo con las líneas actuales, sin persistir nada.
    if v.estado == "borrador":
        from ventas import impuestos as imp

        iva_porcentaje = _iva_pct(db)
        ln = lineas if lineas is not None else repository.lineas_de(db, v.id)
        d = imp.desglosar_venta(ln, iva_pct=iva_porcentaje) if ln else None
        subtotal_sin_impuestos = d.subtotal_sin_impuestos if d else None
        total_descuento = d.total_descuento if d else None
        iva_monto = d.iva_monto if d else None
    else:
        iva_porcentaje = Decimal(str(v.iva_porcentaje)) if v.iva_porcentaje is not None else None
        subtotal_sin_impuestos = _q(v.subtotal_sin_impuestos) if v.subtotal_sin_impuestos is not None else None
        total_descuento = _q(v.total_descuento) if v.total_descuento is not None else None
        iva_monto = _q(v.iva_monto) if v.iva_monto is not None else None

    return VentaOut(
        id=v.id, numero=v.numero, numero_factura=v.numero_factura,
        cliente_id=v.cliente_id, cliente_nombre=cli.get("nombre"),
        cliente_afiliado=cli.get("numero_afiliado"), cliente_email=cli.get("email"),
        sucursal_id=v.sucursal_id, sucursal_nombre=_sucursal_nombre(db, v.sucursal_id),
        vendedor_usuario_id=v.vendedor_usuario_id, vendedor_nombre=_vendedor_nombre(db, v.vendedor_usuario_id),
        cita_id=v.cita_id, estado=v.estado, fecha=v.fecha,
        subtotal=_q(v.subtotal), total=_q(v.total),
        subtotal_sin_impuestos=subtotal_sin_impuestos,
        total_descuento=total_descuento,
        iva_porcentaje=iva_porcentaje,
        iva_monto=iva_monto,
        pagado=pg, saldo=sd,
        descuento_aplicado=v.descuento_aplicado, identificacion_fiscal=v.identificacion_fiscal,
        margen_venta=_q(v.margen_venta) if (vc and v.margen_venta is not None) else None,
        costos_visibles=vc, creado_en=v.creado_en,
    )


def _linea_out(db: Session, ln, *, ver_costos: bool) -> LineaVentaOut:
    desc = numero_serie = None
    if ln.item_tipo == "reloj":
        from inventario import reloj_para_venta

        r = reloj_para_venta(db, ln.reloj_id) or {}
        desc = f"{r.get('marca', '')} {r.get('referencia', '')}".strip() or "Reloj"
        numero_serie = r.get("numero_serie")
    else:
        from piezas import datos_pieza_venta

        p = datos_pieza_venta(db, ln.pieza_id) or {}
        desc = f"{p.get('codigo', '')} · {p.get('descripcion', '')}".strip(" ·") or "Pieza"
    return LineaVentaOut(
        id=ln.id, item_tipo=ln.item_tipo, reloj_id=ln.reloj_id, pieza_id=ln.pieza_id,
        descripcion=desc, numero_serie=numero_serie, cantidad=ln.cantidad,
        precio_lista=_q(ln.precio_lista), precio_final=_q(ln.precio_final),
        descuento_monto=_q(ln.descuento_monto) if ln.descuento_monto is not None else None,
        base_imponible=_q(ln.base_imponible) if ln.base_imponible is not None else None,
        iva_monto=_q(ln.iva_monto) if ln.iva_monto is not None else None,
        tarifa_iva=Decimal(str(ln.tarifa_iva)) if ln.tarifa_iva is not None else None,
        costo=_q(ln.costo) if ver_costos else None,
        margen=_q(ln.margen) if ver_costos else None,
    )


def _detalle(db: Session, v: OrdenVenta, *, user: CurrentUser) -> VentaDetalle:
    from shared.pagos import pagos_de

    vc = puede_ver_costos(user)
    lineas = repository.lineas_de(db, v.id)
    base = _venta_out(db, v, user=user, lineas=lineas).model_dump()
    pagos = [
        PagoVentaOut(pago_id=p.id, medio_pago=p.medio_pago_nombre, monto=_q(p.monto), referencia=p.referencia)
        for p in pagos_de(db, documento_tipo="venta", documento_id=v.id)
    ]
    comprobantes = [
        {"tipo": c.tipo, "objeto": c.objeto, "numero_serie": c.numero_serie_vinculado,
         "generado_en": c.generado_en.isoformat()}
        for c in repository.comprobantes_de(db, v.id)
    ]
    return VentaDetalle(
        **base,
        lineas=[_linea_out(db, ln, ver_costos=vc) for ln in lineas],
        garantias=[
            GarantiaVentaOut(tipo=g.tipo, periodo_dias=g.periodo_dias, fecha_inicio=g.fecha_inicio,
                             fecha_fin=g.fecha_fin, cobertura=g.cobertura)
            for g in repository.garantias_de(db, v.id)
        ],
        pagos=pagos, comprobantes=comprobantes,
    )


def _get(db: Session, vid: int, *, for_update: bool = False) -> OrdenVenta:
    v = repository.obtener(db, vid, for_update=for_update)
    if v is None:
        raise NotFoundError("Venta no encontrada")
    return v


# ============================================================ crear
def crear_venta(db: Session, datos, *, user: CurrentUser) -> VentaDetalle:
    sucursal_id = _sucursal_para_venta(db, user, datos.sucursal_id)
    iva = _iva_pct(db)
    hay_reloj = any(ln.item_tipo == "reloj" for ln in datos.lineas)

    # armar líneas (precios provisionales; el descuento se aplica aparte)
    lineas_calc = []
    for ln in datos.lineas:
        if ln.item_tipo == "reloj":
            if not ln.reloj_id:
                raise ValidationError("Falta reloj_id en una línea de reloj", field="lineas")
            from inventario import reloj_para_venta

            r = reloj_para_venta(db, ln.reloj_id, ver_costos=True)
            if r is None:
                raise ValidationError(f"Unidad inexistente: {ln.reloj_id}", field="lineas")
            precio = _q(ln.precio_lista if ln.precio_lista is not None else r.get("precio_venta"))
            if precio <= 0:
                raise ValidationError(
                    f"La unidad {r['numero_serie']} no tiene precio de venta; indícalo en la línea", field="lineas"
                )
            costo = _q(r.get("_costo"))
            lineas_calc.append(dict(item_tipo="reloj", reloj_id=ln.reloj_id, pieza_id=None,
                                    cantidad=1, precio_lista=precio, costo=costo))
        else:
            if not ln.pieza_id:
                raise ValidationError("Falta pieza_id en una línea de pieza", field="lineas")
            from piezas import datos_pieza_venta

            p = datos_pieza_venta(db, ln.pieza_id)
            if p is None or not p.get("activo", True):
                raise ValidationError(f"Pieza inexistente o inactiva: {ln.pieza_id}", field="lineas")
            precio_u = _q(ln.precio_lista if ln.precio_lista is not None else p.get("precio_venta_suelta"))
            if precio_u <= 0:
                raise ValidationError("La pieza no tiene precio de venta suelta; indícalo", field="lineas")
            precio = _q(precio_u * ln.cantidad)
            costo = _q(_q(p.get("_costo")) * ln.cantidad)
            lineas_calc.append(dict(item_tipo="pieza", reloj_id=None, pieza_id=ln.pieza_id,
                                    cantidad=ln.cantidad, precio_lista=precio, costo=costo))

    subtotal = _q(sum((c["precio_lista"] for c in lineas_calc), Decimal("0")))

    # cliente identificado vs. consumidor final (D8)
    from clientes import cliente_mini, id_consumidor_final

    monto_max = _q(get_parametro(db, "monto_max_consumidor_final", default=500))
    cliente_id = datos.cliente_id
    if cliente_id is None:
        if hay_reloj or subtotal >= monto_max:
            raise ValidationError(
                "Una venta de reloj (o de monto alto) exige una ficha de cliente identificado.",
                field="cliente_id",
            )
        cliente_id = id_consumidor_final(db)
        if cliente_id is None:
            raise ValidationError("No hay cliente «consumidor final» configurado", field="cliente_id")
    else:
        cli = cliente_mini(db, cliente_id)
        if cli is None:
            raise ValidationError("Cliente inexistente", field="cliente_id")
        if cli.get("es_consumidor_final") and (hay_reloj or subtotal >= monto_max):
            raise ValidationError(
                "El «consumidor final» no puede comprar relojes ni montos altos.", field="cliente_id"
            )

    v = repository.crear(
        db, numero=repository.siguiente_numero(db), cliente_id=cliente_id, sucursal_id=sucursal_id,
        vendedor_usuario_id=user.id, cita_id=datos.cita_id, estado="borrador",
        identificacion_fiscal=(datos.identificacion_fiscal or "").strip() or None,
        subtotal=subtotal, total=subtotal, iva_porcentaje=iva, creado_por=user.id,
    )
    for c in lineas_calc:
        repository.agregar_linea(
            db, orden_venta_id=v.id, **c,
            precio_final=c["precio_lista"], tarifa_iva=iva * 100,
            margen=margen_mod.margen_linea(precio_final=c["precio_lista"], costo=c["costo"], iva_pct=iva),
        )
    v.margen_venta = margen_mod.margen_venta(repository.lineas_de(db, v.id), iva_pct=iva)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="crear", entidad="orden_venta", entidad_id=v.id,
                     despues={"numero": v.numero, "cliente_id": cliente_id, "total": str(subtotal)})
    return _detalle(db, v, user=user)


# ============================================================ descuento
def aplicar_descuento(db: Session, vid: int, datos, *, user: CurrentUser) -> DescuentoAplicadoOut:
    v = _get(db, vid, for_update=True)
    if v.estado != "borrador":
        raise ConflictError("Solo se aplica descuento a una venta en borrador")
    if datos.descuento_id and datos.cupon_codigo:
        raise ValidationError("Un descuento y un cupón no se aplican juntos", field="cupon_codigo")

    from clientes import cupon_datos, descuento_por_id
    from shared.descuentos import BeneficioAplicable, aplicar as _aplicar

    beneficio = None
    es_cupon = False
    if datos.descuento_id:
        d = descuento_por_id(db, datos.descuento_id)
        if d is None:
            raise ValidationError("Descuento inexistente o inactivo", field="descuento_id")
        beneficio = BeneficioAplicable(tipo=d["tipo"], valor=d["valor"])
    elif datos.cupon_codigo:
        cp = cupon_datos(db, datos.cupon_codigo)
        if cp is None:
            raise ValidationError("Cupón inexistente", field="cupon_codigo")
        if cp["cliente_id"] != v.cliente_id:
            raise ValidationError("El cupón no pertenece a este cliente", field="cupon_codigo")
        beneficio = BeneficioAplicable(tipo=cp["tipo"], valor=cp["valor"])
        es_cupon = True
    else:
        raise ValidationError("Indica un descuento o un cupón", field="descuento_id")

    iva = _iva_pct(db)
    lineas = repository.lineas_de(db, vid)
    costo_total = _q(sum((_q(ln.costo) for ln in lineas), Decimal("0")))
    marca = None
    relojes = [ln for ln in lineas if ln.item_tipo == "reloj"]
    if len(relojes) == 1:
        from inventario import reloj_para_venta

        marca = (reloj_para_venta(db, relojes[0].reloj_id) or {}).get("marca")

    r = _aplicar(
        db, item_ref=f"venta:{v.numero}", costo=costo_total, precio_lista=_q(v.subtotal),
        marca=marca, descuento=None if es_cupon else beneficio, cupon=beneficio if es_cupon else None,
    )
    if r.decision == "bloquear":
        raise ConflictError("El descuento deja el margen por debajo del mínimo protegido (política: bloquear)")

    # prorratear el descuento entre líneas por peso de precio_lista
    total_final = r.precio_final
    repartido = Decimal("0")
    for i, ln in enumerate(lineas):
        if i == len(lineas) - 1:
            pf = _q(total_final - repartido)
        elif _q(v.subtotal) > 0:
            pf = _q(total_final * _q(ln.precio_lista) / _q(v.subtotal))
        else:
            pf = _q(ln.precio_lista)
        repartido += pf
        ln.precio_final = pf
        ln.margen = margen_mod.margen_linea(precio_final=pf, costo=ln.costo, iva_pct=iva)

    v.total = total_final
    v.margen_venta = margen_mod.margen_venta(lineas, iva_pct=iva)
    v.descuento_aplicado = {
        "tipo": beneficio.tipo, "valor": float(beneficio.valor), "es_cupon": es_cupon,
        "cupon_codigo": datos.cupon_codigo, "descuento_id": datos.descuento_id,
        "monto_descontado": float(r.monto_descontado), "decision": r.decision,
    }
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="orden_venta", entidad_id=vid,
                     despues={"descuento": v.descuento_aplicado})
    return DescuentoAplicadoOut(
        precio_final=r.precio_final, monto_descontado=r.monto_descontado,
        margen_resultante=r.margen_resultante, decision=r.decision,
    )


# ============================================================ pagos
def registrar_pago_venta(db: Session, vid: int, datos, *, user: CurrentUser) -> PagoRegistradoOut:
    v = _get(db, vid, for_update=True)
    if v.estado == "anulada":
        raise ConflictError("La venta está anulada")

    from shared.models import MedioPago
    from shared.pagos import registrar_pago, saldo

    medio = db.scalars(select(MedioPago).where(MedioPago.clave == datos.medio_pago.strip())).first()
    if medio is None:
        raise ValidationError(f"Medio de pago desconocido: {datos.medio_pago}", field="medio_pago")
    p = registrar_pago(
        db, documento_tipo="venta", documento_id=vid, medio_pago_id=medio.id,
        monto=datos.monto, referencia=datos.referencia, actor=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="crear", entidad="pago", entidad_id=p.id,
                     despues={"documento": f"venta#{vid}", "monto": str(datos.monto), "medio": medio.clave})
    return PagoRegistradoOut(
        pago_id=p.id, medio_pago=medio.nombre, monto=_q(datos.monto),
        saldo=saldo(db, documento_tipo="venta", documento_id=vid, total=v.total),
    )


# ============================================================ confirmar
def _garantia_fabrica_dias(db: Session, marca: str | None) -> int:
    if marca:
        v = get_parametro(db, "garantia_fabrica_dias_default", ambito_tipo="marca",
                          ambito_ref=marca, default=None, fallback_global=False)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return int(get_parametro(db, "garantia_fabrica_dias_default", default=730) or 730)


def _garantia_tienda_dias(db: Session) -> int:
    return int(get_parametro(db, "garantia_tienda_dias_default", default=180) or 180)


def confirmar_venta(db: Session, vid: int, datos, *, user: CurrentUser) -> VentaDetalle:
    v = _get(db, vid, for_update=True)
    if v.estado != "borrador":
        raise ConflictError(f"No se confirma una venta en estado '{v.estado}'")
    lineas = repository.lineas_de(db, vid)
    if not lineas:
        raise ValidationError("La venta no tiene líneas", field="lineas")

    # margen mínimo: si el descuento exige autorización, hace falta el id
    da = v.descuento_aplicado or {}
    if da.get("decision") == "requiere_autorizacion" and not datos.autorizacion_margen_minimo_id:
        raise NoAutorizadoError(
            "El descuento deja el margen bajo el mínimo protegido: requiere autorización de Gerencia General"
        )
    if datos.autorizacion_margen_minimo_id:
        from clientes import autorizacion_por_id

        if autorizacion_por_id(db, datos.autorizacion_margen_minimo_id) is None:
            raise ValidationError("Autorización de margen inexistente", field="autorizacion_margen_minimo_id")
        v.autorizacion_margen_minimo_id = datos.autorizacion_margen_minimo_id

    from inventario import marcar_reloj_vendido
    from piezas import vender_pieza

    # baja de stock (atómica: si una falla, revienta la transacción entera)
    for ln in lineas:
        if ln.item_tipo == "reloj":
            marcar_reloj_vendido(db, ln.reloj_id, documento_id=vid, actor=user.id)
        else:
            vender_pieza(db, pieza_id=ln.pieza_id, sucursal_id=v.sucursal_id,
                         cantidad=ln.cantidad, orden_venta_id=vid, actor=user.id)

    # garantías por línea de reloj
    hoy = date.today()
    for ln in lineas:
        if ln.item_tipo != "reloj":
            continue
        from inventario import reloj_para_venta

        marca = (reloj_para_venta(db, ln.reloj_id) or {}).get("marca")
        d_fab = _garantia_fabrica_dias(db, marca)
        d_tie = _garantia_tienda_dias(db)
        repository.agregar_garantia(
            db, orden_venta_id=vid, linea_venta_id=ln.id, tipo="fabrica", periodo_dias=d_fab,
            fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=d_fab),
            cobertura=f"Garantía de fábrica {marca or ''}".strip(),
        )
        repository.agregar_garantia(
            db, orden_venta_id=vid, linea_venta_id=ln.id, tipo="tienda", periodo_dias=d_tie,
            fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=d_tie),
            cobertura="Garantía de tienda: mano de obra del servicio propio",
        )

    # desglose de IVA (los precios son PVP; back-out para la factura)
    from ventas import impuestos as imp

    iva = _iva_pct(db)
    d = imp.desglosar_venta(lineas, iva_pct=iva)
    for ln, dl in zip(lineas, d.lineas):
        ln.descuento_monto = dl.descuento_monto
        ln.base_imponible = dl.base_imponible
        ln.iva_monto = dl.iva_monto
        ln.tarifa_iva = dl.tarifa_iva
    v.iva_porcentaje = iva
    v.subtotal_sin_impuestos = d.subtotal_sin_impuestos
    v.total_descuento = d.total_descuento
    v.iva_monto = d.iva_monto

    # numeración tipo SRI: EEE-PPP-NNNNNNNNN (secuencial propio del punto de emisión)
    v.numero_factura = _asignar_numero_factura(db, v.sucursal_id)

    # CxC por el saldo
    from shared.pagos import saldo

    sd = saldo(db, documento_tipo="venta", documento_id=vid, total=v.total)
    if sd > 0:
        repository.crear_cxc(
            db, origen_tipo="venta", origen_id=vid, cliente_id=v.cliente_id,
            monto_original=v.total, saldo=sd, estado="pendiente",
        )

    v.estado = "confirmada"
    v.fecha = datetime.now(timezone.utc)
    v.actualizado_en = datetime.now(timezone.utc)
    db.flush()

    # cupón (consumo con lock), nivel de fidelización, cita, PDFs
    if da.get("es_cupon") and da.get("cupon_codigo"):
        try:
            from clientes import consumir_cupon

            consumir_cupon(db, codigo=da["cupon_codigo"], documento_tipo="venta", documento_id=vid, actor=user.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("no se consumió el cupón de la venta %s: %s", vid, exc)

    cli = _cliente(db, v.cliente_id)
    if not cli.get("es_consumidor_final"):
        try:
            from clientes import recalcular_nivel

            recalcular_nivel(db, cliente_id=v.cliente_id, hecho="venta_confirmada", documento_id=vid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("no se recalculó el nivel del cliente (venta %s): %s", vid, exc)
    if v.cita_id:
        try:
            from citas import vincular_transaccion

            vincular_transaccion(db, v.cita_id, venta_id=vid, actor=user.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("no se vinculó la cita %s a la venta %s: %s", v.cita_id, vid, exc)

    _generar_documentos(db, v, lineas)

    try:
        from contabilidad import generar_asiento

        generar_asiento(db, evento="venta_confirmada", monto=v.total, glosa=f"Venta {v.numero}",
                       origen="venta", origen_id=vid, actor=user.id)
        pagado = _q(v.total) - sd
        if pagado > 0:
            generar_asiento(db, evento="cobro_cxc", monto=pagado, glosa=f"Cobro al confirmar venta {v.numero}",
                           origen="venta", origen_id=vid, actor=user.id)
    except Exception as exc:  # noqa: BLE001  (010 podría no estar disponible en algún entorno)
        logger.warning("no se generó el asiento contable de la venta %s: %s", vid, exc)

    registrar_cambio(db, actor=user.id, accion="confirmar", entidad="orden_venta", entidad_id=vid,
                     despues={"total": str(v.total), "saldo": str(sd)})
    return _detalle(db, v, user=user)


def _asignar_numero_factura(db: Session, sucursal_id: int) -> str:
    pe = repository.punto_emision(db, sucursal_id, for_update=True)
    if pe is None:
        pe = repository.crear_punto_emision(db, sucursal_id=sucursal_id)
        pe = repository.punto_emision(db, sucursal_id, for_update=True)
    pe.secuencial_actual = int(pe.secuencial_actual or 0) + 1
    db.flush()
    return f"{pe.establecimiento_codigo}-{pe.punto_emision_codigo}-{pe.secuencial_actual:09d}"


def _factura_ctx(db: Session, v: OrdenVenta, lineas) -> dict:
    """Contexto completo de la factura (§7): emisor, cliente, detalle con back-out de
    IVA, totales reglamentarios, formas de pago, garantías, N.º de serie."""
    from shared.pagos import pagos_de

    cfg = repository.config_facturacion(db)
    pe = repository.punto_emision(db, v.sucursal_id)
    suc = _sucursal_nombre(db, v.sucursal_id)
    cli = _cliente(db, v.cliente_id)
    ident = v.identificacion_fiscal or cli.get("identificacion")
    tipo_ident = "Consumidor Final" if cli.get("es_consumidor_final") else ("RUC" if ident and len(str(ident)) == 13 else "Cédula")

    det = []
    for ln in lineas:
        base = _linea_out(db, ln, ver_costos=False)
        factor = Decimal("1") + (Decimal(str(ln.tarifa_iva or 0)) / 100)
        p_unit_base = _q(_q(ln.precio_lista) / factor) if factor else _q(ln.precio_lista)
        det.append({
            "codigo": (base.numero_serie or (f"P{ln.pieza_id}" if ln.pieza_id else str(ln.id))),
            "descripcion": base.descripcion + (f"  ·  N/S {base.numero_serie}" if base.numero_serie else ""),
            "cantidad": ln.cantidad,
            "precio_unitario": p_unit_base,
            "descuento": _q(ln.descuento_monto or 0),
            "precio_total": _q(ln.base_imponible or 0),
            "tarifa_iva": Decimal(str(ln.tarifa_iva or 0)),
        })

    from ventas import impuestos as imp

    d = imp.desglosar_venta(lineas, iva_pct=Decimal(str(v.iva_porcentaje or 0.15)))
    formas_pago = [
        {"forma": p.medio_pago_nombre or "—", "valor": _q(p.monto)}
        for p in pagos_de(db, documento_tipo="venta", documento_id=v.id)
    ]
    pagado_total = _q(sum((f["valor"] for f in formas_pago), Decimal("0")))
    garantias = [
        {"tipo": g.tipo, "cobertura": g.cobertura, "periodo_dias": g.periodo_dias, "fecha_fin": g.fecha_fin}
        for g in repository.garantias_de(db, v.id)
    ]
    return {
        "emisor": {
            "razon_social": cfg.razon_social, "nombre_comercial": cfg.nombre_comercial,
            "ruc": cfg.ruc, "direccion_matriz": cfg.direccion_matriz,
            "direccion_establecimiento": (pe.direccion_establecimiento if pe else None) or cfg.direccion_matriz,
            "obligado_contabilidad": "SÍ" if cfg.obligado_contabilidad else "NO",
            "contribuyente_especial": cfg.contribuyente_especial or "NO",
            "regimen": cfg.regimen, "leyenda_pie": cfg.leyenda_pie,
        },
        "numero_factura": v.numero_factura or v.numero,
        "fecha": v.fecha, "sucursal": suc, "vendedor": _vendedor_nombre(db, v.vendedor_usuario_id),
        "cliente": {
            "nombre": cli.get("nombre"), "identificacion": ident or "9999999999999",
            "tipo_identificacion": tipo_ident, "direccion": cli.get("direccion"),
            "telefono": cli.get("telefono"), "email": cli.get("email"),
        },
        "detalle": det,
        "totales": {
            "subtotal_15": d.subtotal_15, "subtotal_0": d.subtotal_0,
            "subtotal_no_objeto": Decimal("0"),
            "subtotal_sin_impuestos": d.subtotal_sin_impuestos,
            "total_descuento": d.total_descuento,
            "iva_porcentaje": (Decimal(str(v.iva_porcentaje or 0.15)) * 100).quantize(Decimal("0.01")),
            "iva_monto": d.iva_monto, "propina": Decimal("0"), "valor_total": _q(v.total),
        },
        "formas_pago": formas_pago,
        "pagado": pagado_total, "saldo": _q(_q(v.total) - pagado_total),
        "garantias": garantias,
        "es_consumidor_final": bool(cli.get("es_consumidor_final")),
    }


def _generar_documentos(db: Session, v: OrdenVenta, lineas) -> None:
    ctx = _factura_ctx(db, v, lineas)
    try:
        from shared.pdf import factura_venta, guardar_comprobante

        obj = guardar_comprobante(f"ventas/{v.numero}-factura.pdf", factura_venta(ctx))
        repository.agregar_comprobante(db, orden_venta_id=v.id, tipo="comprobante", objeto=obj)
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se generó la factura de la venta %s: %s", v.id, exc)

    cli = _cliente(db, v.cliente_id)
    for ln in lineas:
        if ln.item_tipo != "reloj":
            continue
        from inventario import reloj_para_venta

        r = reloj_para_venta(db, ln.reloj_id) or {}
        gs = [
            {"tipo": g.tipo, "cobertura": g.cobertura, "periodo_dias": g.periodo_dias, "fecha_fin": g.fecha_fin}
            for g in repository.garantias_de(db, v.id) if g.linea_venta_id == ln.id
        ]
        cctx = {
            "numero": v.numero_factura or v.numero, "fecha": v.fecha, "cliente_nombre": cli.get("nombre"),
            "reloj_marca": r.get("marca"), "reloj_referencia": r.get("referencia"),
            "reloj_serie": r.get("numero_serie"), "garantias": gs,
        }
        try:
            from shared.pdf import certificado_garantia_autenticidad, guardar_comprobante

            obj = guardar_comprobante(
                f"ventas/{v.numero}-cert-{r.get('numero_serie', ln.id)}.pdf",
                certificado_garantia_autenticidad(cctx),
            )
            repository.agregar_comprobante(
                db, orden_venta_id=v.id, tipo="certificado_garantia_autenticidad",
                objeto=obj, numero_serie_vinculado=r.get("numero_serie"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("no se generó el certificado de la venta %s / línea %s: %s", v.id, ln.id, exc)


# ============================================================ anular
def anular_venta(db: Session, vid: int, datos, *, user: CurrentUser) -> VentaOut:
    v = _get(db, vid, for_update=True)
    if v.estado != "confirmada":
        raise ConflictError("Solo se anula una venta confirmada")
    lineas = repository.lineas_de(db, vid)

    from servicio_tecnico import tiene_ot_activa_para_reloj

    for ln in lineas:
        if ln.item_tipo == "reloj" and tiene_ot_activa_para_reloj(db, ln.reloj_id):
            raise ConflictError(
                "La unidad tiene una orden de trabajo abierta; resuélvela antes de anular la venta"
            )

    from inventario import revertir_reloj_venta
    from piezas import revertir_venta_pieza

    for ln in lineas:
        if ln.item_tipo == "reloj":
            revertir_reloj_venta(db, ln.reloj_id, documento_id=vid, actor=user.id)
        else:
            revertir_venta_pieza(db, pieza_id=ln.pieza_id, sucursal_id=v.sucursal_id,
                                 cantidad=ln.cantidad, orden_venta_id=vid, actor=user.id)

    cxc = repository.cxc_de_origen(db, origen_tipo="venta", origen_id=vid)
    if cxc is not None:
        cxc.estado = "anulada"
        cxc.saldo = Decimal("0")

    v.estado = "anulada"
    v.actualizado_en = datetime.now(timezone.utc)
    db.flush()

    cli = _cliente(db, v.cliente_id)
    if not cli.get("es_consumidor_final"):
        try:
            from clientes import recalcular_nivel

            recalcular_nivel(db, cliente_id=v.cliente_id, hecho="venta_anulada", documento_id=vid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("no se recalculó el nivel tras anular la venta %s: %s", vid, exc)

    try:
        from contabilidad import generar_asiento_reversa

        generar_asiento_reversa(db, evento="venta_confirmada", monto=v.total,
                                glosa=f"Anulación de venta {v.numero}: {datos.motivo.strip()}",
                                origen="ajuste", origen_id=vid, actor=user.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se generó el asiento de reversa de la venta %s: %s", vid, exc)

    repository.agregar_anulacion(
        db, orden_venta_id=vid, motivo=datos.motivo.strip(), actor_usuario_id=user.id,
        reversas={"stock": True, "margen": True, "nivel": True, "cxc": cxc is not None},
    )
    registrar_cambio(db, actor=user.id, accion="anular", entidad="orden_venta", entidad_id=vid,
                     despues={"motivo": datos.motivo.strip()})
    return _venta_out(db, v, user=user)


# ============================================================ consultas
def listar(db, *, user, q, estado, cliente_id, sucursal_id, desde, hasta, offset, limit):
    cliente_ids = None
    if q and q.strip():
        from clientes import ids_por_texto

        cliente_ids = ids_por_texto(db, q)
    filas, total = repository.buscar(
        db, sucursales=_sucursales(user), estado=estado, cliente_id=cliente_id,
        cliente_ids=cliente_ids, sucursal_id=sucursal_id, desde=desde, hasta=hasta,
        offset=offset, limit=limit,
    )
    return [_venta_out(db, v, user=user) for v in filas], total


def obtener_detalle(db: Session, vid: int, *, user: CurrentUser) -> VentaDetalle:
    return _detalle(db, _get(db, vid), user=user)


def garantias(db: Session, vid: int) -> list[GarantiaVentaOut]:
    _get(db, vid)
    return [
        GarantiaVentaOut(tipo=g.tipo, periodo_dias=g.periodo_dias, fecha_inicio=g.fecha_inicio,
                         fecha_fin=g.fecha_fin, cobertura=g.cobertura)
        for g in repository.garantias_de(db, vid)
    ]


def comprobantes_urls(db: Session, vid: int, *, user: CurrentUser) -> list[dict]:
    _get(db, vid)
    from shared.storage import get_object_url

    salida = []
    for c in repository.comprobantes_de(db, vid):
        salida.append({
            "tipo": c.tipo, "numero_serie": c.numero_serie_vinculado,
            "url": get_object_url("comprobantes-venta", c.objeto),
        })
    return salida


def cuentas_por_cobrar(db: Session, *, cliente_id: int | None, estado: str | None) -> list[CuentaPorCobrarOut]:
    salida = []
    for c in repository.listar_cxc(db, cliente_id=cliente_id, estado=estado):
        cli = _cliente(db, c.cliente_id)
        salida.append(CuentaPorCobrarOut(
            id=c.id, origen_tipo=c.origen_tipo, origen_id=c.origen_id, cliente_id=c.cliente_id,
            cliente_nombre=cli.get("nombre"), monto_original=_q(c.monto_original), saldo=_q(c.saldo),
            estado=c.estado, creado_en=c.creado_en,
        ))
    return salida


def ventas_dia(db: Session, *, user: CurrentUser, fecha: date | None, sucursal_id: int | None) -> VentasDiaOut:
    dia = fecha or date.today()
    filas = repository.ventas_confirmadas_del_dia(
        db, sucursales=_sucursales(user), sucursal_id=sucursal_id, dia=dia,
    )
    total = _q(sum((_q(v.total) for v in filas), Decimal("0")))
    margen = None
    if puede_ver_costos(user):
        margen = _q(sum((_q(v.margen_venta) for v in filas), Decimal("0")))
    return VentasDiaOut(fecha=dia, ventas=len(filas), total=total, margen=margen)


# ============================================================ factura por correo
def enviar_factura_correo(db: Session, vid: int, *, user: CurrentUser):
    """Acción manual del personal: envía la factura de una venta confirmada al correo
    del cliente (plantilla del design-system, Ppio XI). No es una notificación
    automatizada (eso es 014); es un envío puntual iniciado en el sistema."""
    from ventas.schemas import EnviarFacturaOut

    v = _get(db, vid)
    if v.estado != "confirmada":
        raise ConflictError("Solo se envía la factura de una venta confirmada")
    cli = _cliente(db, v.cliente_id)
    email = (cli.get("email") or "").strip()
    if not email:
        return EnviarFacturaOut(enviado=False, email=None, detalle="El cliente no tiene correo registrado")

    ctx = _factura_ctx(db, v, repository.lineas_de(db, vid))
    adjunto = None
    try:
        from shared.storage import get_object_url

        for c in repository.comprobantes_de(db, vid):
            if c.tipo == "comprobante":
                adjunto = get_object_url("comprobantes-venta", c.objeto)
                break
    except Exception:  # noqa: BLE001  (MinIO no disponible → se envía sin enlace)
        adjunto = None
    try:
        from shared.correo import enviar

        enviar("factura_venta", email, {
            "cliente_nombre": cli.get("nombre"),
            "numero_factura": ctx["numero_factura"],
            "total": str(ctx["totales"]["valor_total"]),
            "url_factura": adjunto,
        })
        registrar_cambio(db, actor=user.id, accion="enviar_factura", entidad="orden_venta", entidad_id=vid,
                         despues={"email": email, "numero_factura": ctx["numero_factura"]})
        return EnviarFacturaOut(enviado=True, email=email, detalle="Factura enviada")
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se pudo enviar la factura de la venta %s: %s", vid, exc)
        return EnviarFacturaOut(enviado=False, email=email, detalle=f"Error al enviar: {exc}")


# ============================================================ config facturación
def get_config_facturacion(db: Session):
    from ventas.schemas import ConfigFacturacionOut

    c = repository.config_facturacion(db)
    return ConfigFacturacionOut(
        razon_social=c.razon_social, nombre_comercial=c.nombre_comercial, ruc=c.ruc,
        direccion_matriz=c.direccion_matriz, obligado_contabilidad=c.obligado_contabilidad,
        contribuyente_especial=c.contribuyente_especial, regimen=c.regimen,
        leyenda_pie=c.leyenda_pie, actualizado_en=c.actualizado_en,
    )


def set_config_facturacion(db: Session, datos, *, actor: int):
    c = repository.config_facturacion(db)
    for campo in ("razon_social", "nombre_comercial", "ruc", "direccion_matriz",
                  "obligado_contabilidad", "contribuyente_especial", "regimen", "leyenda_pie"):
        setattr(c, campo, getattr(datos, campo))
    c.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="config_facturacion", entidad_id=1,
                     despues={"ruc": c.ruc, "razon_social": c.razon_social})
    return get_config_facturacion(db)


def listar_puntos_emision(db: Session):
    from ventas.schemas import PuntoEmisionOut

    return [
        PuntoEmisionOut(
            sucursal_id=p.sucursal_id, sucursal_nombre=_sucursal_nombre(db, p.sucursal_id),
            establecimiento_codigo=p.establecimiento_codigo, punto_emision_codigo=p.punto_emision_codigo,
            direccion_establecimiento=p.direccion_establecimiento, secuencial_actual=p.secuencial_actual,
        )
        for p in repository.puntos_emision(db)
    ]


def set_punto_emision(db: Session, sucursal_id: int, datos, *, actor: int):
    from ventas.schemas import PuntoEmisionOut
    from shared.models import Sucursal

    if db.get(Sucursal, sucursal_id) is None:
        raise ValidationError("Sucursal inexistente", field="sucursal_id")
    p = repository.punto_emision(db, sucursal_id)
    if p is None:
        p = repository.crear_punto_emision(db, sucursal_id=sucursal_id)
    p.establecimiento_codigo = datos.establecimiento_codigo.strip().zfill(3)
    p.punto_emision_codigo = datos.punto_emision_codigo.strip().zfill(3)
    p.direccion_establecimiento = (datos.direccion_establecimiento or "").strip() or None
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="punto_emision", entidad_id=p.id,
                     despues={"sucursal_id": sucursal_id, "codigo": f"{p.establecimiento_codigo}-{p.punto_emision_codigo}"})
    return PuntoEmisionOut(
        sucursal_id=p.sucursal_id, sucursal_nombre=_sucursal_nombre(db, sucursal_id),
        establecimiento_codigo=p.establecimiento_codigo, punto_emision_codigo=p.punto_emision_codigo,
        direccion_establecimiento=p.direccion_establecimiento, secuencial_actual=p.secuencial_actual,
    )


# ============================================================ proveedor a 006
def _proveedor_transacciones(db: Session, cliente_id: int):
    from clientes import TransaccionCliente

    salida = []
    for v in repository.ventas_confirmadas_de_cliente(db, cliente_id):
        salida.append(TransaccionCliente(
            cliente_id=cliente_id, fecha=v.fecha.date(), monto=_q(v.total), tipo="venta",
            documento_id=v.id, detalle=f"Venta {v.numero}", sucursal_id=v.sucursal_id,
        ))
    return salida


# ============================================================ consumidores 001
_consumidores_registrados = False
_proveedores_registrados = False


def _recalcular_por_parametro(db: Session, clave: str) -> int:
    """`margen_minimo` cambió → re-evalúa las ventas en borrador con descuento."""
    n = 0
    for v in repository.ventas_borrador(db):
        if v.descuento_aplicado:
            n += 1
    logger.info("recálculo de margen mínimo en ventas borrador (%s): %d con descuento", clave, n)
    return n


def registrar_consumidores() -> None:
    global _consumidores_registrados
    if _consumidores_registrados:
        return
    from shared.parametros import registrar_consumidor

    registrar_consumidor("margen_minimo", _recalcular_por_parametro, nombre="ventas.recalculo_margen")
    _consumidores_registrados = True


def registrar_proveedores() -> None:
    global _proveedores_registrados
    if _proveedores_registrados:
        return
    from clientes import registrar_proveedor_transacciones

    registrar_proveedor_transacciones(_proveedor_transacciones)
    _proveedores_registrados = True
