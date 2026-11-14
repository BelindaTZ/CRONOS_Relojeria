"""Lógica del módulo `clientes` (feature 006).

- CRM básico: alta con `numero_afiliado` autogenerado y **consentimiento LOPDP
  obligatorio**; `identificacion` editable solo con rol elevado.
- **Programa de fidelización**: niveles configurables + `regla_nivel`; motor de
  recálculo del nivel al confirmarse una compra/servicio (`recalcular_nivel`,
  consumido por 008/009); recálculo masivo diferido al cambiar una regla.
- **Descuentos generales y cupones** (§4.8.2), mutuamente excluyentes.
- **Margen mínimo protegido**: la lógica vive en `shared/descuentos`; aquí se
  exponen los endpoints de configuración y de autorización de Gerencia General.
- Reportes operativos: clientes por nivel, mejores clientes, historial de cliente.

Las transacciones (compras 009 + servicios 008) llegan por
`registrar_proveedor_transacciones`; hasta que existan esas features, el motor se
valida con fixtures (Const. Ppio IX).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from clientes import nivel as nivel_mod
from clientes import repository
from clientes.models import Cliente, Cupon
from clientes.schemas import (
    AplicarDescuentoOut,
    ClienteDetalle,
    ClienteOut,
    ClientesPorNivelOut,
    CuponMiniOut,
    CuponOut,
    DescuentoOut,
    HistorialClienteOut,
    MargenMinimoOut,
    MejorClienteOut,
    MovimientoHistorialOut,
    NivelOut,
    ReglaNivelOut,
    RecalcularNivelOut,
    TextoConsentimientoOut,
)
from shared.auditoria import registrar_cambio
from shared.descuentos import BeneficioAplicable, aplicar as _aplicar_descuento
from shared.descuentos import margen_minimo as _mm
from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.guard import CurrentUser
from shared.parametros import get_parametro, set_parametro

logger = logging.getLogger("cronos.clientes")

_ROLES_ELEVADOS = {"Gerencia General", "Gerente de Sucursal"}


class NoAutorizadoError(ConflictError):
    status_code = 403
    code = "no_autorizado"


def es_rol_elevado(user: CurrentUser) -> bool:
    return bool(_ROLES_ELEVADOS & set(getattr(user, "roles", []) or []))


# ===================================================== transacciones (008/009)
@dataclass(frozen=True)
class TransaccionCliente:
    cliente_id: int
    fecha: date
    monto: Decimal
    tipo: str  # "venta" | "servicio"
    documento_id: int | None = None
    detalle: str | None = None
    sucursal_id: int | None = None  # sucursal donde se hizo la compra/servicio (008/009)


ProveedorTransacciones = Callable[[Session, int], "list[TransaccionCliente]"]
_PROVEEDORES_TX: list[ProveedorTransacciones] = []


def registrar_proveedor_transacciones(fn: ProveedorTransacciones) -> None:
    """008 (servicios) y 009 (ventas) registran aquí su fuente de transacciones."""
    _PROVEEDORES_TX.append(fn)


def _transacciones(db: Session, cliente_id: int) -> list[TransaccionCliente]:
    salida: list[TransaccionCliente] = []
    for fn in _PROVEEDORES_TX:
        salida.extend(fn(db, cliente_id) or [])
    return salida


# ===================================================== salida
def _cliente_out(db: Session, c: Cliente) -> ClienteOut:
    niv = repository.nivel(db, c.nivel_fidelizacion_id) if c.nivel_fidelizacion_id else None
    return ClienteOut(
        id=c.id, tipo=c.tipo, identificacion=c.identificacion, numero_afiliado=c.numero_afiliado,
        nombre=c.nombre, telefono=c.telefono, email=c.email, direccion=c.direccion,
        fecha_nacimiento=c.fecha_nacimiento, preferencias=c.preferencias, notas=c.notas,
        nivel_fidelizacion_id=c.nivel_fidelizacion_id, nivel_nombre=niv.nombre if niv else None,
        es_consumidor_final=c.es_consumidor_final, estado=c.estado, creado_en=c.creado_en,
    )


def _cupon_mini(c: Cupon) -> CuponMiniOut:
    return CuponMiniOut(
        id=c.id, codigo=c.codigo, tipo=c.tipo, valor=Decimal(c.valor), alcance=c.alcance,
        vigencia_fin=c.vigencia_fin, estado=c.estado,
    )


# ===================================================== CRUD cliente
def listar(db, *, q, nivel_id, offset, limit):
    filas, total = repository.buscar(
        db, q=q, nivel_id=nivel_id, solo_activos=False, incluir_consumidor_final=False,
        offset=offset, limit=limit,
    )
    return [_cliente_out(db, c) for c in filas], total


def texto_consentimiento(db: Session) -> TextoConsentimientoOut:
    raw = get_parametro(db, "texto_consentimiento_lopdp", default={"version": 1, "texto": ""})
    return TextoConsentimientoOut(version=int(raw.get("version", 1)), texto=str(raw.get("texto", "")))


def crear(db: Session, datos, *, actor: int) -> ClienteDetalle:
    if not datos.consentimiento.aceptado:
        raise ValidationError(
            "Debes registrar la aceptación del consentimiento de tratamiento de datos (LOPDP)",
            field="consentimiento",
        )
    if repository.por_identificacion(db, datos.identificacion.strip()):
        raise ConflictError("Ya existe un cliente con esa cédula/RUC", field="identificacion")

    base = repository.nivel_base(db)
    c = repository.crear(
        db, tipo=datos.tipo, identificacion=datos.identificacion.strip(),
        numero_afiliado=repository.siguiente_afiliado(db), nombre=datos.nombre.strip(),
        telefono=(datos.telefono or "").strip() or None, email=(datos.email or "").strip() or None,
        direccion=(datos.direccion or "").strip() or None, fecha_nacimiento=datos.fecha_nacimiento,
        preferencias=datos.preferencias or None, notas=(datos.notas or "").strip() or None,
        nivel_fidelizacion_id=base.id if base else None, estado="activo",
    )
    repository.agregar_consentimiento(
        db, cliente_id=c.id, aceptado=True, version_texto=datos.consentimiento.version_texto
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="cliente", entidad_id=c.id,
                     despues={"identificacion": c.identificacion, "numero_afiliado": c.numero_afiliado})
    return obtener_detalle(db, c.id)


def actualizar(db: Session, cid: int, datos, *, user: CurrentUser) -> ClienteDetalle:
    c = repository.obtener(db, cid)
    if c is None:
        raise NotFoundError("Cliente no encontrado")
    if c.es_consumidor_final:
        raise ValidationError("El cliente genérico «Consumidor Final» no se edita")

    cambios = datos.model_dump(exclude_unset=True)
    if cambios.get("identificacion") and cambios["identificacion"].strip() != c.identificacion:
        if not es_rol_elevado(user):
            raise NoAutorizadoError("Corregir la cédula/RUC de un cliente requiere rol elevado")
        if repository.por_identificacion(db, cambios["identificacion"].strip()):
            raise ConflictError("Esa cédula/RUC ya está en uso", field="identificacion")

    antes = _cliente_out(db, c).model_dump()
    for campo in ("identificacion", "tipo", "nombre", "telefono", "email", "direccion",
                  "fecha_nacimiento", "preferencias", "notas"):
        if campo in cambios:
            valor = cambios[campo]
            if isinstance(valor, str):
                valor = valor.strip() or None
            setattr(c, campo, valor)
    c.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="editar", entidad="cliente", entidad_id=cid,
                     antes=antes, despues=_cliente_out(db, c).model_dump())
    return obtener_detalle(db, cid)


def set_estado(db: Session, cid: int, estado: str, *, actor: int) -> ClienteOut:
    c = repository.obtener(db, cid)
    if c is None:
        raise NotFoundError("Cliente no encontrado")
    if c.es_consumidor_final:
        raise ValidationError("El cliente genérico «Consumidor Final» no se inactiva")
    c.estado = estado
    c.actualizado_en = datetime.now(timezone.utc)
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="cliente", entidad_id=cid,
                     despues={"estado": estado})
    return _cliente_out(db, c)


def obtener_detalle(db: Session, cid: int) -> ClienteDetalle:
    c = repository.obtener(db, cid)
    if c is None:
        raise NotFoundError("Cliente no encontrado")
    niv = repository.nivel(db, c.nivel_fidelizacion_id) if c.nivel_fidelizacion_id else None
    cons = repository.consentimiento_vigente(db, cid)
    base = _cliente_out(db, c).model_dump()
    return ClienteDetalle(
        **base,
        cupones_activos=[_cupon_mini(x) for x in repository.cupones_activos_de(db, cid)],
        beneficios_nivel=niv.beneficios if niv else None,
        consentimiento_vigente=(
            {"aceptado": cons.aceptado, "version_texto": cons.version_texto} if cons else None
        ),
    )


# ===================================================== niveles
def _regla_out(r) -> ReglaNivelOut:
    return ReglaNivelOut(
        id=r.id, criterio=r.criterio, ventana_meses=r.ventana_meses,
        umbral_monto=r.umbral_monto, umbral_frecuencia=r.umbral_frecuencia,
        vigente_desde=r.vigente_desde,
    )


def _nivel_out(db, n) -> NivelOut:
    conteo = repository.contar_clientes_por_nivel(db)
    r = repository.regla_vigente(db, n.id)
    return NivelOut(
        id=n.id, nombre=n.nombre, orden=n.orden, beneficios=n.beneficios, es_base=n.es_base,
        activo=n.activo, regla_vigente=_regla_out(r) if r else None,
        clientes=conteo.get(n.id, 0),
    )


def listar_niveles(db: Session) -> list[NivelOut]:
    return [_nivel_out(db, n) for n in repository.niveles(db, solo_activos=False)]


def crear_nivel(db: Session, datos, *, actor: int) -> NivelOut:
    if repository.por_nombre_nivel(db, datos.nombre):
        raise ConflictError("Ya existe un nivel con ese nombre", field="nombre")
    if datos.es_base and repository.nivel_base(db):
        raise ConflictError("Ya hay un nivel base definido")
    n = repository.crear_nivel(
        db, nombre=datos.nombre.strip(), orden=datos.orden, beneficios=datos.beneficios or {},
        es_base=datos.es_base, activo=True,
    )
    if datos.regla and not datos.es_base:
        repository.agregar_regla(
            db, nivel_fidelizacion_id=n.id, criterio=datos.regla.criterio,
            ventana_meses=datos.regla.ventana_meses, umbral_monto=datos.regla.umbral_monto,
            umbral_frecuencia=datos.regla.umbral_frecuencia, vigente_desde=date.today(), creado_por=actor,
        )
    registrar_cambio(db, actor=actor, accion="crear", entidad="nivel_fidelizacion", entidad_id=n.id,
                     despues={"nombre": n.nombre, "orden": n.orden})
    recalcular_masivo(db, motivo="nivel_nuevo")
    return _nivel_out(db, n)


def set_regla_nivel(db: Session, nivel_id: int, datos, *, actor: int) -> NivelOut:
    n = repository.nivel(db, nivel_id)
    if n is None:
        raise NotFoundError("Nivel no encontrado")
    if n.es_base:
        raise ValidationError("El nivel base no lleva regla de umbral")
    repository.agregar_regla(
        db, nivel_fidelizacion_id=nivel_id, criterio=datos.criterio,
        ventana_meses=datos.ventana_meses, umbral_monto=datos.umbral_monto,
        umbral_frecuencia=datos.umbral_frecuencia, vigente_desde=date.today(), creado_por=actor,
    )
    registrar_cambio(db, actor=actor, accion="editar", entidad="regla_nivel", entidad_id=nivel_id,
                     despues=datos.model_dump(mode="json"))
    afectados = recalcular_masivo(db, motivo="regla_nivel")
    logger.info("regla de nivel %s cambiada → recálculo masivo: %d clientes", nivel_id, afectados)
    return _nivel_out(db, n)


# ===================================================== motor de nivel
def _niveles_regla(db: Session) -> list[nivel_mod.NivelRegla]:
    out = []
    for n in repository.niveles(db, solo_activos=True):
        r = repository.regla_vigente(db, n.id)
        out.append(nivel_mod.NivelRegla(
            nivel_id=n.id, orden=n.orden, es_base=n.es_base,
            criterio=r.criterio if r else None,
            ventana_meses=r.ventana_meses if r else 12,
            umbral_monto=Decimal(str(r.umbral_monto)) if r and r.umbral_monto is not None else None,
            umbral_frecuencia=r.umbral_frecuencia if r else None,
        ))
    return out


def _nivel_calculado(db: Session, cliente_id: int) -> int | None:
    txs = [
        nivel_mod.TransaccionInfo(fecha=t.fecha, monto=Decimal(str(t.monto)), tipo=t.tipo)
        for t in _transacciones(db, cliente_id)
    ]
    return nivel_mod.calcular_nivel(txs, _niveles_regla(db))


def recalcular_nivel(
    db: Session, *, cliente_id: int, hecho: str = "recalculo_masivo", documento_id: int | None = None,
) -> RecalcularNivelOut:
    c = repository.obtener(db, cliente_id, for_update=True)
    if c is None:
        raise NotFoundError("Cliente no encontrado")
    if c.es_consumidor_final:
        return RecalcularNivelOut(cliente_id=cliente_id, cambio=False)

    anterior_id = c.nivel_fidelizacion_id
    nuevo_id = _nivel_calculado(db, cliente_id)
    anterior = repository.nivel(db, anterior_id) if anterior_id else None
    nuevo = repository.nivel(db, nuevo_id) if nuevo_id else None

    if nuevo_id == anterior_id:
        return RecalcularNivelOut(
            cliente_id=cliente_id,
            nivel_anterior=anterior.nombre if anterior else None,
            nivel_nuevo=nuevo.nombre if nuevo else None,
            cambio=False,
        )

    c.nivel_fidelizacion_id = nuevo_id
    c.actualizado_en = datetime.now(timezone.utc)
    repository.registrar_cambio_nivel(
        db, cliente_id=cliente_id, nivel_anterior_id=anterior_id, nivel_nuevo_id=nuevo_id,
        hecho_disparador=hecho, documento_id=documento_id,
    )
    db.flush()

    # feature 014: aviso automático solo en ASCENSO (nunca en descenso silencioso
    # — spec US2, "cuando el cliente asciende... recibe un email con los
    # beneficios del nuevo nivel"). El envío se encola, nunca bloquea el recálculo.
    if nuevo and (not anterior or nuevo.orden > anterior.orden):
        try:
            from notificaciones import encolar

            beneficios = nuevo.beneficios or {}
            encolar(
                db, tipo="nivel", disparo_origen_tipo="nivel_cliente", disparo_origen_id=cliente_id,
                hito=nuevo.nombre, cliente_id=cliente_id,
                contexto={
                    "cliente_nombre": c.nombre, "nivel_nombre": nuevo.nombre,
                    "beneficios": list(beneficios.values()) if isinstance(beneficios, dict) else beneficios,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("no se encoló el aviso de ascenso de nivel (cliente %s): %s", cliente_id, exc)

    return RecalcularNivelOut(
        cliente_id=cliente_id,
        nivel_anterior=anterior.nombre if anterior else None,
        nivel_nuevo=nuevo.nombre if nuevo else None,
        cambio=True,
    )


def recalcular_masivo(db: Session, *, motivo: str) -> int:
    """Job diferido: reclasifica a todos los clientes activos; el historial previo se conserva."""
    n = 0
    for c in repository.todos_activos(db):
        r = recalcular_nivel(db, cliente_id=c.id, hecho="recalculo_masivo")
        if r.cambio:
            n += 1
    logger.info("recálculo masivo de niveles (%s): %d clientes cambiaron", motivo, n)
    return n


# ===================================================== descuentos
def _descuento_out(d) -> DescuentoOut:
    return DescuentoOut(
        id=d.id, nombre=d.nombre, tipo=d.tipo, valor=Decimal(d.valor), alcance=d.alcance,
        alcance_ref=d.alcance_ref, segmento=d.segmento, segmento_ref=d.segmento_ref,
        vigencia_inicio=d.vigencia_inicio, vigencia_fin=d.vigencia_fin, evento=d.evento,
        limite_uso=d.limite_uso, max_usos=d.max_usos, usos=d.usos, estado=d.estado,
    )


def listar_descuentos(db: Session) -> list[DescuentoOut]:
    return [_descuento_out(d) for d in repository.listar_descuentos(db)]


def crear_descuento(db: Session, datos, *, actor: int) -> DescuentoOut:
    if datos.tipo == "porcentaje" and Decimal(str(datos.valor)) > 1:
        raise ValidationError("Un descuento porcentual se expresa como fracción (0,10 = 10 %)", field="valor")
    d = repository.crear_descuento(
        db, nombre=datos.nombre.strip(), tipo=datos.tipo, valor=datos.valor,
        alcance=datos.alcance, alcance_ref=datos.alcance_ref, segmento=datos.segmento,
        segmento_ref=datos.segmento_ref, vigencia_inicio=datos.vigencia_inicio,
        vigencia_fin=datos.vigencia_fin, evento=datos.evento, limite_uso=datos.limite_uso,
        max_usos=datos.max_usos, estado="activo", creado_por=actor,
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="descuento", entidad_id=d.id,
                     despues={"nombre": d.nombre, "tipo": d.tipo})
    return _descuento_out(d)


def actualizar_descuento(db: Session, did: int, datos, *, actor: int) -> DescuentoOut:
    d = repository.obtener_descuento(db, did)
    if d is None:
        raise NotFoundError("Descuento no encontrado")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(d, campo, valor.strip() if isinstance(valor, str) else valor)
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="descuento", entidad_id=did,
                     despues=datos.model_dump(exclude_unset=True, mode="json"))
    return _descuento_out(d)


# ===================================================== cupones
def _cupon_out(db, c) -> CuponOut:
    cli = repository.obtener(db, c.cliente_id)
    return CuponOut(
        id=c.id, codigo=c.codigo, cliente_id=c.cliente_id, tipo=c.tipo, valor=Decimal(c.valor),
        alcance=c.alcance, alcance_ref=c.alcance_ref, vigencia_inicio=c.vigencia_inicio,
        vigencia_fin=c.vigencia_fin, evento=c.evento, limite_uso=c.limite_uso, max_usos=c.max_usos,
        usos=c.usos, estado=c.estado, cliente_nombre=cli.nombre if cli else None,
    )


def listar_cupones(db: Session, *, cliente_id, estado) -> list[CuponOut]:
    return [_cupon_out(db, c) for c in repository.listar_cupones(db, cliente_id=cliente_id, estado=estado)]


def crear_cupon(db: Session, datos, *, actor: int) -> CuponOut:
    if repository.cupon_por_codigo(db, datos.codigo.strip()):
        raise ConflictError("Ya existe un cupón con ese código", field="codigo")
    cli = repository.obtener(db, datos.cliente_id)
    if cli is None or cli.es_consumidor_final:
        raise ValidationError("El cupón debe asignarse a un cliente registrado", field="cliente_id")
    if datos.tipo == "porcentaje" and Decimal(str(datos.valor)) > 1:
        raise ValidationError("Un cupón porcentual se expresa como fracción (0,10 = 10 %)", field="valor")
    c = repository.crear_cupon(
        db, codigo=datos.codigo.strip().upper(), cliente_id=datos.cliente_id, tipo=datos.tipo,
        valor=datos.valor, alcance=datos.alcance, alcance_ref=datos.alcance_ref,
        vigencia_inicio=datos.vigencia_inicio, vigencia_fin=datos.vigencia_fin, evento=datos.evento,
        limite_uso=datos.limite_uso, max_usos=datos.max_usos, estado="activo", creado_por=actor,
    )
    registrar_cambio(db, actor=actor, accion="crear", entidad="cupon", entidad_id=c.id,
                     despues={"codigo": c.codigo, "cliente_id": c.cliente_id})
    _avisar_cupon(db, c, cliente_nombre=cli.nombre)
    return _cupon_out(db, c)


def _avisar_cupon(db: Session, c: Cupon, *, cliente_nombre: str) -> None:
    """feature 014, US2: aviso automático al emitir un cupón (encolado, nunca
    bloquea la creación del cupón — el cupón se crea igual aunque falle)."""
    try:
        from notificaciones import encolar

        descripcion = f"{c.valor * 100:.0f}% de descuento" if c.tipo == "porcentaje" else f"${c.valor} de descuento"
        encolar(
            db, tipo="cupon", disparo_origen_tipo="cupon", disparo_origen_id=c.id, hito=c.codigo,
            cliente_id=c.cliente_id,
            contexto={
                "cliente_nombre": cliente_nombre, "codigo": c.codigo, "descripcion": descripcion,
                "vigencia_fin": c.vigencia_fin.isoformat() if c.vigencia_fin else "sin vencimiento",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("no se encoló el aviso de cupón %s: %s", c.id, exc)


def _limite_alcanzado(c: Cupon) -> bool:
    if c.limite_uso == "una_vez":
        return c.usos >= 1
    if c.limite_uso in ("n_veces", "global", "por_cliente"):
        return c.max_usos is not None and c.usos >= c.max_usos
    return False


def consumir_cupon(db: Session, *, codigo: str, documento_tipo: str, documento_id: int, actor: int | None = None) -> CuponOut:
    c = repository.cupon_por_codigo(db, codigo.strip().upper(), for_update=True)
    if c is None:
        raise NotFoundError("Cupón no encontrado")
    hoy = date.today()
    if c.estado == "usado":
        raise ConflictError("El cupón ya fue usado", field="codigo")
    if c.estado == "vencido" or (c.vigencia_fin and hoy > c.vigencia_fin):
        c.estado = "vencido"
        db.flush()
        raise ConflictError("El cupón está vencido", field="codigo")
    if c.vigencia_inicio and hoy < c.vigencia_inicio:
        raise ConflictError("El cupón aún no está vigente", field="codigo")
    if _limite_alcanzado(c):
        raise ConflictError("El cupón alcanzó su límite de uso", field="codigo")

    c.usos += 1
    if c.limite_uso == "una_vez" or _limite_alcanzado(c):
        c.estado = "usado"
    db.flush()
    registrar_cambio(db, actor=actor, accion="editar", entidad="cupon", entidad_id=c.id,
                     despues={"consumido_en": f"{documento_tipo}#{documento_id}", "usos": c.usos})
    return _cupon_out(db, c)


# ===================================================== margen mínimo
def get_margen_minimo(db: Session, *, ambito: str = "global", ref: str | None = None) -> MargenMinimoOut:
    mm = _mm.vigente(db, marca=ref if ambito == "marca" else None, item_ref=ref if ambito == "producto" else None)
    return MargenMinimoOut(tipo=mm.tipo, valor=mm.valor, ambito=mm.ambito, ref=mm.ref, politica=mm.politica)


def set_margen_minimo(db: Session, datos, *, actor: int) -> MargenMinimoOut:
    if datos.tipo == "porcentaje_costo" and Decimal(str(datos.valor)) > 1:
        raise ValidationError("El margen mínimo porcentual se expresa como fracción (0,15 = 15 %)", field="valor")
    ambito_tipo = datos.ambito
    ambito_ref = None if datos.ambito == "global" else (datos.ref or None)
    if datos.ambito != "global" and not ambito_ref:
        raise ValidationError("Indica la marca o el producto del ámbito", field="ref")
    anterior, resumen = set_parametro(
        db, clave="margen_minimo", valor={"tipo": datos.tipo, "valor": float(datos.valor)},
        tipo="json", ambito_tipo=ambito_tipo, ambito_ref=ambito_ref, actor=actor,
    )
    if datos.politica:
        set_parametro(db, clave="margen_minimo_politica", valor=datos.politica, tipo="texto", actor=actor)
    registrar_cambio(db, actor=actor, accion="editar", entidad="parametro_configuracion",
                     entidad_id=f"margen_minimo:{ambito_tipo}:{ambito_ref or 'global'}",
                     antes=anterior, despues={"tipo": datos.tipo, "valor": float(datos.valor)})
    return get_margen_minimo(db, ambito=datos.ambito, ref=ambito_ref)


def aplicar_descuento(db: Session, datos) -> AplicarDescuentoOut:
    d = BeneficioAplicable(tipo=datos.descuento.tipo, valor=datos.descuento.valor) if datos.descuento else None
    cp = BeneficioAplicable(tipo=datos.cupon.tipo, valor=datos.cupon.valor) if datos.cupon else None
    r = _aplicar_descuento(
        db, item_ref=datos.item_ref, costo=datos.costo, precio_lista=datos.precio_lista,
        marca=datos.marca, descuento=d, cupon=cp,
    )
    return AplicarDescuentoOut(
        precio_final=r.precio_final, monto_descontado=r.monto_descontado,
        margen_resultante=r.margen_resultante, decision=r.decision,
        margen_minimo_aplicado=MargenMinimoOut(
            tipo=r.margen_minimo.tipo, valor=r.margen_minimo.valor,
            ambito=r.margen_minimo.ambito, ref=r.margen_minimo.ref, politica=r.margen_minimo.politica,
        ),
    )


def autorizar_margen_minimo(db: Session, datos, *, user: CurrentUser):
    if "Gerencia General" not in set(user.roles or []):
        raise NoAutorizadoError("Solo Gerencia General autoriza saltar el margen mínimo protegido")
    from clientes.models import AutorizacionMargenMinimo

    a = AutorizacionMargenMinimo(
        documento_tipo=datos.documento_tipo, documento_id=datos.documento_id,
        autorizador_usuario_id=user.id, margen_resultante=datos.margen_resultante,
        motivo=datos.motivo.strip(),
    )
    db.add(a)
    db.flush()
    registrar_cambio(db, actor=user.id, accion="autorizar", entidad="autorizacion_margen_minimo",
                     entidad_id=a.id,
                     despues={"documento": f"{datos.documento_tipo}#{datos.documento_id}", "motivo": datos.motivo.strip()})
    return {"id": a.id, "documento_tipo": a.documento_tipo, "documento_id": a.documento_id,
            "autorizador_usuario_id": a.autorizador_usuario_id, "fecha": a.fecha.isoformat()}


# ===================================================== reportes
def clientes_por_nivel(db: Session) -> list[ClientesPorNivelOut]:
    conteo = repository.contar_clientes_por_nivel(db)
    salida = []
    for n in repository.niveles(db, solo_activos=False):
        salida.append(ClientesPorNivelOut(nivel_id=n.id, nivel_nombre=n.nombre, clientes=conteo.get(n.id, 0)))
    if conteo.get(None):
        salida.append(ClientesPorNivelOut(nivel_id=None, nivel_nombre="Sin nivel", clientes=conteo[None]))
    return salida


def _sucursal_nombre(db: Session, sid: int | None) -> str | None:
    if not sid:
        return None
    from shared.models import Sucursal

    s = db.get(Sucursal, sid)
    return s.nombre if s else f"#{sid}"


def clientes_en_riesgo(db: Session) -> list["ClienteEnRiesgoOut"]:
    """Clientes de nivel con valor (no base) cuyo patrón propio de compra indica un
    silencio anómalo — candidatos a cupón de reactivación (§4.8.2)."""
    from clientes import riesgo as _riesgo
    from clientes.schemas import ClienteEnRiesgoOut

    piso = int(get_parametro(db, "churn_piso_dias", default=90) or 90)
    factor = float(get_parametro(db, "churn_factor_cadencia", default=2) or 2)
    min_tx = int(get_parametro(db, "churn_min_transacciones", default=3) or 3)
    ventana = int(get_parametro(db, "churn_ventana_analisis_meses", default=24) or 24)

    niveles_valor = {n.id for n in repository.niveles(db, solo_activos=True) if not n.es_base}
    hoy = date.today()
    salida: list[ClienteEnRiesgoOut] = []
    for c in repository.todos_activos(db):
        if c.nivel_fidelizacion_id not in niveles_valor:
            continue
        txs = [_riesgo.TransaccionRiesgo(fecha=t.fecha) for t in _transacciones(db, c.id)]
        r = _riesgo.analizar(
            txs, hoy=hoy, piso_dias=piso, factor_cadencia=factor,
            min_transacciones=min_tx, ventana_meses=ventana,
        )
        if r is None:
            continue
        niv = repository.nivel(db, c.nivel_fidelizacion_id)
        salida.append(ClienteEnRiesgoOut(
            cliente_id=c.id, nombre=c.nombre, numero_afiliado=c.numero_afiliado,
            nivel_nombre=niv.nombre if niv else None,
            ultima_compra=r.ultima_fecha, dias_silencio=r.dias_silencio,
            cadencia_dias=r.cadencia_dias, ratio=r.ratio, severidad=r.severidad,
            transacciones=r.n_transacciones,
        ))
    salida.sort(key=lambda x: x.ratio, reverse=True)
    return salida


def emitir_cupon_reactivacion(db: Session, datos, *, actor: int) -> "CuponOut":
    """Emite un cupón puntual de reactivación para un cliente en riesgo (acción del reporte)."""
    from datetime import timedelta

    from clientes.schemas import CuponIn

    c = repository.obtener(db, datos.cliente_id)
    if c is None or c.es_consumidor_final:
        raise ValidationError("El cupón debe asignarse a un cliente registrado", field="cliente_id")
    codigo = (datos.codigo or f"REACT-{c.numero_afiliado.split('-')[-1]}").strip().upper()
    vig = datos.vigencia_fin or (date.today() + timedelta(days=60))
    return crear_cupon(db, CuponIn(
        codigo=codigo, cliente_id=datos.cliente_id, tipo=datos.tipo, valor=datos.valor,
        alcance="tienda", limite_uso="una_vez", vigencia_fin=vig,
    ), actor=actor)


def mejores_clientes(db: Session, *, top: int, desde: date | None) -> list[MejorClienteOut]:
    filas = []
    for c in repository.todos_activos(db):
        txs = _transacciones(db, c.id)
        if desde:
            txs = [t for t in txs if t.fecha >= desde]
        compras = sum((Decimal(str(t.monto)) for t in txs if t.tipo == "venta"), Decimal("0"))
        servicios = sum((Decimal(str(t.monto)) for t in txs if t.tipo == "servicio"), Decimal("0"))
        total = compras + servicios
        if total > 0:
            filas.append(MejorClienteOut(
                cliente_id=c.id, nombre=c.nombre, numero_afiliado=c.numero_afiliado,
                total_compras=compras, total_servicios=servicios, total=total,
            ))
    filas.sort(key=lambda x: x.total, reverse=True)
    return filas[:top]


def historial_cliente(db: Session, cliente_id: int) -> HistorialClienteOut:
    c = repository.obtener(db, cliente_id)
    if c is None:
        raise NotFoundError("Cliente no encontrado")
    txs = _transacciones(db, cliente_id)
    movimientos = [
        MovimientoHistorialOut(
            tipo="compra" if t.tipo == "venta" else "servicio",
            fecha=datetime(t.fecha.year, t.fecha.month, t.fecha.day, tzinfo=timezone.utc),
            detalle=t.detalle or ("Compra" if t.tipo == "venta" else "Servicio técnico"),
            monto=Decimal(str(t.monto)), documento_id=t.documento_id,
            sucursal_id=t.sucursal_id, sucursal_nombre=_sucursal_nombre(db, t.sucursal_id),
        )
        for t in sorted(txs, key=lambda x: x.fecha, reverse=True)
    ]
    cambios = [
        {
            "fecha": h.fecha.isoformat(),
            "nivel_anterior_id": h.nivel_anterior_id, "nivel_nuevo_id": h.nivel_nuevo_id,
            "hecho": h.hecho_disparador, "documento_id": h.documento_id,
        }
        for h in repository.historial_nivel(db, cliente_id)
    ]
    return HistorialClienteOut(
        cliente_id=cliente_id,
        total_compras=sum((m.monto for m in movimientos if m.tipo == "compra"), Decimal("0")),
        total_servicios=sum((m.monto for m in movimientos if m.tipo == "servicio"), Decimal("0")),
        movimientos=movimientos, cambios_nivel=cambios,
    )


# ===================================================== consumidores 001
_consumidores_registrados = False


def _recalcular_por_parametro(db: Session, clave: str) -> int:
    """`margen_minimo` cambió → recálculo de operaciones abiertas (008/009 aún no existen)."""
    logger.info("parámetro %s cambiado — 008/009 recalcularán sus operaciones abiertas cuando existan", clave)
    return 0


def registrar_consumidores() -> None:
    global _consumidores_registrados
    if _consumidores_registrados:
        return
    from shared.parametros import registrar_consumidor

    registrar_consumidor("margen_minimo", _recalcular_por_parametro, nombre="clientes.recalculo_margen")
    _consumidores_registrados = True


# ===================================================== API pública (007/008/009)
def cliente_mini(db: Session, cliente_id: int) -> dict | None:
    c = repository.obtener(db, cliente_id)
    if c is None:
        return None
    niv = repository.nivel(db, c.nivel_fidelizacion_id) if c.nivel_fidelizacion_id else None
    return {
        "id": c.id, "nombre": c.nombre, "identificacion": c.identificacion,
        "numero_afiliado": c.numero_afiliado, "es_consumidor_final": c.es_consumidor_final,
        "nivel_id": c.nivel_fidelizacion_id, "nivel_nombre": niv.nombre if niv else None,
        "beneficios_nivel": niv.beneficios if niv else None,
        "email": c.email, "telefono": c.telefono, "direccion": c.direccion,
    }


def id_consumidor_final(db: Session) -> int | None:
    c = repository.consumidor_final(db)
    return c.id if c else None


def cupon_datos(db: Session, codigo: str) -> dict | None:
    """Público (009): tipo/valor/cliente de un cupón para previsualizar el descuento
    (el consumo con lock sigue siendo `consumir_cupon`)."""
    c = repository.cupon_por_codigo(db, (codigo or "").strip().upper())
    if c is None:
        return None
    return {"codigo": c.codigo, "cliente_id": c.cliente_id, "tipo": c.tipo,
            "valor": Decimal(c.valor), "alcance": c.alcance, "estado": c.estado}


def descuento_por_id(db: Session, descuento_id: int) -> dict | None:
    """Público (009): datos de un descuento general vigente para aplicarlo a una venta."""
    d = repository.obtener_descuento(db, descuento_id)
    if d is None or d.estado != "activo":
        return None
    return {"id": d.id, "nombre": d.nombre, "tipo": d.tipo, "valor": Decimal(d.valor),
            "alcance": d.alcance, "alcance_ref": d.alcance_ref}


def autorizacion_por_id(db: Session, autorizacion_id: int) -> dict | None:
    """Público (008): datos de una autorización de Gerencia General (crédito / salto de
    margen mínimo) para vincularla a una OT o venta."""
    from clientes.models import AutorizacionMargenMinimo

    a = db.get(AutorizacionMargenMinimo, autorizacion_id)
    if a is None:
        return None
    return {
        "id": a.id, "documento_tipo": a.documento_tipo, "documento_id": a.documento_id,
        "autorizador_usuario_id": a.autorizador_usuario_id,
        "margen_resultante": a.margen_resultante, "motivo": a.motivo,
    }


def ids_por_texto(db: Session, q: str) -> list[int]:
    """Ids de clientes que coinciden con `q` (nombre, cédula/RUC, email, teléfono, afiliado).
    Lo usan otros módulos (007 citas) para buscar por cliente sin acoplarse a esta tabla."""
    if not q or not q.strip():
        return []
    filas, _ = repository.buscar(
        db, q=q, nivel_id=None, solo_activos=False, incluir_consumidor_final=False,
        offset=0, limit=200,
    )
    return [c.id for c in filas]
