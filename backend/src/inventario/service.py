"""Lógica del módulo `inventario` (feature 003).

- Relojes como unidad física con número de serie único (FR-001, FR-002).
- Alta ligada a una línea de recepción de compra de 002 (FR-003), fotos a
  `reloj-imagenes` (FR-004), papeles del Full Set a `documentos`.
- Historial INALTERABLE por número de serie (`evento_serie`, solo INSERT).
- Corrección de ficha / número de serie solo con rol elevado + motivo (FR-016a).
- `costo_adquisicion` y `margen` ocultos para roles sin visibilidad de costos (FR-019).
- Alertas de stock (cerca del máximo / última unidad) que abren la reposición de 002.
- Catálogo de calibres (008 añade la ficha de lubricación).
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from inventario import repository
from inventario.models import Reloj
from inventario.schemas import (
    AccionReponer,
    AlertaStockOut,
    CalibreIn,
    CalibreOut,
    DocumentoRelojOut,
    EventoSerieOut,
    FotoOut,
    LineaRecepcionPendienteOut,
    RelojDetalle,
    RelojIn,
    RelojOut,
    RelojPatch,
    ValorInventarioOut,
)
from shared.auditoria import registrar_cambio
from shared.exceptions import ConflictError, DomainError, NotFoundError, ValidationError
from shared.parametros import get_parametro
from shared.storage import get_object_url, put_object

logger = logging.getLogger("cronos.inventario")

_BUCKET_FOTOS = "reloj-imagenes"
_BUCKET_DOCS = "documentos"
_ROLES_VER_COSTOS = {"Gerencia General", "Gerente de Sucursal", "Contador", "Administrador"}
_ROLES_ELEVADOS = {"Gerencia General", "Gerente de Sucursal"}
_EN_STOCK = ("disponible", "reservado", "en_transito")


class NoAutorizadoError(DomainError):
    status_code = 403
    code = "rol_no_elevado"


def puede_ver_costos(user) -> bool:
    """FR-019: el costo de adquisición y el margen se restringen a roles administrativos.

    El enum de operaciones RBAC está fijado por la constitución en 4 valores
    (crear/consultar/editar/eliminar); la visibilidad de costos se resuelve por
    rol, no como una 5ª operación."""
    return bool(_ROLES_VER_COSTOS & set(getattr(user, "roles", []) or []))


def _es_elevado(user) -> bool:
    return bool(_ROLES_ELEVADOS & set(getattr(user, "roles", []) or []))


# =========================================================== calibres
def listar_calibres(db: Session, *, q: str | None = None) -> list[CalibreOut]:
    return [
        CalibreOut(id=c.id, codigo=c.codigo, marca=c.marca, descripcion=c.descripcion, relojes=n)
        for c, n in repository.listar_calibres(db, q=q)
    ]


def crear_calibre(db: Session, datos: CalibreIn, *, actor: int) -> CalibreOut:
    if repository.calibre_por_codigo(db, datos.codigo):
        raise ConflictError("Ya existe un calibre con ese código", field="codigo")
    c = repository.crear_calibre(db, codigo=datos.codigo, marca=datos.marca, descripcion=datos.descripcion)
    registrar_cambio(db, actor=actor, accion="crear", entidad="calibre", entidad_id=c.id,
                     despues=datos.model_dump(exclude_none=True))
    return CalibreOut(id=c.id, codigo=c.codigo, marca=c.marca, descripcion=c.descripcion, relojes=0)


def calibres_por_ids(db: Session, ids: list[int]) -> dict[int, str]:
    """Público: usado por `piezas` para etiquetar calibres compatibles."""
    return repository.codigos_calibre(db, ids)


def validar_calibres(db: Session, ids: list[int]) -> None:
    faltan = [i for i in ids if repository.calibre_por_id(db, i) is None]
    if faltan:
        raise ValidationError(f"Calibres inexistentes: {faltan}", field="calibres_compatibles")


# =========================================================== relojes
def _margen(costo, precio) -> Decimal | None:
    if costo is None or precio is None:
        return None
    return Decimal(precio) - Decimal(costo)


def _buscar_o_crear(db: Session, modelo, nombre: str | None, **extra):
    """Busca un valor de catálogo por nombre (case-insensitive) o lo crea. Devuelve id|None."""
    if not nombre or not nombre.strip():
        return None
    from sqlalchemy import func as _f, select as _s

    fila = db.scalars(_s(modelo).where(_f.lower(modelo.nombre) == nombre.strip().lower())).first()
    if fila is None:
        fila = modelo(nombre=nombre.strip(), **extra)
        db.add(fila)
        db.flush()
    return fila.id


def _resolver_catalogos(db: Session, datos) -> dict:
    """Traduce marca/materiales/color (id o texto) a ids + la marca denormalizada."""
    from shared.models import Color, MarcaReloj, Material

    d = datos.model_dump()
    marca_id = d.get("marca_id") or _buscar_o_crear(db, MarcaReloj, d.get("marca"))
    caja_id = d.get("material_caja_id") or _buscar_o_crear(db, Material, d.get("material_caja"))
    braz_id = d.get("material_brazalete_id") or _buscar_o_crear(db, Material, d.get("material_brazalete"))
    color_id = d.get("color_esfera_id") or _buscar_o_crear(db, Color, d.get("color_esfera"))
    marca_txt = None
    if marca_id:
        m = db.get(MarcaReloj, marca_id)
        marca_txt = m.nombre if m else None
    return {
        "marca_id": marca_id, "marca": marca_txt,
        "material_caja_id": caja_id, "material_brazalete_id": braz_id, "color_esfera_id": color_id,
    }


def _labels_catalogo(db: Session, r: Reloj) -> dict:
    from shared.models import Color, MarcaReloj, Material

    def _n(modelo, idx):
        o = db.get(modelo, idx) if idx else None
        return o.nombre if o else None

    color = db.get(Color, r.color_esfera_id) if r.color_esfera_id else None
    return {
        "marca_id": r.marca_id,
        "material_caja": _n(Material, r.material_caja_id) or r.material_caja,
        "material_caja_id": r.material_caja_id,
        "material_brazalete": _n(Material, r.material_brazalete_id) or r.material_brazalete,
        "material_brazalete_id": r.material_brazalete_id,
        "color_esfera": (color.nombre if color else r.color_esfera),
        "color_esfera_id": r.color_esfera_id,
        "color_esfera_hex": color.hex if color else None,
    }


def _reloj_out(db: Session, r: Reloj, *, ver_costos: bool, detalle: bool = False) -> RelojOut:
    cod = repository.codigos_calibre(db, [r.calibre_id]).get(r.calibre_id) if r.calibre_id else None
    base = dict(
        id=r.id, numero_serie=r.numero_serie, marca=r.marca, referencia=r.referencia,
        calibre_id=r.calibre_id, calibre_codigo=cod, anio_fabricacion=r.anio_fabricacion,
        **_labels_catalogo(db, r),
        tipo_cristal=r.tipo_cristal, resistencia_agua=r.resistencia_agua,
        estado_producto=r.estado_producto, precio_venta=r.precio_venta, fecha_ingreso=r.fecha_ingreso,
        proveedor_id=r.proveedor_id, recepcion_linea_id=r.recepcion_linea_id, full_set=r.full_set,
        full_set_detalle=r.full_set_detalle, sucursal_actual_id=r.sucursal_actual_id,
        disponibilidad=r.disponibilidad, creado_en=r.creado_en,
        foto_url=get_object_url(_BUCKET_FOTOS, r.fotos[0].objeto) if r.fotos else None,
        costos_visibles=ver_costos,
        costo_adquisicion=r.costo_adquisicion if ver_costos else None,
        margen=_margen(r.costo_adquisicion, r.precio_venta) if ver_costos else None,
    )
    if not detalle:
        return RelojOut(**base)
    return RelojDetalle(
        **base,
        fotos=[FotoOut(id=f.id, orden=f.orden, url=get_object_url(_BUCKET_FOTOS, f.objeto))
               for f in repository.fotos_de(db, r.id)],
        documentos=[DocumentoRelojOut(id=d.id, tipo=d.tipo, nombre=d.nombre,
                                      url=get_object_url(_BUCKET_DOCS, d.objeto))
                    for d in repository.documentos_de(db, r.id)],
    )


def sucursales_visibles(user, sucursal_id: int | None) -> list[int] | None:
    """Scoping por sucursal (feature 004, FR-008): Gerencia General ve el
    consolidado (o filtra por `sucursal_id`); el resto solo sus sucursales."""
    if getattr(user, "es_gerencia", False):
        return [sucursal_id] if sucursal_id else None
    permitidas = list(getattr(user, "sucursal_ids", []) or [])
    if sucursal_id:
        permitidas = [s for s in permitidas if s == sucursal_id]
    return permitidas or [-1]


def listar_relojes(db, *, user, q, marca, sucursal_id, disponibilidad, calibre, offset, limit, tipo_cristal=None):
    filas, total = repository.buscar_relojes(
        db, q=q, marca=marca, sucursal_id=sucursal_id, disponibilidad=disponibilidad,
        calibre=calibre, sucursales=sucursales_visibles(user, sucursal_id), offset=offset, limit=limit,
        tipo_cristal=tipo_cristal,
    )
    vc = puede_ver_costos(user)
    return [_reloj_out(db, r, ver_costos=vc) for r in filas], total


def buscar_disponibilidad_global(
    db: Session, *, q: str | None, marca: str | None, calibre: str | None, tipo_cristal: str | None,
) -> list[dict]:
    """Público (009/004): para armar una venta, el vendedor puede consultar el
    inventario COMPLETO (todas las sucursales) de un modelo — no solo la suya —
    y así saber si conviene iniciar un traslado (Esp. §4.1/§4.4, feedback del
    usuario 2026-09-11). Deliberadamente sin scoping ni costos."""
    filas = repository.buscar_disponibilidad_global(db, q=q, marca=marca, calibre=calibre, tipo_cristal=tipo_cristal)
    ids_calibre = [r.calibre_id for r, _ in filas if r.calibre_id]
    codigos = repository.codigos_calibre(db, ids_calibre) if ids_calibre else {}
    return [
        {
            "id": r.id, "numero_serie": r.numero_serie, "marca": r.marca, "referencia": r.referencia,
            "calibre_codigo": codigos.get(r.calibre_id), "tipo_cristal": r.tipo_cristal,
            "precio_venta": r.precio_venta, "sucursal_id": r.sucursal_actual_id, "sucursal_nombre": nombre_sucursal,
        }
        for r, nombre_sucursal in filas
    ]


def obtener_por_serie(db: Session, serie: str, *, user) -> RelojDetalle:
    r = repository.reloj_por_serie(db, serie)
    if r is None:
        raise NotFoundError("No hay ningún reloj con ese número de serie")
    return _reloj_out(db, r, ver_costos=puede_ver_costos(user), detalle=True)


def _resolver_calibre(db: Session, calibre_id: int | None) -> int | None:
    if calibre_id is None:
        return None
    if repository.calibre_por_id(db, calibre_id) is None:
        raise ValidationError("Calibre inexistente", field="calibre_id")
    return calibre_id


def crear_reloj(db: Session, datos: RelojIn, *, foto: bytes | None, foto_nombre: str | None, actor: int) -> RelojDetalle:
    from proveedores.public import linea_compra_info

    if repository.reloj_por_serie(db, datos.numero_serie):
        raise ConflictError("Ya existe una unidad con ese número de serie", field="numero_serie")

    if not datos.recepcion_linea_id and not (datos.motivo_alta_manual and datos.motivo_alta_manual.strip()):
        raise ValidationError(
            "Vincula la unidad a una línea de recepción de compra, o indica el motivo del alta manual "
            "(inventario inicial, recompra a cliente, consignación…).",
            field="motivo_alta_manual",
        )

    campos = datos.model_dump(exclude={
        "marca", "material_caja", "material_brazalete", "color_esfera", "motivo_alta_manual",
    })
    campos["calibre_id"] = _resolver_calibre(db, datos.calibre_id)
    campos.update(_resolver_catalogos(db, datos))

    # Herencia desde la línea de recepción de compra (002).
    if datos.recepcion_linea_id:
        info = linea_compra_info(db, datos.recepcion_linea_id)
        if info is None or info.item_tipo != "reloj":
            raise ValidationError("Línea de recepción de compra inválida", field="recepcion_linea_id")
        campos["proveedor_id"] = campos.get("proveedor_id") or info.proveedor_id
        campos["sucursal_actual_id"] = campos.get("sucursal_actual_id") or info.sucursal_destino_id
        if campos.get("costo_adquisicion") is None and info.costo_unitario:
            campos["costo_adquisicion"] = Decimal(str(info.costo_unitario))
        if not campos.get("referencia"):
            campos["referencia"] = info.item_ref
        if not campos.get("marca_id") and info.marca:
            from shared.models import MarcaReloj

            campos["marca_id"] = _buscar_o_crear(db, MarcaReloj, info.marca)
            campos["marca"] = info.marca
        if not campos.get("calibre_id") and info.calibre_codigo:
            from inventario.repository import calibre_por_codigo

            cal = calibre_por_codigo(db, info.calibre_codigo)
            campos["calibre_id"] = cal.id if cal else None
        if not campos.get("anio_fabricacion") and info.anio:
            campos["anio_fabricacion"] = info.anio

    if not campos.get("marca"):
        raise ValidationError("La marca es obligatoria", field="marca_id")

    if campos.get("fecha_ingreso") is None:
        campos["fecha_ingreso"] = date.today()

    r = Reloj(**campos)
    db.add(r)
    db.flush()

    if foto:
        _guardar_foto(db, r, foto, foto_nombre)

    repository.registrar_evento(
        db, numero_serie=r.numero_serie, reloj_id=r.id, tipo="ingreso",
        documento_tipo="recepcion_compra" if datos.recepcion_linea_id else "alta_manual",
        documento_id=datos.recepcion_linea_id, actor=actor,
        detalle={
            "marca": r.marca, "referencia": r.referencia, "sucursal_id": r.sucursal_actual_id,
            "motivo": None if datos.recepcion_linea_id else (datos.motivo_alta_manual or "").strip(),
        },
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="reloj", entidad_id=r.id,
                     despues={"numero_serie": r.numero_serie, "marca": r.marca, "referencia": r.referencia})
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    return _reloj_out(db, r, ver_costos=True, detalle=True)


def corregir_reloj(db: Session, rid: int, datos: RelojPatch, *, user) -> RelojDetalle:
    if not _es_elevado(user):
        raise NoAutorizadoError("Corregir la ficha de una unidad requiere rol elevado")
    r = repository.obtener_reloj(db, rid)
    if r is None:
        raise NotFoundError("Unidad no encontrada")

    cambios = datos.model_dump(exclude_unset=True, exclude={"motivo"})
    if not cambios:
        raise ValidationError("No hay cambios que aplicar", field="motivo")

    antes = _reloj_out(db, r, ver_costos=True).model_dump()
    serie_anterior = r.numero_serie

    if "numero_serie" in cambios and cambios["numero_serie"] and cambios["numero_serie"] != serie_anterior:
        if repository.reloj_por_serie(db, cambios["numero_serie"]):
            raise ConflictError("Ese número de serie ya está en uso", field="numero_serie")
    if "calibre_id" in cambios:
        _resolver_calibre(db, cambios["calibre_id"])

    # marca por id o por texto (busca-o-crea); mantiene `reloj.marca` sincronizada
    if cambios.pop("marca", None) or "marca_id" in cambios:
        resueltos = _resolver_catalogos(db, datos)
        if resueltos["marca_id"]:
            r.marca_id, r.marca = resueltos["marca_id"], resueltos["marca"]
        cambios.pop("marca_id", None)

    for campo, valor in cambios.items():
        setattr(r, campo, valor)
    db.flush()

    # El historial es inalterable: los eventos previos conservan la serie anterior.
    # `historial_serie` los sigue mostrando porque resuelve la serie → reloj_id.
    repository.registrar_evento(
        db, numero_serie=r.numero_serie, reloj_id=r.id, tipo="correccion",
        detalle={"motivo": datos.motivo, "cambios": {k: str(v) for k, v in cambios.items()},
                 "serie_anterior": serie_anterior if r.numero_serie != serie_anterior else None},
        actor=user.id,
    )
    registrar_cambio(db, actor=user.id, accion="corregir", entidad="reloj", entidad_id=r.id,
                     antes=antes, despues={**_reloj_out(db, r, ver_costos=True).model_dump(), "motivo": datos.motivo})
    return _reloj_out(db, r, ver_costos=puede_ver_costos(user), detalle=True)


# ------------------------------------------------------------ fotos / documentos
def _guardar_foto(db: Session, r: Reloj, data: bytes, nombre: str | None) -> FotoOut:
    n = len(repository.fotos_de(db, r.id))
    ext = (nombre or "foto.jpg").rsplit(".", 1)[-1].lower()[:5]
    clave = f"reloj/{r.numero_serie}/{uuid.uuid4().hex}.{ext}"
    put_object(_BUCKET_FOTOS, clave, data, content_type=f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}")
    f = repository.agregar_foto(db, reloj_id=r.id, objeto=clave, orden=n)
    return FotoOut(id=f.id, orden=f.orden, url=get_object_url(_BUCKET_FOTOS, clave))


def agregar_foto(db: Session, rid: int, *, data: bytes, nombre: str | None, actor: int) -> FotoOut:
    r = repository.obtener_reloj(db, rid)
    if r is None:
        raise NotFoundError("Unidad no encontrada")
    if not data:
        raise ValidationError("El archivo de imagen está vacío", field="foto")
    out = _guardar_foto(db, r, data, nombre)
    registrar_cambio(db, actor=actor, accion="crear", entidad="foto_reloj", entidad_id=out.id,
                     despues={"reloj_id": rid})
    return out


def agregar_documento(db: Session, rid: int, *, tipo: str, nombre: str, data: bytes, actor: int) -> DocumentoRelojOut:
    r = repository.obtener_reloj(db, rid)
    if r is None:
        raise NotFoundError("Unidad no encontrada")
    tipo = tipo if tipo in {"papeles_full_set", "factura_compra", "otro"} else "otro"
    clave = f"reloj/{r.numero_serie}/docs/{uuid.uuid4().hex}-{(nombre or 'documento')[:60]}"
    put_object(_BUCKET_DOCS, clave, data, content_type="application/octet-stream")
    d = repository.agregar_documento(db, reloj_id=rid, objeto=clave, tipo=tipo, nombre=nombre, subido_por=actor)
    registrar_cambio(db, actor=actor, accion="crear", entidad="documento_reloj", entidad_id=d.id,
                     despues={"reloj_id": rid, "tipo": tipo})
    return DocumentoRelojOut(id=d.id, tipo=d.tipo, nombre=d.nombre, url=get_object_url(_BUCKET_DOCS, clave))


def historial_serie(db: Session, serie: str) -> list[EventoSerieOut]:
    r = repository.reloj_por_serie(db, serie)
    eventos = repository.eventos_de_serie(db, serie, reloj_id=r.id if r else None)
    if not eventos and r is None:
        raise NotFoundError("No hay ningún reloj con ese número de serie")
    return [
        EventoSerieOut(tipo=e.tipo, fecha=e.fecha, documento_tipo=e.documento_tipo,
                       documento_id=e.documento_id, detalle=e.detalle)
        for e in eventos
    ]


# ------------------------------------------------------------ traslados (004)
def relojes_disponibles_en(db: Session, sucursal_id: int, *, q: str | None = None, limit: int = 50) -> list[dict]:
    """Público (004): relojes `disponible` en una sucursal, para armar una transferencia."""
    filas, _ = repository.buscar_relojes(
        db, q=q, marca=None, sucursal_id=sucursal_id, disponibilidad="disponible",
        calibre=None, offset=0, limit=limit,
    )
    return [
        {"id": r.id, "numero_serie": r.numero_serie, "marca": r.marca, "referencia": r.referencia}
        for r in filas
    ]


def ids_relojes_por_serie(db: Session, q_serie: str) -> list[int]:
    """Público (004): ids de relojes cuyo número de serie coincide (para filtrar transferencias)."""
    filas, _ = repository.buscar_relojes(
        db, q=q_serie.strip(), marca=None, sucursal_id=None, disponibilidad=None,
        calibre=None, offset=0, limit=200,
    )
    return [r.id for r in filas if q_serie.strip().lower() in r.numero_serie.lower()]


def reloj_para_traslado(db: Session, reloj_id: int) -> dict | None:
    """Público (004): datos mínimos de un reloj para validar una transferencia."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        return None
    return {
        "id": r.id, "numero_serie": r.numero_serie, "marca": r.marca, "referencia": r.referencia,
        "sucursal_actual_id": r.sucursal_actual_id, "disponibilidad": r.disponibilidad,
    }


