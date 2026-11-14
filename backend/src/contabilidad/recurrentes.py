"""Gastos recurrentes (feature 010, research D12): agua/wifi/arriendo/teléfono se
repiten cada periodo. Un scheduler in-proceso (mismo patrón que `compra_programada`
de 002 — sin Airflow) genera, al llegar `proxima_generacion`, un `gasto` en
`borrador` con el monto estimado; Gerencia General lo confirma (ajustando monto y
`estado_pago`) desde `gastos.confirmar_gasto`.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from contabilidad import repository
from contabilidad.schemas import GastoRecurrenteOut
from contabilidad.service import NoAutorizadoError, puede_gestionar_contabilidad
from shared.auditoria import registrar_cambio
from shared.exceptions import NotFoundError, ValidationError
from shared.guard import CurrentUser

_MESES = {"mensual": 1, "bimestral": 2, "trimestral": 3}


def _sumar_meses(d: date, meses: int) -> date:
    mes_total = d.month - 1 + meses
    anio = d.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(d.day, 28)  # evita desbordes de fin de mes; suficiente para "próxima generación"
    return date(anio, mes, dia)


def _out(db: Session, g) -> GastoRecurrenteOut:
    from shared.models import Sucursal, CategoriaGasto

    cat = db.get(CategoriaGasto, g.categoria_gasto_id)
    suc = db.get(Sucursal, g.sucursal_id)
    nombre = None
    if g.proveedor_id:
        from proveedores.public import proveedor_nombre

        nombre = proveedor_nombre(db, g.proveedor_id)
    elif g.beneficiario_id:
        b = repository.beneficiario_por_id(db, g.beneficiario_id)
        nombre = b.nombre if b else None
    return GastoRecurrenteOut(
        id=g.id, categoria_gasto_id=g.categoria_gasto_id, categoria_nombre=cat.nombre if cat else None,
        sucursal_id=g.sucursal_id, sucursal_nombre=suc.nombre if suc else None,
        proveedor_id=g.proveedor_id, beneficiario_id=g.beneficiario_id, contraparte_nombre=nombre,
        descripcion=g.descripcion, monto_estimado=g.monto_estimado, frecuencia=g.frecuencia,
        proxima_generacion=g.proxima_generacion, estado=g.estado,
    )


def listar(db: Session) -> list[GastoRecurrenteOut]:
    return [_out(db, g) for g in repository.listar_gastos_recurrentes(db)]


def crear(db: Session, datos, *, user: CurrentUser) -> GastoRecurrenteOut:
    if not puede_gestionar_contabilidad(user):
        raise NoAutorizadoError("Los gastos recurrentes los define Gerencia General o Contador")
    if not (datos.proveedor_id or datos.beneficiario_id):
        raise ValidationError("Indica un proveedor o un beneficiario", field="beneficiario_id")
    from shared.models import CategoriaGasto, Sucursal

    if db.get(CategoriaGasto, datos.categoria_gasto_id) is None:
        raise ValidationError("Categoría inexistente", field="categoria_gasto_id")
    if db.get(Sucursal, datos.sucursal_id) is None:
        raise ValidationError("Sucursal inexistente", field="sucursal_id")

    g = repository.crear_gasto_recurrente(
        db, categoria_gasto_id=datos.categoria_gasto_id, sucursal_id=datos.sucursal_id,
        proveedor_id=datos.proveedor_id, beneficiario_id=datos.beneficiario_id,
        descripcion=datos.descripcion.strip(), monto_estimado=datos.monto_estimado, frecuencia=datos.frecuencia,
        proxima_generacion=datos.proxima_generacion or date.today(), estado="activo", creado_por=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="crear", entidad="gasto_recurrente", entidad_id=g.id,
                     despues={"descripcion": g.descripcion, "frecuencia": g.frecuencia})
    return _out(db, g)


def set_estado(db: Session, gid: int, estado: str, *, user: CurrentUser) -> GastoRecurrenteOut:
    if not puede_gestionar_contabilidad(user):
        raise NoAutorizadoError("Los gastos recurrentes los administra Gerencia General o Contador")
    g = repository.obtener_gasto_recurrente(db, gid)
    if g is None:
        raise NotFoundError("Gasto recurrente no encontrado")
    g.estado = estado
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="gasto_recurrente", entidad_id=gid,
                     despues={"estado": estado})
    return _out(db, g)


def generar_vencidos(db: Session, *, hoy: date | None = None) -> int:
    """Job del scheduler: crea un `gasto` en `borrador` por cada recurrente activo y
    vencido, y avanza `proxima_generacion`. Devuelve cuántos generó."""
    hoy = hoy or date.today()
    n = 0
    for g in repository.recurrentes_vencidos(db, hoy=hoy):
        repository.crear_gasto(
            db, sucursal_id=g.sucursal_id, categoria_gasto_id=g.categoria_gasto_id,
            proveedor_id=g.proveedor_id, beneficiario_id=g.beneficiario_id, monto=g.monto_estimado,
            fecha=g.proxima_generacion, descripcion=f"{g.descripcion} (generado automáticamente)",
            estado_pago=None, estado="borrador", gasto_recurrente_id=g.id,
        )
        g.proxima_generacion = _sumar_meses(g.proxima_generacion, _MESES[g.frecuencia])
        n += 1
    if n:
        db.flush()
    return n
