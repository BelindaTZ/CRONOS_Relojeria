"""Router del módulo `notificaciones` (feature 014). Solo HTTP (Ppio X)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from notificaciones import service
from notificaciones.schemas import (
    EncolarIn,
    EnvioOut,
    PlantillaDetalleOut,
    PlantillaIn,
    PlantillaOut,
    PreferenciaIn,
    PreferenciaOut,
    PreviewIn,
    PreviewOut,
)
from shared.database import get_db
from shared.guard import CurrentUser, get_current_user_full_scope, require_gerencia_o_delegado, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["notificaciones"])
internal_router = APIRouter(prefix="/_internal", tags=["_internal"])

_leer = require_perm("notificaciones", "consultar")
_plantillas = require_gerencia_o_delegado


@router.get("/envios", response_model=Page[EnvioOut])
def listar_envios(
    tipo: str | None = None,
    estado: str | None = None,
    cliente_id: int | None = None,
    disparo_origen_id: int | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    items, total = service.listar(
        db, tipo=tipo, estado=estado, cliente_id=cliente_id, disparo_origen_id=disparo_origen_id,
        offset=pp.offset, limit=pp.limit,
    )
    return {"items": items, "total": total, "page": pp.page, "size": pp.size}


@router.post("/envios/{envio_id}/reintentar", response_model=EnvioOut, status_code=status.HTTP_202_ACCEPTED)
def reintentar_envio(envio_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    envio = service.reintentar(db, envio_id, user=user)
    db.commit()
    return envio


@router.get("/preferencias/cliente/{cliente_id}", response_model=list[PreferenciaOut])
def get_preferencias(cliente_id: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.get_preferencias(db, cliente_id)


@router.put("/preferencias/cliente/{cliente_id}", response_model=PreferenciaOut)
def set_preferencia(cliente_id: int, datos: PreferenciaIn, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    r = service.set_preferencia(db, cliente_id, datos.tipo_comunicacion, datos.opt_in)
    db.commit()
    return r


@router.get("/plantillas", response_model=list[PlantillaOut])
def listar_plantillas(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_plantillas(db)


@router.get("/plantillas/{tipo}", response_model=PlantillaDetalleOut)
def get_plantilla(tipo: str, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.get_plantilla(db, tipo)


@router.put("/plantillas/{tipo}", response_model=PlantillaOut)
def set_plantilla(tipo: str, datos: PlantillaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_plantillas)):
    r = service.set_plantilla(db, tipo, asunto=datos.asunto, cuerpo=datos.cuerpo, user=user)
    db.commit()
    return r


@router.post("/plantillas/{tipo}/preview", response_model=PreviewOut)
def preview_plantilla(tipo: str, datos: PreviewIn, _: CurrentUser = Depends(_plantillas)):
    return service.preview_plantilla(tipo, datos.contexto)


@router.get("/reportes/envios", response_model=Page[EnvioOut])
def reporte_envios(
    tipo: str | None = None,
    estado: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    items, total = service.listar(db, tipo=tipo, estado=estado, cliente_id=None, disparo_origen_id=None, offset=pp.offset, limit=pp.limit)
    return {"items": items, "total": total, "page": pp.page, "size": pp.size}


@router.post("/webhooks/email", status_code=status.HTTP_204_NO_CONTENT)
async def webhook_email(request: Request, db: Session = Depends(get_db)):
    """Eventos de entrega de SendGrid. Sin autenticación de usuario (contrato) —
    NOTA de seguridad documentada en CONVENCIONES §27: aún no valida la firma
    ECDSA del Event Webhook de SendGrid (requiere una clave de firma que el
    negocio no ha configurado todavía); mientras tanto, el peor caso es que un
    tercero pueda marcar un envío propio como entregado/rebotado — nunca
    escribe sobre datos operativos ni dispara un envío nuevo."""
    eventos = await request.json()
    if isinstance(eventos, dict):
        eventos = [eventos]
    service.procesar_webhook(db, eventos)


@internal_router.post("/notificaciones/encolar", status_code=status.HTTP_202_ACCEPTED)
def encolar_notificacion(datos: EncolarIn, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user_full_scope)):
    """Uso operativo/pruebas: en producción, 001/006/007/008 llaman
    `notificaciones.encolar()` directo en Python (mismo patrón que el resto de
    las integraciones entre módulos de este backend — Ppio X), no por HTTP."""
    envio = service.encolar(
        db, tipo=datos.tipo, disparo_origen_tipo=datos.disparo_origen_tipo, disparo_origen_id=datos.disparo_origen_id,
        hito=datos.hito, contexto=datos.contexto, cliente_id=datos.cliente_id, usuario_id=datos.usuario_id,
        destinatario_email=datos.destinatario_email, programar_para=datos.programar_para,
    )
    db.commit()
    return {"envio_id": envio.id, "estado": envio.estado}


@internal_router.post("/notificaciones/scheduler/tick")
def scheduler_tick(db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user_full_scope)):
    """Fuerza una corrida del worker (pruebas / operación) — mismo patrón que
    `proveedores`/`contabilidad`."""
    recordatorios = service.generar_recordatorios_cita(db)
    procesados = service.procesar_cola(db)
    return {"recordatorios_generados": recordatorios, "procesados": procesados}