def marcar_reloj_en_transito(db: Session, reloj_id: int, *, transferencia_id: int, actor: int) -> None:
    """Público (004): al enviar la transferencia. Exige `disponible`."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        raise NotFoundError("Unidad no encontrada")
    if r.disponibilidad != "disponible":
        raise ConflictError(
            f"La unidad {r.numero_serie} ya no está disponible (estado: {r.disponibilidad})"
        )
    r.disponibilidad = "en_transito"
    db.flush()
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"disponibilidad": "disponible"},
                     despues={"disponibilidad": "en_transito", "transferencia_id": transferencia_id})


def recibir_reloj_transferido(
    db: Session, reloj_id: int, *, sucursal_destino_id: int, transferencia_id: int,
    origen: str, destino: str, motivo: str, actor: int,
) -> None:
    """Público (004): al confirmar la recepción. Mueve la unidad a la sucursal destino."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        raise NotFoundError("Unidad no encontrada")
    origen_id = r.sucursal_actual_id
    r.sucursal_actual_id = sucursal_destino_id
    r.disponibilidad = "disponible"
    db.flush()
    repository.registrar_evento(
        db, numero_serie=r.numero_serie, reloj_id=r.id, tipo="transferencia",
        documento_tipo="transferencia", documento_id=transferencia_id,
        detalle={"origen": origen, "destino": destino, "motivo": motivo}, actor=actor,
    )
    for suc in {origen_id, sucursal_destino_id}:
        _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=suc)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"sucursal_actual_id": origen_id, "disponibilidad": "en_transito"},
                     despues={"sucursal_actual_id": sucursal_destino_id, "disponibilidad": "disponible",
                              "transferencia_id": transferencia_id})


