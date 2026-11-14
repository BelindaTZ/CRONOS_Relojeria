"""Registro de gastos operativos: pagado ahora vs. por pagar (feature 010, research D11).

- `pagado`: exige `medio_pago`; registra un `movimiento_caja` (si el medio es
  efectivo/caja de la sucursal) y el asiento `gasto_pagado` (debe cuenta de gasto
  según la categoría, haber Caja y Bancos).
- `por_pagar`: exige contraparte (`proveedor_id` **o** `beneficiario_id`); crea la
  `cuenta_por_pagar` (`origen_tipo=gasto`) y el asiento `gasto_por_pagar` (debe
  cuenta de gasto, haber Cuentas por Pagar Gastos).
- Registro y confirmación: **exclusivo de Gerencia General** (FR-018).
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from contabilidad import repository
from contabilidad.schemas import GastoOut
from contabilidad.service import NoAutorizadoError, puede_gestionar_contabilidad
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from shared.storage import get_object_url, put_object

_CENT = Decimal("0.01")
_BUCKET = "documentos"


def _q(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _sucursal_nombre(db: Session, sid: int) -> str | None:
    from shared.models import Sucursal

    s = db.get(Sucursal, sid)
    return s.nombre if s else None


def _contraparte_nombre(db: Session, g) -> str | None:
    if g.proveedor_id:
        from proveedores.public import proveedor_nombre

        return proveedor_nombre(db, g.proveedor_id)
    if g.beneficiario_id:
        b = repository.beneficiario_por_id(db, g.beneficiario_id)
        return b.nombre if b else None
    return None


def _gasto_out(db: Session, g) -> GastoOut:
    from shared.models import CategoriaGasto

    cat = db.get(CategoriaGasto, g.categoria_gasto_id)
    return GastoOut(
        id=g.id, sucursal_id=g.sucursal_id, sucursal_nombre=_sucursal_nombre(db, g.sucursal_id),
        categoria_gasto_id=g.categoria_gasto_id, categoria_nombre=cat.nombre if cat else None,
        categoria_tipo=cat.tipo if cat else None, proveedor_id=g.proveedor_id, beneficiario_id=g.beneficiario_id,
        contraparte_nombre=_contraparte_nombre(db, g), monto=_q(g.monto), fecha=g.fecha,
        descripcion=g.descripcion,
        documento_soporte_url=get_object_url(_BUCKET, g.documento_soporte_objeto) if g.documento_soporte_objeto else None,
        estado_pago=g.estado_pago, estado=g.estado, gasto_recurrente_id=g.gasto_recurrente_id,
        cuenta_por_pagar_id=g.cuenta_por_pagar_id, movimiento_caja_id=g.movimiento_caja_id,
        asiento_id=g.asiento_id, creado_en=g.creado_en,
    )


def _validar_categoria(db: Session, categoria_id: int):
    from shared.models import CategoriaGasto

    cat = db.get(CategoriaGasto, categoria_id)
    if cat is None or not cat.activo:
        raise ValidationError("Categoría de gasto inválida o inactiva", field="categoria_gasto_id")
    return cat


def _aplicar_pago(db: Session, g, *, cat, estado_pago: str, medio_pago: str | None,
                  proveedor_id: int | None, beneficiario_id: int | None, actor: int) -> None:
    """Aplica el efecto del `estado_pago`: movimiento de caja o CxP, y el asiento."""
    from contabilidad import caja as caja_mod
    from contabilidad.asientos_auto import generar
    from contabilidad.schemas import MovimientoCajaIn

    if estado_pago == "pagado":
        if not medio_pago:
            raise ValidationError("Un gasto 'pagado' exige el medio de pago", field="medio_pago")
        from shared.models import MedioPago

        medio = db.query(MedioPago).filter_by(clave=medio_pago.strip()).first()
        if medio is None:
            raise ValidationError(f"Medio de pago desconocido: {medio_pago}", field="medio_pago")
        g.medio_pago_id = medio.id
        try:
            mov = caja_mod.registrar_movimiento(
                db, g.sucursal_id,
                MovimientoCajaIn(tipo="salida", monto=g.monto, medio_pago=medio_pago,
                                 documento_tipo="gasto", documento_id=g.id, nota=g.descripcion),
                user=_ActorPlano(actor),
            )
            g.movimiento_caja_id = mov.id
        except ConflictError:
            pass  # sin sesión de caja abierta: el gasto queda igual confirmado, solo sin movimiento de caja
        asiento = generar(
            db, evento="gasto_pagado", monto=g.monto, glosa=f"Gasto #{g.id} — {cat.nombre}",
            origen="gasto", origen_id=g.id, condicion_ctx={"categoria_tipo": cat.tipo}, actor=actor,
        )
    else:  # por_pagar
        if not (proveedor_id or beneficiario_id):
            raise ValidationError(
                "Un gasto 'por pagar' exige un proveedor o un beneficiario", field="beneficiario_id"
            )
        cxp = repository.crear_cxp(
            db, origen_tipo="gasto", orden_compra_id=None, gasto_id=g.id,
            proveedor_id=proveedor_id, beneficiario_id=beneficiario_id,
            monto_original=_q(g.monto), saldo=_q(g.monto), estado="pendiente",
        )
        g.proveedor_id = proveedor_id
        g.beneficiario_id = beneficiario_id
        g.cuenta_por_pagar_id = cxp.id
        asiento = generar(
            db, evento="gasto_por_pagar", monto=g.monto, glosa=f"Gasto #{g.id} — {cat.nombre}",
            origen="gasto", origen_id=g.id, condicion_ctx={"categoria_tipo": cat.tipo}, actor=actor,
        )
    g.asiento_id = asiento.id if asiento else None
    db.flush()


class _ActorPlano:
    """Adaptador mínimo: `caja.registrar_movimiento` espera un `CurrentUser` completo,
    pero aquí solo tenemos el id del actor (ya autorizado por `gastos.py`)."""

    def __init__(self, uid: int):
        self.id = uid


def registrar_gasto(
    db: Session, datos, *, soporte: bytes | None, soporte_nombre: str | None, user: CurrentUser,
) -> GastoOut:
    if not puede_gestionar_contabilidad(user):
        raise NoAutorizadoError("El registro de gastos requiere Gerencia General o Contador")
    cat = _validar_categoria(db, datos.categoria_gasto_id)

    objeto = None
    if soporte:
        import uuid as _uuid

        objeto = f"gastos/{_uuid.uuid4().hex}-{(soporte_nombre or 'soporte')[:60]}"
        put_object(_BUCKET, objeto, soporte, content_type="application/octet-stream")

    from shared.models import Sucursal

    if db.get(Sucursal, datos.sucursal_id) is None:
        raise ValidationError("Sucursal inexistente", field="sucursal_id")

    g = repository.crear_gasto(
        db, sucursal_id=datos.sucursal_id, categoria_gasto_id=datos.categoria_gasto_id,
        monto=_q(datos.monto), fecha=datos.fecha, descripcion=(datos.descripcion or "").strip() or None,
        documento_soporte_objeto=objeto, estado_pago=datos.estado_pago, estado="confirmado", creado_por=user.id,
    )
    _aplicar_pago(
        db, g, cat=cat, estado_pago=datos.estado_pago, medio_pago=datos.medio_pago,
        proveedor_id=datos.proveedor_id, beneficiario_id=datos.beneficiario_id, actor=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="crear", entidad="gasto", entidad_id=g.id,
                     despues={"sucursal_id": g.sucursal_id, "monto": str(g.monto), "estado_pago": g.estado_pago})
    return _gasto_out(db, g)


def listar_gastos(db, *, user, sucursal_id, categoria_gasto_id, estado_pago, estado, desde, hasta, offset, limit):
    from contabilidad.service import _sucursales

    filas, total = repository.buscar_gastos(
        db, sucursales=_sucursales(user), sucursal_id=sucursal_id, categoria_gasto_id=categoria_gasto_id,
        estado_pago=estado_pago, estado=estado, desde=desde, hasta=hasta, offset=offset, limit=limit,
    )
    return [_gasto_out(db, g) for g in filas], total


def confirmar_gasto(db: Session, gasto_id: int, datos, *, user: CurrentUser) -> GastoOut:
    if not puede_gestionar_contabilidad(user):
        raise NoAutorizadoError("La confirmación de gastos requiere Gerencia General o Contador")
    g = repository.obtener_gasto(db, gasto_id, for_update=True)
    if g is None:
        raise NotFoundError("Gasto no encontrado")
    if g.estado != "borrador":
        raise ConflictError("El gasto ya está confirmado")
    cat = _validar_categoria(db, g.categoria_gasto_id)
    if datos.monto is not None:
        g.monto = _q(datos.monto)
    g.estado = "confirmado"
    db.flush()
    _aplicar_pago(
        db, g, cat=cat, estado_pago=datos.estado_pago, medio_pago=datos.medio_pago,
        proveedor_id=datos.proveedor_id, beneficiario_id=datos.beneficiario_id, actor=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="editar", entidad="gasto", entidad_id=g.id,
                     despues={"estado": "confirmado", "monto": str(g.monto), "estado_pago": datos.estado_pago})
    return _gasto_out(db, g)
