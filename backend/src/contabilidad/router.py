from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from contabilidad import caja as caja_mod
from contabilidad import gastos as gastos_mod
from contabilidad import recurrentes as recurrentes_mod
from contabilidad import service
from contabilidad.schemas import (
    AsientoIn,
    AsientoOut,
    BalanceComprobacionOut,
    BeneficiarioIn,
    BeneficiarioOut,
    CerrarCajaIn,
    ChequeIn,
    ChequeOut,
    CobroCxcIn,
    ConfirmarGastoIn,
    CuentaContableIn,
    CuentaContableOut,
    CxcOut,
    CxpOut,
    EstadoGastoRecurrenteIn,
    EstadoResultadosOut,
    GastoIn,
    GastoOut,
    GastoRecurrenteIn,
    GastoRecurrenteOut,
    MayorOut,
    MovimientoCajaIn,
    MovimientoCajaOut,
    PagoCxpIn,
    PeriodoIn,
    PeriodoOut,
    RentabilidadSucursalOut,
    SesionCajaOut,
)
from shared.database import get_db
from shared.guard import CurrentUser, get_current_user_full_scope, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page

router = APIRouter(tags=["contabilidad"])

_leer = require_perm("contable", "consultar")
_crear = require_perm("contable", "crear")
_editar = require_perm("contable", "editar")