def revertir_reloj_transferencia(db: Session, reloj_id: int, *, transferencia_id: int, actor: int) -> None:
    """Público (004): al cancelar una transferencia en tránsito — vuelve a `disponible` en origen."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None or r.disponibilidad != "en_transito":
        return
    r.disponibilidad = "disponible"
    db.flush()
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"disponibilidad": "en_transito"},
                     despues={"disponibilidad": "disponible", "transferencia_cancelada": transferencia_id})


def marcar_reloj_en_servicio(db: Session, reloj_id: int, *, orden_trabajo_id: int, actor: int) -> None:
    """Público (008): al abrir la OT — nunca debe quedar vendible mientras está en el
    taller (bug 2026-09-11: un reloj en reparación seguía "disponible" en Ventas).
    `crear_ot` solo permite abrir la OT si la unidad se compró en la tienda o hay un
    motivo de excepción (es del cliente) — en ambos casos parte de `disponible` o
    `vendido`; nunca de `en_transito`/`dado_de_baja`/`en_servicio` (una OT a la vez)."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        raise NotFoundError("Unidad no encontrada")
    if r.disponibilidad not in ("disponible", "vendido"):
        raise ConflictError(
            f"La unidad {r.numero_serie} no puede entrar a servicio (estado: {r.disponibilidad})"
        )
    antes = r.disponibilidad
    r.disponibilidad = "en_servicio"
    db.flush()
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"disponibilidad": antes},
                     despues={"disponibilidad": "en_servicio", "orden_trabajo_id": orden_trabajo_id})


