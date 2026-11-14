from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from servicio_tecnico import service
from servicio_tecnico.schemas import (
    AprobarPresupuestoIn,
    CambioEstadoIn,
    CosteoOut,
    DanoPayloadOut,
    DescuentoAplicadoOut,
    DescuentoOTIn,
    DiagnosticoIn,
    EntregarIn,
    HorasIn,
    InformeServicioOut,
    LubricacionIn,
    LubricacionOut,
    OrdenTrabajoDetalle,
    OrdenTrabajoIn,
    OrdenTrabajoOut,
    OrdenTrabajoPatch,
    PagoOTIn,
    PagoRegistradoOut,
    PiezaUsadaIn,
    PiezaUsadaOut,
    PresupuestoIn,
    PresupuestoOut,
    ReabrirGarantiaIn,
    RelojElegibleOut,
    ReportarDanoIn,
    SolicitarCompraUrgenteIn,
    TecnicoSugeridoOut,
    TrabajoRealizadoIn,
)
from shared.database import get_db
from shared.guard import CurrentUser, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["servicio-tecnico"])

_leer = require_perm("ordenes_trabajo", "consultar")
_crear = require_perm("ordenes_trabajo", "crear")
_editar = require_perm("ordenes_trabajo", "editar")


@router.get("/ordenes-trabajo", response_model=Page[OrdenTrabajoOut])
def listar(
    estado: str | None = None,
    tecnico_id: int | None = None,
    sucursal_id: int | None = None,
    numero_serie: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    items, total = service.listar(
        db, user=user, estado=estado, tecnico_id=tecnico_id, sucursal_id=sucursal_id,
        numero_serie=numero_serie, offset=pp.offset, limit=pp.limit,
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.get("/ordenes-trabajo-en-curso", response_model=list[OrdenTrabajoOut])
def en_curso(db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.ot_en_curso(db, user=user)


@router.get("/informe-servicios", response_model=list[InformeServicioOut])
def informe(
    cliente_id: int | None = None,
    tecnico_id: int | None = None,
    numero_serie: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    return service.informe_servicios(
        db, user=user, cliente_id=cliente_id, tecnico_id=tecnico_id,
        numero_serie=numero_serie, desde=desde, hasta=hasta,
    )


@router.post("/ordenes-trabajo", response_model=OrdenTrabajoOut, status_code=status.HTTP_201_CREATED)
def crear(datos: OrdenTrabajoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_ot(db, datos, user=user)


@router.get("/ordenes-trabajo/relojes-elegibles", response_model=list[RelojElegibleOut])
def relojes_elegibles(
    q: str | None = None,
    db: Session = Depends(get_db), _: CurrentUser = Depends(_crear),
):
    """Catálogo real de unidades para el selector de "unidad" al abrir una OT — con
    el cliente dueño ya resuelto cuando hay una venta confirmada."""
    return service.relojes_elegibles(db, q=q)


@router.get("/ordenes-trabajo/tecnico-sugerido", response_model=TecnicoSugeridoOut)
def tecnico_sugerido(
    numero_serie: str, sucursal_id: int | None = None,
    db: Session = Depends(get_db), _: CurrentUser = Depends(_crear),
):
    """Previsualización para el formulario de alta (FR §3.3): qué técnico se
    asignaría por marca/calibre + sucursal, antes de confirmar la OT."""
    return service.tecnico_sugerido_para_serie(db, numero_serie=numero_serie, sucursal_id=sucursal_id)


@router.get("/ordenes-trabajo/{oid}", response_model=OrdenTrabajoDetalle)
def detalle(oid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.obtener_detalle(db, oid, user=user)


@router.patch("/ordenes-trabajo/{oid}", response_model=OrdenTrabajoOut)
def actualizar(oid: int, datos: OrdenTrabajoPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.actualizar(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/diagnostico", response_model=OrdenTrabajoOut)
def diagnostico(oid: int, datos: DiagnosticoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_diagnostico(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/trabajo", response_model=OrdenTrabajoOut)
def trabajo(oid: int, datos: TrabajoRealizadoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_trabajo(db, oid, datos.trabajo_realizado, user=user)


@router.post("/ordenes-trabajo/{oid}/horas", response_model=OrdenTrabajoOut)
def horas(oid: int, datos: HorasIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_horas(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/presupuesto", response_model=PresupuestoOut, status_code=status.HTTP_201_CREATED)
def crear_presupuesto(oid: int, datos: PresupuestoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.crear_presupuesto(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/presupuesto/aprobar", response_model=OrdenTrabajoDetalle)
def aprobar_presupuesto(oid: int, datos: AprobarPresupuestoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.aprobar_presupuesto(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/piezas", response_model=PiezaUsadaOut, status_code=status.HTTP_201_CREATED)
def agregar_pieza(oid: int, datos: PiezaUsadaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.agregar_pieza_ot(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/piezas/solicitar-compra-urgente")
def solicitar_compra_urgente(
    oid: int, datos: SolicitarCompraUrgenteIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar),
):
    return service.solicitar_compra_urgente(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/lubricacion", response_model=LubricacionOut, status_code=status.HTTP_201_CREATED)
def lubricacion(oid: int, datos: LubricacionIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_lubricacion_ot(db, oid, datos, user=user)


@router.get("/ordenes-trabajo/{oid}/costeo", response_model=CosteoOut)
def costeo(oid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.get_costeo(db, oid, user=user)


@router.post("/ordenes-trabajo/{oid}/descuento", response_model=DescuentoAplicadoOut)
def descuento(oid: int, datos: DescuentoOTIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.aplicar_descuento(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/pagos", response_model=PagoRegistradoOut, status_code=status.HTTP_201_CREATED)
def pago(oid: int, datos: PagoOTIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_pago_ot(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/estado", response_model=OrdenTrabajoOut)
def estado(oid: int, datos: CambioEstadoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.cambiar_estado(db, oid, datos.estado, user=user)


@router.post("/ordenes-trabajo/{oid}/entregar", response_model=OrdenTrabajoDetalle)
def entregar(oid: int, datos: EntregarIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.entregar(db, oid, datos, user=user)


@router.get("/ordenes-trabajo/{oid}/documento/{tipo}")
def documento(oid: int, tipo: str, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return {"url": service.documento_url(db, oid, tipo, user=user)}


@router.post("/ordenes-trabajo/{oid}/reabrir-garantia", response_model=OrdenTrabajoOut, status_code=status.HTTP_201_CREATED)
def reabrir(oid: int, datos: ReabrirGarantiaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.reabrir_por_garantia(db, oid, datos, user=user)


@router.post("/ordenes-trabajo/{oid}/reportar-dano", response_model=DanoPayloadOut)
def reportar_dano(oid: int, datos: ReportarDanoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.reportar_dano(db, oid, datos, user=user)
