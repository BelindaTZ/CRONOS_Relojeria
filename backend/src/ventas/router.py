from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.guard import CurrentUser, require_gerencia_o_delegado, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page
from ventas import service
from ventas.schemas import (
    AnularVentaIn,
    ConfigFacturacionIn,
    ConfigFacturacionOut,
    ConfirmarVentaIn,
    CuentaPorCobrarOut,
    DescuentoAplicadoOut,
    DescuentoVentaIn,
    EnviarFacturaOut,
    GarantiaVentaOut,
    PagoRegistradoOut,
    PagoVentaIn,
    PuntoEmisionIn,
    PuntoEmisionOut,
    VentaDetalle,
    VentaIn,
    VentaOut,
    VentasDiaOut,
)

router = APIRouter(tags=["ventas"])

_leer = require_perm("ventas", "consultar")
_crear = require_perm("ventas", "crear")
_editar = require_perm("ventas", "editar")


@router.get("/ventas", response_model=Page[VentaOut])
def listar(
    q: str | None = None,
    estado: str | None = None,
    cliente_id: int | None = None,
    sucursal_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    items, total = service.listar(
        db, user=user, q=q, estado=estado, cliente_id=cliente_id, sucursal_id=sucursal_id,
        desde=desde, hasta=hasta, offset=pp.offset, limit=pp.limit,
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.get("/ventas-dia", response_model=VentasDiaOut)
def ventas_dia(
    fecha: date | None = None,
    sucursal_id: int | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    return service.ventas_dia(db, user=user, fecha=fecha, sucursal_id=sucursal_id)


@router.get("/cuentas-por-cobrar", response_model=list[CuentaPorCobrarOut])
def cuentas_por_cobrar(
    cliente_id: int | None = None,
    estado: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.cuentas_por_cobrar(db, cliente_id=cliente_id, estado=estado)


@router.post("/ventas", response_model=VentaDetalle, status_code=status.HTTP_201_CREATED)
def crear(datos: VentaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_venta(db, datos, user=user)


@router.get("/ventas/{vid}", response_model=VentaDetalle)
def detalle(vid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.obtener_detalle(db, vid, user=user)


@router.post("/ventas/{vid}/descuento", response_model=DescuentoAplicadoOut)
def descuento(vid: int, datos: DescuentoVentaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.aplicar_descuento(db, vid, datos, user=user)


@router.post("/ventas/{vid}/pagos", response_model=PagoRegistradoOut, status_code=status.HTTP_201_CREATED)
def pago(vid: int, datos: PagoVentaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_pago_venta(db, vid, datos, user=user)


@router.post("/ventas/{vid}/confirmar", response_model=VentaDetalle)
def confirmar(vid: int, datos: ConfirmarVentaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.confirmar_venta(db, vid, datos, user=user)


@router.post("/ventas/{vid}/anular", response_model=VentaOut)
def anular(vid: int, datos: AnularVentaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.anular_venta(db, vid, datos, user=user)


@router.get("/ventas/{vid}/garantias", response_model=list[GarantiaVentaOut])
def garantias(vid: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.garantias(db, vid)


@router.get("/ventas/{vid}/comprobantes")
def comprobantes(vid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.comprobantes_urls(db, vid, user=user)


@router.post("/ventas/{vid}/enviar-factura", response_model=EnviarFacturaOut)
def enviar_factura(vid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.enviar_factura_correo(db, vid, user=user)


# --------------------------------------------------------------- configuración de facturación (Gerencia)
@router.get("/facturacion/emisor", response_model=ConfigFacturacionOut)
def get_emisor(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.get_config_facturacion(db)


@router.put("/facturacion/emisor", response_model=ConfigFacturacionOut)
def set_emisor(datos: ConfigFacturacionIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)):
    return service.set_config_facturacion(db, datos, actor=user.id)


@router.get("/facturacion/puntos-emision", response_model=list[PuntoEmisionOut])
def listar_puntos(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_puntos_emision(db)


@router.put("/facturacion/puntos-emision/{sucursal_id}", response_model=PuntoEmisionOut)
def set_punto(sucursal_id: int, datos: PuntoEmisionIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_gerencia_o_delegado)):
    return service.set_punto_emision(db, sucursal_id, datos, actor=user.id)