def revertir_reloj_servicio(db: Session, reloj_id: int, *, orden_trabajo_id: int, actor: int) -> None:
    """Público (008): al entregar o cancelar la OT. Siempre vuelve a `vendido`, nunca a
    `disponible` — toda unidad que entra a servicio es del cliente (comprada aquí o
    ajena con motivo de excepción, ver `marcar_reloj_en_servicio`), jamás stock propio
    para vender; devolverla "disponible" la volvería a ofrecer en Ventas."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None or r.disponibilidad != "en_servicio":
        return
    r.disponibilidad = "vendido"
    db.flush()
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"disponibilidad": "en_servicio"},
                     despues={"disponibilidad": "vendido", "orden_trabajo_id": orden_trabajo_id})


# ------------------------------------------------------------ evento externo (008/009/011)
def registrar_evento_externo(
    db: Session, *, numero_serie: str, tipo: str, documento_tipo: str, documento_id: int,
    detalle: dict | None = None, actor: int | None = None,
) -> None:
    """Público: 008/009/011 registran servicios / venta / baja en el historial."""
    r = repository.reloj_por_serie(db, numero_serie)
    repository.registrar_evento(
        db, numero_serie=numero_serie, reloj_id=r.id if r else None, tipo=tipo,
        documento_tipo=documento_tipo, documento_id=documento_id, detalle=detalle, actor=actor,
    )


def reloj_para_ot(db: Session, reloj_id: int) -> dict | None:
    """Público (008): datos de la unidad para abrir una orden de trabajo."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        return None
    return {
        "id": r.id, "numero_serie": r.numero_serie, "marca": r.marca,
        "referencia": r.referencia, "calibre_id": r.calibre_id,
        "disponibilidad": r.disponibilidad, "sucursal_actual_id": r.sucursal_actual_id,
    }


