"""Lógica del módulo `lubricacion` (feature 008).

- Catálogo de productos **Moebius** (§4.6), ampliable, vinculable a la pieza-insumo
  perecedera de 003.
- **Ficha de lubricación por calibre**: puntos + producto recomendado por punto +
  notas técnicas. La mantiene el Técnico Jefe / Gerencia General.
- Registro por punto en la OT (recomendado vs. usado, con desviación) — lo llama
  `servicio_tecnico` vía `registrar_en_ot`; el consumo del insumo descuenta stock (003).
- Reporte operativo de desviaciones (recomendado ≠ usado). El analítico agregado es 013.

API pública para `servicio_tecnico`:
- `ficha_para_calibre(db, calibre_id)` — puntos con recomendado, para ofrecer al abrir la OT.
- `producto_por_codigo(db, codigo)` — resuelve el código Moebius a id.
- `registrar_en_ot(db, *, orden_trabajo_id, sucursal_id, punto_lubricacion_id?, punto_nombre?,
   producto_usado_codigo, tecnico_id?, actor?)` — registro + consumo de stock; devuelve (registro, costo_insumo).
- `registros_de_ot(db, orden_trabajo_id)` / `costo_insumos_ot(db, orden_trabajo_id)`.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from lubricacion import repository
from lubricacion.models import RegistroLubricacionOT
from lubricacion.schemas import (
    DesviacionOut,
    FichaIn,
    FichaOut,
    ProductoMoebiusIn,
    ProductoMoebiusOut,
    PuntoOut,
)
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser

logger = logging.getLogger("cronos.lubricacion")

_ROLES_JEFE = {"Gerencia General", "Técnico Jefe"}


class NoAutorizadoError(ConflictError):
    status_code = 403
    code = "no_autorizado"


def _es_jefe(user: CurrentUser) -> bool:
    return bool(_ROLES_JEFE & set(getattr(user, "roles", []) or []))


# =========================================================== productos moebius
def _producto_out(p) -> ProductoMoebiusOut:
    return ProductoMoebiusOut(
        id=p.id, codigo=p.codigo, uso_recomendado=p.uso_recomendado,
        pieza_id=p.pieza_id, activo=p.activo,
    )


def listar_productos(db: Session) -> list[ProductoMoebiusOut]:
    return [_producto_out(p) for p in repository.listar_productos(db)]


def crear_producto(db: Session, datos: ProductoMoebiusIn, *, user: CurrentUser) -> ProductoMoebiusOut:
    if not _es_jefe(user):
        raise NoAutorizadoError("El catálogo Moebius lo mantiene el Técnico Jefe o Gerencia General")
    if repository.producto_por_codigo(db, datos.codigo):
        raise ConflictError("Ya existe un producto Moebius con ese código", field="codigo")
    if datos.pieza_id is not None:
        from piezas import datos_pieza

        if datos_pieza(db, datos.pieza_id) is None:
            raise ValidationError("La pieza-insumo vinculada no existe", field="pieza_id")
    p = repository.crear_producto(
        db, codigo=datos.codigo.strip(), uso_recomendado=(datos.uso_recomendado or "").strip() or None,
        pieza_id=datos.pieza_id,
    )
    registrar_cambio(db, actor=user.id, accion="crear", entidad="producto_moebius", entidad_id=p.id,
                     despues={"codigo": p.codigo})
    return _producto_out(p)


# =========================================================== ficha por calibre
def _calibre_codigo(db: Session, calibre_id: int) -> str | None:
    from inventario import calibres_por_ids

    return calibres_por_ids(db, [calibre_id]).get(calibre_id)


def _punto_out(db: Session, punto) -> PuntoOut:
    prod = repository.producto(db, punto.producto_moebius_id) if punto.producto_moebius_id else None
    return PuntoOut(
        id=punto.id, nombre=punto.nombre, producto_moebius_id=punto.producto_moebius_id,
        producto_recomendado=prod.codigo if prod else None, notas=punto.notas, orden=punto.orden,
    )


def _ficha_out(db: Session, ficha) -> FichaOut:
    return FichaOut(
        calibre_id=ficha.calibre_id, calibre_codigo=_calibre_codigo(db, ficha.calibre_id),
        notas_generales=ficha.notas_generales, actualizado_en=ficha.actualizado_en,
        puntos=[_punto_out(db, p) for p in ficha.puntos],
    )


def get_ficha(db: Session, calibre_id: int) -> FichaOut:
    ficha = repository.ficha_por_calibre(db, calibre_id)
    if ficha is None:
        raise NotFoundError("El calibre no tiene ficha de lubricación aún")
    return _ficha_out(db, ficha)


def set_ficha(db: Session, calibre_id: int, datos: FichaIn, *, user: CurrentUser) -> FichaOut:
    if not _es_jefe(user):
        raise NoAutorizadoError("La ficha de lubricación la mantiene el Técnico Jefe o Gerencia General")
    from inventario import calibres_por_ids

    if not calibres_por_ids(db, [calibre_id]):
        raise ValidationError("Calibre inexistente", field="calibre_id")

    ficha = repository.ficha_por_calibre(db, calibre_id)
    if ficha is None:
        ficha = repository.crear_ficha(
            db, calibre_id=calibre_id, notas_generales=(datos.notas_generales or "").strip() or None,
            creado_por=user.id,
        )
    else:
        ficha.notas_generales = (datos.notas_generales or "").strip() or None
        repository.borrar_puntos(db, ficha.id)
    for i, pt in enumerate(datos.puntos):
        prod = repository.producto_por_codigo(db, pt.producto_moebius_codigo) if pt.producto_moebius_codigo else None
        if pt.producto_moebius_codigo and prod is None:
            raise ValidationError(f"Producto Moebius desconocido: {pt.producto_moebius_codigo}", field="puntos")
        repository.agregar_punto(
            db, ficha_lubricacion_calibre_id=ficha.id, nombre=pt.nombre.strip(),
            producto_moebius_id=prod.id if prod else None,
            notas=(pt.notas or "").strip() or None, orden=i,
        )
    db.flush()
    db.refresh(ficha)
    registrar_cambio(db, actor=user.id, accion="editar", entidad="ficha_lubricacion_calibre",
                     entidad_id=ficha.id, despues={"calibre_id": calibre_id, "puntos": len(datos.puntos)})
    return _ficha_out(db, ficha)


# =========================================================== API pública (008)
def ficha_para_calibre(db: Session, calibre_id: int | None) -> dict | None:
    if calibre_id is None:
        return None
    ficha = repository.ficha_por_calibre(db, calibre_id)
    if ficha is None:
        return None
    return {
        "calibre_id": calibre_id,
        "notas_generales": ficha.notas_generales,
        "puntos": [
            {
                "id": p.id, "nombre": p.nombre,
                "producto_recomendado": (
                    repository.producto(db, p.producto_moebius_id).codigo
                    if p.producto_moebius_id else None
                ),
                "notas": p.notas,
            }
            for p in ficha.puntos
        ],
    }


def producto_por_codigo(db: Session, codigo: str) -> dict | None:
    p = repository.producto_por_codigo(db, codigo)
    if p is None:
        return None
    return {"id": p.id, "codigo": p.codigo, "pieza_id": p.pieza_id}


def registrar_en_ot(
    db: Session,
    *,
    orden_trabajo_id: int,
    sucursal_id: int,
    producto_usado_codigo: str,
    punto_lubricacion_id: int | None = None,
    punto_nombre: str | None = None,
    calibre_id: int | None = None,
    tecnico_id: int | None = None,
    actor: int | None = None,
) -> tuple[RegistroLubricacionOT, Decimal]:
    usado = repository.producto_por_codigo(db, producto_usado_codigo)
    if usado is None:
        raise ValidationError(f"Producto Moebius desconocido: {producto_usado_codigo}", field="producto_usado_codigo")

    recomendado_id = None
    nombre = (punto_nombre or "").strip()
    pt = None
    if punto_lubricacion_id is not None:
        pt = repository.punto(db, punto_lubricacion_id)
        if pt is None:
            raise ValidationError("Punto de lubricación inexistente", field="punto_lubricacion_id")
    elif nombre and calibre_id is not None:
        ficha = repository.ficha_por_calibre(db, calibre_id)
        if ficha is not None:
            pt = next((p for p in ficha.puntos if p.nombre.strip().lower() == nombre.lower()), None)
    if pt is not None:
        punto_lubricacion_id = pt.id
        recomendado_id = pt.producto_moebius_id
        nombre = nombre or pt.nombre
    if not nombre:
        raise ValidationError("Indica el punto de lubricación", field="punto_nombre")

    desviacion = recomendado_id is not None and recomendado_id != usado.id
    r = RegistroLubricacionOT(
        orden_trabajo_id=orden_trabajo_id, punto_lubricacion_id=punto_lubricacion_id,
        punto_nombre=nombre, producto_recomendado_id=recomendado_id,
        producto_usado_id=usado.id, tecnico_id=tecnico_id, desviacion=desviacion,
    )
    db.add(r)
    db.flush()

    costo = Decimal("0")
    if usado.pieza_id is not None:
        from piezas import consumir_en_ot

        try:
            costo = consumir_en_ot(
                db, pieza_id=usado.pieza_id, sucursal_id=sucursal_id, cantidad=1,
                orden_trabajo_id=orden_trabajo_id, actor=actor,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("consumo de insumo de lubricación no aplicado (OT %s): %s", orden_trabajo_id, exc)
    return r, costo


def registros_de_ot(db: Session, orden_trabajo_id: int) -> list[dict]:
    filas = db.scalars(
        select(RegistroLubricacionOT).where(RegistroLubricacionOT.orden_trabajo_id == orden_trabajo_id)
        .order_by(RegistroLubricacionOT.id)
    )
    salida = []
    for r in filas:
        rec = repository.producto(db, r.producto_recomendado_id) if r.producto_recomendado_id else None
        usa = repository.producto(db, r.producto_usado_id)
        salida.append({
            "id": r.id, "punto_nombre": r.punto_nombre,
            "producto_recomendado": rec.codigo if rec else None,
            "producto_usado": usa.codigo if usa else "—",
            "desviacion": r.desviacion, "fecha": r.fecha,
        })
    return salida


def costo_insumos_ot(db: Session, orden_trabajo_id: int) -> Decimal:
    from piezas import costo_pieza

    filas = db.scalars(
        select(RegistroLubricacionOT).where(RegistroLubricacionOT.orden_trabajo_id == orden_trabajo_id)
    )
    total = Decimal("0")
    for r in filas:
        usa = repository.producto(db, r.producto_usado_id)
        if usa and usa.pieza_id is not None:
            total += costo_pieza(db, usa.pieza_id)
    return total.quantize(Decimal("0.01"))


def desviacion_lubricacion(db: Session, *, desde=None, hasta=None) -> list[DesviacionOut]:
    from datetime import datetime as _dt

    stmt = select(RegistroLubricacionOT).where(RegistroLubricacionOT.desviacion.is_(True))
    if desde:
        stmt = stmt.where(RegistroLubricacionOT.fecha >= _dt(desde.year, desde.month, desde.day))
    if hasta:
        stmt = stmt.where(RegistroLubricacionOT.fecha <= _dt(hasta.year, hasta.month, hasta.day, 23, 59, 59))
    salida = []
    for r in db.scalars(stmt.order_by(RegistroLubricacionOT.fecha)):
        rec = repository.producto(db, r.producto_recomendado_id) if r.producto_recomendado_id else None
        usa = repository.producto(db, r.producto_usado_id)
        salida.append(DesviacionOut(
            orden_trabajo_id=r.orden_trabajo_id, punto_nombre=r.punto_nombre,
            producto_recomendado=rec.codigo if rec else None,
            producto_usado=usa.codigo if usa else "—",
            tecnico_id=r.tecnico_id, fecha=r.fecha,
        ))
    return salida
