"""Configuración: catálogos, parámetros con recálculo en cascada y visor de auditoría."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from configuracion import repository
from configuracion.schemas import (
    ActivoIn,
    AuditoriaItem,
    CatalogoItem,
    CategoriaGastoIn,
    CategoriaMermaIn,
    CanalCitaIn,
    ColorIn,
    CondicionPagoIn,
    MarcaRelojIn,
    MaterialIn,
    MedioPagoIn,
    ParametroHistorialItem,
    ParametroIn,
    ParametroOut,
    RecalculoOut,
    SetParametroOut,
)
from shared.auditoria import registrar_cambio
from shared.auditoria import repository as auditoria_repo
from shared.exceptions import ConflictError
from shared.parametros import get_parametro, set_parametro
from shared.parametros import repository as parametros_repo


# ------------------------------------------------------------------- catálogos
def _slug(nombre: str) -> str:
    import re
    import unicodedata

    base = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "_", base.lower().strip()).strip("_")
    return s[:20] or "medio"


def listar_medios_pago(db: Session) -> list[CatalogoItem]:
    return [CatalogoItem(id=m.id, clave=m.clave, nombre=m.nombre, activo=m.activo) for m in repository.medios_pago(db)]


def crear_medio_pago(db: Session, datos: MedioPagoIn, *, actor: int) -> CatalogoItem:
    clave = _slug(datos.nombre)
    if repository.medio_pago_por_clave(db, clave):
        raise ConflictError("Ya existe un medio de pago equivalente", field="nombre")
    m = repository.crear_medio_pago(db, clave=clave, nombre=datos.nombre)
    registrar_cambio(db, actor=actor, accion="crear", entidad="medio_pago", entidad_id=m.id,
                     despues={"nombre": datos.nombre})
    return CatalogoItem(id=m.id, clave=m.clave, nombre=m.nombre, activo=m.activo)


def set_activo_medio_pago(db: Session, mid: int, activo: bool, *, actor: int) -> CatalogoItem:
    m = repository.medio_pago(db, mid)
    if m is None:
        raise NotFoundError("Medio de pago no encontrado")
    m.activo = activo
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="medio_pago", entidad_id=mid,
                     despues={"activo": activo})
    return CatalogoItem(id=m.id, clave=m.clave, nombre=m.nombre, activo=m.activo)


def listar_condiciones_pago(db: Session, *, solo_activas: bool = False) -> list[CatalogoItem]:
    return [
        CatalogoItem(id=c.id, nombre=c.nombre, dias_credito=c.dias_credito, activo=c.activo)
        for c in repository.condiciones_pago(db, solo_activas=solo_activas)
    ]


def crear_condicion_pago(db: Session, datos: CondicionPagoIn, *, actor: int) -> CatalogoItem:
    existentes = {c.nombre.lower() for c in repository.condiciones_pago(db)}
    if datos.nombre.lower() in existentes:
        raise ConflictError("Ya existe esa condición de pago", field="nombre")
    c = repository.crear_condicion_pago(db, nombre=datos.nombre, dias_credito=datos.dias_credito)
    registrar_cambio(db, actor=actor, accion="crear", entidad="condicion_pago", entidad_id=c.id,
                     despues=datos.model_dump())
    return CatalogoItem(id=c.id, nombre=c.nombre, dias_credito=c.dias_credito, activo=c.activo)


def set_activo_condicion_pago(db: Session, cid: int, activo: bool, *, actor: int) -> CatalogoItem:
    c = repository.condicion_pago(db, cid)
    if c is None:
        raise NotFoundError("Condición de pago no encontrada")
    c.activo = activo
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="condicion_pago", entidad_id=cid,
                     despues={"activo": activo})
    return CatalogoItem(id=c.id, nombre=c.nombre, dias_credito=c.dias_credito, activo=c.activo)


def listar_categorias_gasto(db: Session) -> list[CatalogoItem]:
    return [
        CatalogoItem(id=c.id, nombre=c.nombre, tipo=c.tipo, activo=c.activo)
        for c in repository.categorias_gasto(db)
    ]


def crear_categoria_gasto(db: Session, datos: CategoriaGastoIn, *, actor: int) -> CatalogoItem:
    existentes = {c.nombre.lower() for c in repository.categorias_gasto(db)}
    if datos.nombre.lower() in existentes:
        raise ConflictError("Ya existe una categoría con ese nombre", field="nombre")
    c = repository.crear_categoria_gasto(db, nombre=datos.nombre, tipo=datos.tipo)
    registrar_cambio(db, actor=actor, accion="crear", entidad="categoria_gasto", entidad_id=c.id,
                     despues=datos.model_dump())
    return CatalogoItem(id=c.id, nombre=c.nombre, tipo=c.tipo, activo=c.activo)


def listar_categorias_merma(db: Session, *, causa: str | None = None) -> list[CatalogoItem]:
    return [
        CatalogoItem(id=c.id, nombre=c.nombre, tipo=c.causa, activo=c.activo)
        for c in repository.categorias_merma(db, causa=causa)
    ]


def crear_categoria_merma(db: Session, datos: CategoriaMermaIn, *, actor: int) -> CatalogoItem:
    existentes = {c.nombre.lower() for c in repository.categorias_merma(db)}
    if datos.nombre.lower() in existentes:
        raise ConflictError("Ya existe una categoría de merma con ese nombre", field="nombre")
    c = repository.crear_categoria_merma(db, nombre=datos.nombre, causa=datos.causa)
    registrar_cambio(db, actor=actor, accion="crear", entidad="categoria_merma", entidad_id=c.id,
                     despues=datos.model_dump())
    return CatalogoItem(id=c.id, nombre=c.nombre, tipo=c.causa, activo=c.activo)


def listar_canales_cita(db: Session) -> list[CatalogoItem]:
    return [
        CatalogoItem(id=c.id, clave=c.clave, nombre=c.nombre, activo=c.activo)
        for c in repository.canales_cita(db)
    ]


def set_canales_cita(db: Session, entradas: list[CanalCitaIn], *, actor: int) -> list[CatalogoItem]:
    antes = [c.clave for c in repository.canales_cita(db)]
    for e in entradas:
        repository.upsert_canal(db, clave=e.clave, nombre=e.nombre, activo=e.activo)
    registrar_cambio(db, actor=actor, accion="editar", entidad="canal_cita",
                     antes=antes, despues=[e.model_dump() for e in entradas])
    return listar_canales_cita(db)


# ------------------------------------------------------------------- parámetros
def get_parametro_out(
    db: Session, clave: str, *, ambito_tipo: str = "global", ambito_ref: str | None = None
) -> ParametroOut:
    vig = parametros_repo.vigente(db, clave, ambito_tipo=ambito_tipo, ambito_ref=ambito_ref)
    hist = parametros_repo.historial(db, clave, ambito_tipo=ambito_tipo, ambito_ref=ambito_ref)
    return ParametroOut(
        clave=clave,
        tipo=vig.tipo if vig else "numero",
        valor_vigente=vig.valor if vig else None,
        historial=[
            ParametroHistorialItem(
                valor=h.valor,
                vigente_desde=h.vigente_desde,
                creado_por=str(h.creado_por) if h.creado_por else None,
            )
            for h in hist
        ],
    )


def set_parametro_cmd(db: Session, clave: str, datos: ParametroIn, *, actor: int) -> SetParametroOut:
    anterior, resumen = set_parametro(
        db,
        clave=clave,
        valor=datos.valor,
        tipo=datos.tipo,
        ambito_tipo=datos.ambito_tipo,
        ambito_ref=datos.ambito_ref,
        vigente_desde=datos.vigente_desde,
        actor=actor,
    )
    registrar_cambio(
        db, actor=actor, accion="editar", entidad="parametro_configuracion", entidad_id=clave,
        antes={"valor": anterior}, despues={"valor": datos.valor, "ambito_tipo": datos.ambito_tipo},
    )
    return SetParametroOut(
        clave=clave,
        valor_vigente=datos.valor,
        recalculo=RecalculoOut(
            consumidores=resumen.consumidores,
            entidades_abiertas_afectadas=resumen.entidades_abiertas_afectadas,
            documentos_emitidos_intactos=resumen.documentos_emitidos_intactos,
        ),
    )


# ------------------------------------------------------------------- auditoría
# --- catálogos de la ficha de reloj ---
def _marca_out(m) -> CatalogoItem:
    return CatalogoItem(id=m.id, nombre=m.nombre, activo=m.activo, pais=m.pais,
                        sitio_web=m.sitio_web, nota=m.nota)


def listar_marcas_reloj(db: Session, *, solo_activas: bool = False) -> list[CatalogoItem]:
    return [_marca_out(m) for m in repository.marcas_reloj(db, solo_activas=solo_activas)]


def crear_marca_reloj(db: Session, datos: MarcaRelojIn, *, actor: int) -> CatalogoItem:
    if repository.marca_reloj_por_nombre(db, datos.nombre):
        raise ConflictError("Ya existe esa marca", field="nombre")
    m = repository.crear_marca_reloj(db, nombre=datos.nombre.strip(), pais=datos.pais,
                                     sitio_web=datos.sitio_web, nota=datos.nota)
    registrar_cambio(db, actor=actor, accion="crear", entidad="marca_reloj", entidad_id=m.id,
                     despues=datos.model_dump(exclude_none=True))
    return _marca_out(m)


def actualizar_marca_reloj(db: Session, mid: int, datos: MarcaRelojIn, *, actor: int) -> CatalogoItem:
    m = repository.marca_reloj(db, mid)
    if m is None:
        raise ConflictError("Marca no encontrada")
    m.nombre, m.pais, m.sitio_web, m.nota = datos.nombre.strip(), datos.pais, datos.sitio_web, datos.nota
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="marca_reloj", entidad_id=mid,
                     despues=datos.model_dump(exclude_none=True))
    return _marca_out(m)


def set_activo_marca_reloj(db: Session, mid: int, activo: bool, *, actor: int) -> CatalogoItem:
    m = repository.marca_reloj(db, mid)
    if m is None:
        raise ConflictError("Marca no encontrada")
    m.activo = activo
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="marca_reloj", entidad_id=mid,
                     despues={"activo": activo})
    return _marca_out(m)


def listar_materiales(db: Session, *, solo_activas: bool = False) -> list[CatalogoItem]:
    return [CatalogoItem(id=m.id, nombre=m.nombre, activo=m.activo)
            for m in repository.materiales(db, solo_activas=solo_activas)]


def crear_material(db: Session, datos: MaterialIn, *, actor: int) -> CatalogoItem:
    if repository.material_por_nombre(db, datos.nombre):
        raise ConflictError("Ya existe ese material", field="nombre")
    m = repository.crear_material(db, nombre=datos.nombre.strip())
    registrar_cambio(db, actor=actor, accion="crear", entidad="material", entidad_id=m.id,
                     despues={"nombre": m.nombre})
    return CatalogoItem(id=m.id, nombre=m.nombre, activo=m.activo)


def set_activo_material(db: Session, mid: int, activo: bool, *, actor: int) -> CatalogoItem:
    m = repository.material(db, mid)
    if m is None:
        raise ConflictError("Material no encontrado")
    m.activo = activo
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="material", entidad_id=mid, despues={"activo": activo})
    return CatalogoItem(id=m.id, nombre=m.nombre, activo=m.activo)


def listar_colores(db: Session, *, solo_activas: bool = False) -> list[CatalogoItem]:
    return [CatalogoItem(id=c.id, nombre=c.nombre, hex=c.hex, activo=c.activo)
            for c in repository.colores(db, solo_activas=solo_activas)]


def crear_color(db: Session, datos: ColorIn, *, actor: int) -> CatalogoItem:
    if repository.color_por_nombre(db, datos.nombre):
        raise ConflictError("Ya existe ese color", field="nombre")
    c = repository.crear_color(db, nombre=datos.nombre.strip(), hex=datos.hex)
    registrar_cambio(db, actor=actor, accion="crear", entidad="color", entidad_id=c.id,
                     despues={"nombre": c.nombre, "hex": c.hex})
    return CatalogoItem(id=c.id, nombre=c.nombre, hex=c.hex, activo=c.activo)


def set_activo_color(db: Session, cid: int, activo: bool, *, actor: int) -> CatalogoItem:
    c = repository.color(db, cid)
    if c is None:
        raise ConflictError("Color no encontrado")
    c.activo = activo
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="color", entidad_id=cid, despues={"activo": activo})
    return CatalogoItem(id=c.id, nombre=c.nombre, hex=c.hex, activo=c.activo)


def listar_auditoria(
    db: Session,
    *,
    entidad: str | None,
    actor: int | None,
    desde: datetime | None,
    hasta: datetime | None,
    offset: int,
    limit: int,
) -> tuple[list[AuditoriaItem], int]:
    filas, total = auditoria_repo.listar(
        db, entidad=entidad, actor=actor, desde=desde, hasta=hasta, offset=offset, limit=limit
    )
    return [
        AuditoriaItem(
            id=r.id,
            actor_usuario_id=r.actor_usuario_id,
            actor_nombre=actor_nombre,
            actor_identificacion=actor_identificacion,
            accion=r.accion,
            entidad=r.entidad,
            entidad_id=r.entidad_id,
            antes=r.antes,
            despues=r.despues,
            ip_origen=r.ip_origen,
            creado_en=r.creado_en,
        )
        for r, actor_nombre, actor_identificacion in filas
    ], total