def relojes_elegibles_para_ot(db: Session, *, q: str | None = None, limit: int = 50) -> list[dict]:
    """Público (008): unidades reales para el selector de "unidad" al abrir una OT
    (feedback del usuario, 2026-09-11: el número de serie era texto libre — Ppio XI
    exige elegir de un catálogo real, no escribirlo a mano)."""
    return [
        {"id": r.id, "numero_serie": r.numero_serie, "marca": r.marca, "referencia": r.referencia,
         "disponibilidad": r.disponibilidad}
        for r in repository.buscar_relojes_elegibles_ot(db, q=q, limit=limit)
    ]


def serie_adquirida_en_tienda(db: Session, numero_serie: str) -> bool:
    """Público (008): la unidad tiene al menos un evento de `venta` (o `venta_previa_sistema`)
    en su historial de serie — es decir, consta que se compró en la tienda."""
    eventos = repository.eventos_de_serie(db, numero_serie)
    return any(e.tipo in ("venta", "venta_previa_sistema") for e in eventos)


def reloj_para_venta(db: Session, reloj_id: int, *, ver_costos: bool = False) -> dict | None:
    """Público (009): datos de la unidad para una línea de venta. `costo_adquisicion`
    solo si `ver_costos` (rol administrativo)."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        return None
    return {
        "id": r.id, "numero_serie": r.numero_serie, "marca": r.marca,
        "referencia": r.referencia, "disponibilidad": r.disponibilidad,
        "sucursal_actual_id": r.sucursal_actual_id,
        "precio_venta": r.precio_venta,
        "costo_adquisicion": r.costo_adquisicion if ver_costos else None,
        "_costo": r.costo_adquisicion,  # uso interno del cálculo de margen (nunca al cliente)
    }


def marcar_reloj_vendido(db: Session, reloj_id: int, *, documento_id: int, actor: int) -> None:
    """Público (009): al confirmar la venta. Exige la unidad `disponible`.
    Registra `evento_serie(venta)` y saca la unidad del stock activo."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        raise NotFoundError("Unidad no encontrada")
    if r.disponibilidad != "disponible":
        raise ConflictError(
            f"La unidad {r.numero_serie} no está disponible para la venta (estado: {r.disponibilidad})"
        )
    r.disponibilidad = "vendido"
    db.flush()
    repository.registrar_evento(
        db, numero_serie=r.numero_serie, reloj_id=r.id, tipo="venta",
        documento_tipo="orden_venta", documento_id=documento_id, actor=actor,
    )
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"disponibilidad": "disponible"},
                     despues={"disponibilidad": "vendido", "orden_venta_id": documento_id})