# --------------------------------------------------------------- plan de cuentas
@router.get("/plan-cuentas", response_model=list[CuentaContableOut])
def get_plan_cuentas(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.plan_cuentas(db)


@router.post("/plan-cuentas", response_model=CuentaContableOut, status_code=status.HTTP_201_CREATED)
def crear_cuenta(datos: CuentaContableIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_cuenta(db, datos, actor=user.id)


# --------------------------------------------------------------- diario / mayor / balance
@router.get("/asientos", response_model=Page[AsientoOut])
def listar_asientos(
    origen: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    items, total = service.listar_asientos(db, origen=origen, desde=desde, hasta=hasta, offset=pp.offset, limit=pp.limit)
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("/asientos", response_model=AsientoOut, status_code=status.HTTP_201_CREATED)
def crear_asiento(datos: AsientoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_asiento_manual(db, datos, user=user)


@router.get("/mayor", response_model=MayorOut)
def get_mayor(cuenta: str, periodo: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.mayor(db, cuenta_codigo=cuenta, periodo=periodo)


@router.get("/balance", response_model=BalanceComprobacionOut)
def get_balance(periodo: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.balance_comprobacion(db, periodo=periodo)


@router.get("/estado-resultados", response_model=EstadoResultadosOut)
def get_estado_resultados(
    periodo: str | None = None, sucursal_id: int | None = None,
    db: Session = Depends(get_db), _: CurrentUser = Depends(_leer),
):
    return service.estado_resultados(db, periodo=periodo, sucursal_id=sucursal_id)


# --------------------------------------------------------------- periodos
@router.get("/periodos", response_model=list[PeriodoOut])
def listar_periodos(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_periodos(db)


@router.post("/periodos", response_model=PeriodoOut, status_code=status.HTTP_201_CREATED)
def crear_periodo(datos: PeriodoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_periodo(db, datos, user=user)


@router.post("/periodos/{periodo_id}/cerrar", response_model=PeriodoOut)
def cerrar_periodo(periodo_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.cerrar_periodo(db, periodo_id, user=user)


# --------------------------------------------------------------- caja
@router.post("/caja/{sucursal_id}/sesiones", response_model=SesionCajaOut, status_code=status.HTTP_201_CREATED)
def abrir_sesion_caja(
    sucursal_id: int, saldo_inicial: float = 0,
    db: Session = Depends(get_db), user: CurrentUser = Depends(_crear),
):
    from decimal import Decimal

    return caja_mod.abrir_sesion(db, sucursal_id, saldo_inicial=Decimal(str(saldo_inicial)), user=user)


@router.get("/caja/{sucursal_id}/sesiones/actual", response_model=SesionCajaOut | None)
def sesion_actual_caja(sucursal_id: int, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return caja_mod.sesion_actual(db, sucursal_id)


@router.post("/caja/{sucursal_id}/movimientos", response_model=MovimientoCajaOut, status_code=status.HTTP_201_CREATED)
def registrar_movimiento_caja(
    sucursal_id: int, datos: MovimientoCajaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar),
):
    return caja_mod.registrar_movimiento(db, sucursal_id, datos, user=user)


@router.post("/caja/{sucursal_id}/sesiones/actual/cerrar", response_model=SesionCajaOut)
def cerrar_sesion_caja(
    sucursal_id: int, datos: CerrarCajaIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar),
):
    return caja_mod.cerrar_sesion(db, sucursal_id, datos, user=user)


# --------------------------------------------------------------- cheques
@router.get("/cheques", response_model=list[ChequeOut])
def listar_cheques(tipo: str | None = None, estado: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_cheques(db, tipo=tipo, estado=estado)


@router.post("/cheques", response_model=ChequeOut, status_code=status.HTTP_201_CREATED)
def crear_cheque(datos: ChequeIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.registrar_cheque(db, datos, actor=user.id)


@router.post("/cheques/{cheque_id}/protestar", response_model=ChequeOut)
def protestar_cheque(cheque_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.protestar_cheque(db, cheque_id, user=user)


# --------------------------------------------------------------- CxC
@router.get("/cxc", response_model=list[CxcOut])
def listar_cxc(cliente_id: int | None = None, estado: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_cxc(db, cliente_id=cliente_id, estado=estado)


@router.post("/cxc/{cxc_id}/cobros", response_model=CxcOut, status_code=status.HTTP_201_CREATED)
def registrar_cobro(cxc_id: int, datos: CobroCxcIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_cobro_cxc(db, cxc_id, datos, user=user)


@router.get("/cxc/aging")
def get_aging_cxc(fecha_corte: date | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.aging_cxc(db, fecha_corte=fecha_corte)


@router.get("/cxc-pendientes", response_model=list[CxcOut])
def get_cxc_pendientes(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.cxc_pendientes(db)


# --------------------------------------------------------------- beneficiarios / CxP
@router.get("/beneficiarios", response_model=list[BeneficiarioOut])
def listar_beneficiarios(q: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_beneficiarios(db, q=q)


@router.post("/beneficiarios", response_model=BeneficiarioOut, status_code=status.HTTP_201_CREATED)
def crear_beneficiario(datos: BeneficiarioIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_beneficiario(db, datos, actor=user.id)


@router.get("/cxp", response_model=list[CxpOut])
def listar_cxp(
    proveedor_id: int | None = None, beneficiario_id: int | None = None,
    origen_tipo: str | None = None, estado: str | None = None,
    db: Session = Depends(get_db), _: CurrentUser = Depends(_leer),
):
    return service.listar_cxp(db, proveedor_id=proveedor_id, beneficiario_id=beneficiario_id,
                              origen_tipo=origen_tipo, estado=estado)


@router.post("/cxp/{cxp_id}/pagos", response_model=CxpOut, status_code=status.HTTP_201_CREATED)
def registrar_pago_cxp(cxp_id: int, datos: PagoCxpIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.registrar_pago_cxp(db, cxp_id, datos, user=user)


@router.get("/cxp/aging")
def get_aging_cxp(fecha_corte: date | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.aging_cxp(db, fecha_corte=fecha_corte)


# --------------------------------------------------------------- gastos
@router.get("/gastos", response_model=Page[GastoOut])
def listar_gastos(
    sucursal_id: int | None = None, categoria_gasto_id: int | None = None,
    estado_pago: str | None = None, estado: str | None = None,
    desde: date | None = None, hasta: date | None = None,
    pp: PageParams = Depends(page_params), db: Session = Depends(get_db), user: CurrentUser = Depends(_leer),
):
    items, total = gastos_mod.listar_gastos(
        db, user=user, sucursal_id=sucursal_id, categoria_gasto_id=categoria_gasto_id,
        estado_pago=estado_pago, estado=estado, desde=desde, hasta=hasta, offset=pp.offset, limit=pp.limit,
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.post("/gastos", response_model=GastoOut, status_code=status.HTTP_201_CREATED)
async def registrar_gasto(
    data: str = Form(...),
    soporte: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_crear),
):
    import json

    datos = GastoIn.model_validate(json.loads(data))
    contenido = await soporte.read() if soporte else None
    return gastos_mod.registrar_gasto(
        db, datos, soporte=contenido, soporte_nombre=soporte.filename if soporte else None, user=user,
    )


@router.post("/gastos/{gasto_id}/confirmar", response_model=GastoOut)
def confirmar_gasto(gasto_id: int, datos: ConfirmarGastoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return gastos_mod.confirmar_gasto(db, gasto_id, datos, user=user)


# --------------------------------------------------------------- gastos recurrentes
@router.get("/gastos-recurrentes", response_model=list[GastoRecurrenteOut])
def listar_gastos_recurrentes(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return recurrentes_mod.listar(db)


@router.post("/gastos-recurrentes", response_model=GastoRecurrenteOut, status_code=status.HTTP_201_CREATED)
def crear_gasto_recurrente(datos: GastoRecurrenteIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return recurrentes_mod.crear(db, datos, user=user)


@router.put("/gastos-recurrentes/{gid}/estado", response_model=GastoRecurrenteOut)
def set_estado_gasto_recurrente(
    gid: int, datos: EstadoGastoRecurrenteIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar),
):
    return recurrentes_mod.set_estado(db, gid, datos.estado, user=user)


# --------------------------------------------------------------- rentabilidad
@router.get("/rentabilidad-sucursal", response_model=list[RentabilidadSucursalOut])
def get_rentabilidad_sucursal(
    periodo: str | None = None, sucursal_id: int | None = None,
    db: Session = Depends(get_db), _: CurrentUser = Depends(_leer),
):
    return service.rentabilidad_sucursal(db, periodo=periodo, sucursal_id=sucursal_id)


# --------------------------------------------------------------- interno (011, pruebas)
internal_router = APIRouter(prefix="/_internal", tags=["_internal"])


@internal_router.post("/contabilidad/asiento")
def generar_asiento_interno(
    evento: str, monto: float, glosa: str, origen: str = "manual", origen_id: int | None = None,
    db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user_full_scope),
):
    """011 (mermas) y otros módulos futuros invocan aquí el motor de asiento
    automático sin depender de las internas de `contabilidad`."""
    from contabilidad.asientos_auto import generar

    a = generar(db, evento=evento, monto=monto, glosa=glosa, origen=origen, origen_id=origen_id, actor=user.id)
    return {"asiento_id": a.id if a else None}


@internal_router.post("/contabilidad/scheduler/tick")
def scheduler_tick(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user_full_scope)):
    """Fuerza una corrida del generador de gastos recurrentes (pruebas / operación)."""
    n = recurrentes_mod.generar_vencidos(db)
    return {"gastos_generados": n}