def revertir_reloj_venta(db: Session, reloj_id: int, *, documento_id: int, actor: int) -> None:
    """Público (009): al anular la venta — la unidad vuelve a `disponible` con evento `reingreso`."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None or r.disponibilidad != "vendido":
        return
    r.disponibilidad = "disponible"
    db.flush()
    repository.registrar_evento(
        db, numero_serie=r.numero_serie, reloj_id=r.id, tipo="reingreso",
        documento_tipo="orden_venta", documento_id=documento_id, actor=actor,
    )
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"disponibilidad": "vendido"},
                     despues={"disponibilidad": "disponible", "venta_anulada": documento_id})


def reloj_para_merma(db: Session, reloj_id: int) -> dict | None:
    """Público (011): datos de la unidad para reportar una merma (incluye el
    costo de adquisición — el costeo de la pérdida es siempre a ese costo)."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        return None
    return {
        "id": r.id, "numero_serie": r.numero_serie, "marca": r.marca,
        "referencia": r.referencia, "disponibilidad": r.disponibilidad,
        "sucursal_actual_id": r.sucursal_actual_id, "costo_adquisicion": r.costo_adquisicion,
    }


def marcar_reloj_baja(db: Session, reloj_id: int, *, documento_id: int, actor: int) -> None:
    """Público (011): al confirmar la baja definitiva por merma. La unidad no
    puede estar ya `vendido` ni `dado_de_baja` (FR-018)."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None:
        raise NotFoundError("Unidad no encontrada")
    if r.disponibilidad in ("vendido", "dado_de_baja"):
        raise ConflictError(
            f"La unidad {r.numero_serie} no puede darse de baja (estado: {r.disponibilidad})"
        )
    antes = r.disponibilidad
    r.disponibilidad = "dado_de_baja"
    db.flush()
    repository.registrar_evento(
        db, numero_serie=r.numero_serie, reloj_id=r.id, tipo="baja",
        documento_tipo="merma", documento_id=documento_id, actor=actor,
    )
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"disponibilidad": antes},
                     despues={"disponibilidad": "dado_de_baja", "merma_id": documento_id})


def revertir_reloj_baja(db: Session, reloj_id: int, *, documento_id: int, actor: int) -> None:
    """Público (011): "reparado y reingresado a stock" — vuelve a `disponible`."""
    r = repository.obtener_reloj(db, reloj_id)
    if r is None or r.disponibilidad != "dado_de_baja":
        return
    r.disponibilidad = "disponible"
    db.flush()
    repository.registrar_evento(
        db, numero_serie=r.numero_serie, reloj_id=r.id, tipo="reingreso",
        documento_tipo="merma", documento_id=documento_id, actor=actor,
    )
    _recalcular_alertas_modelo(db, marca=r.marca, referencia=r.referencia, sucursal_id=r.sucursal_actual_id)
    registrar_cambio(db, actor=actor, accion="editar", entidad="reloj", entidad_id=r.id,
                     antes={"disponibilidad": "dado_de_baja"},
                     despues={"disponibilidad": "disponible", "merma_reingresada": documento_id})


# =========================================================== alertas de stock
def _recalcular_alertas_modelo(db: Session, *, marca: str, referencia: str, sucursal_id: int | None) -> None:
    ref = f"{marca}|{referencia}"
    n = repository.contar_modelo(db, marca=marca, referencia=referencia, sucursal_id=sucursal_id)
    maximo = int(get_parametro(db, "stock_maximo_modelo", default=12) or 12)
    umbral = int(get_parametro(db, "umbral_reposicion_relojes", default=1) or 1)
    base = {"marca": marca, "referencia": referencia, "unidades": n, "maximo": maximo}

    repository.resolver_alertas(db, ambito="modelo", ref=ref, sucursal_id=sucursal_id,
                               tipos=["ultima_unidad", "cerca_maximo"])
    # (a) reposición: el modelo bajó al umbral configurado o menos (FR-012)
    if 0 < n <= umbral:
        if repository.alerta_abierta(db, ambito="modelo", ref=ref, sucursal_id=sucursal_id, tipo="ultima_unidad") is None:
            repository.abrir_alerta(db, ambito="modelo", ref=ref, sucursal_id=sucursal_id, tipo="ultima_unidad", detalle=base)
    # (b) sobre-stock: alcanzó o superó el máximo recomendado — avisa, no bloquea (SC-006)
    elif n >= maximo:
        if repository.alerta_abierta(db, ambito="modelo", ref=ref, sucursal_id=sucursal_id, tipo="cerca_maximo") is None:
            repository.abrir_alerta(db, ambito="modelo", ref=ref, sucursal_id=sucursal_id, tipo="cerca_maximo", detalle=base)


def recalcular_alertas_pieza(
    db: Session, *, pieza_id: int, pieza_codigo: str, sucursal_id: int,
    stock_actual: int, stock_minimo: int, lotes_vencidos: int = 0, lotes_por_vencer: int = 0,
) -> None:
    """Público: `piezas` lo llama tras cada movimiento / recálculo de lotes."""
    ref = str(pieza_id)
    umbral = int(get_parametro(db, "umbral_reposicion_piezas", default=0) or 0)

    repository.resolver_alertas(db, ambito="pieza", ref=ref, sucursal_id=sucursal_id, tipos=["bajo_minimo"])
    if stock_actual <= stock_minimo + umbral:
        if repository.alerta_abierta(db, ambito="pieza", ref=ref, sucursal_id=sucursal_id, tipo="bajo_minimo") is None:
            repository.abrir_alerta(db, ambito="pieza", ref=ref, sucursal_id=sucursal_id, tipo="bajo_minimo",
                                   detalle={"codigo": pieza_codigo, "stock": stock_actual, "minimo": stock_minimo})

    for tipo, cuenta in (("lote_vencido", lotes_vencidos), ("caducidad_proxima", lotes_por_vencer)):
        repository.resolver_alertas(db, ambito="pieza", ref=ref, sucursal_id=sucursal_id, tipos=[tipo])
        if cuenta > 0 and repository.alerta_abierta(
            db, ambito="pieza", ref=ref, sucursal_id=sucursal_id, tipo=tipo
        ) is None:
            repository.abrir_alerta(db, ambito="pieza", ref=ref, sucursal_id=sucursal_id, tipo=tipo,
                                   detalle={"codigo": pieza_codigo, "lotes": cuenta})


def _accion_reponer(db: Session, a) -> AccionReponer | None:
    # 'cerca_maximo' es sobre-stock: no se repone.
    if a.tipo not in ("ultima_unidad", "bajo_minimo"):
        return None
    if a.ambito == "modelo":
        marca, referencia = a.ref.split("|", 1)
        maximo = int(get_parametro(db, "stock_maximo_modelo", default=12) or 12)
        n = (a.detalle or {}).get("unidades", 0)
        prov = repository.proveedor_habitual_modelo(db, marca=marca, referencia=referencia)
        return AccionReponer(item_tipo="reloj", item_ref=referencia, marca=marca,
                             cantidad_sugerida=max(1, maximo - int(n)), proveedor_id=prov)
    codigo = (a.detalle or {}).get("codigo") or a.ref
    minimo = (a.detalle or {}).get("minimo", 0)
    stock = (a.detalle or {}).get("stock", 0)
    return AccionReponer(item_tipo="pieza", item_ref=str(codigo),
                         cantidad_sugerida=max(1, int(minimo) * 2 - int(stock)), proveedor_id=None)


def _etiqueta_alerta(a) -> str:
    d = a.detalle or {}
    if a.ambito == "modelo":
        return f"{d.get('marca', '')} {d.get('referencia', '')}".strip() or a.ref
    return str(d.get("codigo") or a.ref)


def listar_alertas(db: Session, *, tipo: str | None, sucursal_id: int | None) -> list[AlertaStockOut]:
    salida = []
    for a in repository.alertas_abiertas(db, tipo=tipo, sucursal_id=sucursal_id):
        salida.append(AlertaStockOut(
            id=a.id, ambito=a.ambito, ref=a.ref, etiqueta=_etiqueta_alerta(a),
            sucursal_id=a.sucursal_id, tipo=a.tipo, detalle=a.detalle, creado_en=a.creado_en,
            accion_reponer=_accion_reponer(db, a),
        ))
    return salida


# =========================================================== valor de inventario
def valor_inventario(db: Session, *, user, sucursal_id: int | None) -> ValorInventarioOut:
    filas = repository.valor_inventario(db, sucursal_id=sucursal_id, sucursales=sucursales_visibles(user, sucursal_id))
    unidades = sum(int(f[1]) for f in filas)
    a_precio = sum(Decimal(str(f[2])) for f in filas) if filas else Decimal("0")
    a_costo = sum(Decimal(str(f[3])) for f in filas) if filas else Decimal("0")
    por_suc = [
        {"sucursal_id": f[0], "unidades": int(f[1]), "a_precio_venta": float(f[2]),
         "a_costo": float(f[3]) if puede_ver_costos(user) else None}
        for f in filas
    ]
    return ValorInventarioOut(
        unidades=unidades, a_precio_venta=a_precio,
        a_costo=a_costo if puede_ver_costos(user) else None, por_sucursal=por_suc,
    )


# =========================================================== líneas pendientes de fichar
def lineas_recepcion_pendientes(db: Session) -> list[LineaRecepcionPendienteOut]:
    from proveedores.public import lineas_compra_recibidas

    salida = []
    for info in lineas_compra_recibidas(db, item_tipo="reloj"):
        fichadas = repository.relojes_por_recepcion_linea(db, info.linea_id)
        pendientes = info.recibidas - fichadas
        if pendientes <= 0:
            continue
        salida.append(LineaRecepcionPendienteOut(
            recepcion_linea_id=info.linea_id, orden_compra_id=info.orden_compra_id,
            proveedor_id=info.proveedor_id, sucursal_destino_id=info.sucursal_destino_id,
            item_ref=info.item_ref, marca=info.marca, calibre_codigo=info.calibre_codigo,
            anio=info.anio, numero_serie=info.numero_serie, descripcion=info.descripcion,
            recibidas=info.recibidas,
            fichadas=fichadas, pendientes=pendientes, costo_unitario=Decimal(str(info.costo_unitario)),
        ))
    return salida


# =========================================================== consumidores de parámetros
def _recalcular_todas_las_alertas_modelo(db: Session, _clave: str) -> int:
    vistos = set()
    for marca, referencia, sucursal_id in repository.modelos_distintos(db):
        clave = (marca, referencia, sucursal_id)
        if clave in vistos:
            continue
        vistos.add(clave)
        _recalcular_alertas_modelo(db, marca=marca, referencia=referencia, sucursal_id=sucursal_id)
    return len(vistos)


def registrar_consumidores() -> None:
    from shared.parametros import registrar_consumidor

    for clave in ("stock_maximo_modelo", "umbral_reposicion_relojes"):
        registrar_consumidor(clave, _recalcular_todas_las_alertas_modelo, nombre="inventario.alertas_modelo")
